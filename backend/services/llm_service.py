"""
Yerel LLM (Ollama) istemcisi + araç-çağrımı (tool-calling) döngüsü.

Tamamen yerel: Ollama `http://localhost:11434` üzerinde çalışır, harici API yok.
Model varsayılan `qwen2.5` (güçlü araç çağrımı + Türkçe). Env ile değiştirilebilir.
"""
import os
import json
import asyncio

import httpx

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
RAG_MODEL = os.environ.get("RAG_MODEL", "qwen2.5")
MAX_ITERS = 5
TIMEOUT = httpx.Timeout(120.0, connect=5.0)


class LLMUnavailable(Exception):
    """Ollama'ya ulaşılamadı / model yok."""


async def chat_with_tools(messages, tools, execute_fn):
    """messages + tools ile Ollama'yı çağırır; tool_call gelirse execute_fn ile
    çalıştırıp döngüye devam eder. (final_answer, used[]) döndürür.

    execute_fn(name, args) -> dict  (senkron; ayrı thread'de çalıştırılır)
    used: [{ "name", "args", "result" }]
    """
    convo = list(messages)
    used = []

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for _ in range(MAX_ITERS):
            try:
                resp = await client.post(f"{OLLAMA_HOST}/api/chat", json={
                    "model": RAG_MODEL,
                    "messages": convo,
                    "tools": tools,
                    "stream": False,
                    "options": {"temperature": 0.2},
                })
            except httpx.ConnectError as e:
                raise LLMUnavailable(
                    f"Ollama'ya ulaşılamadı ({OLLAMA_HOST}). 'ollama serve' çalışıyor mu?") from e
            except httpx.HTTPError as e:
                raise LLMUnavailable(f"LLM isteği başarısız: {e}") from e

            if resp.status_code == 404:
                raise LLMUnavailable(
                    f"Model '{RAG_MODEL}' bulunamadı. 'ollama pull {RAG_MODEL}' çalıştırın.")
            resp.raise_for_status()
            msg = resp.json().get("message", {}) or {}
            convo.append(msg)

            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                return (msg.get("content") or "").strip(), used

            for tc in tool_calls:
                fn = tc.get("function", {}) or {}
                name = fn.get("name", "")
                args = fn.get("arguments", {}) or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                result = await asyncio.to_thread(execute_fn, name, args)
                used.append({"name": name, "args": args, "result": result})
                convo.append({
                    "role": "tool",
                    "tool_name": name,
                    "content": json.dumps(result, ensure_ascii=False),
                })

    # iterasyon sınırı aşıldı — son metni döndür (varsa)
    last = (convo[-1].get("content") or "").strip() if convo else ""
    return (last or "Bu soruyu mevcut veriden yanıtlayamadım."), used


async def health():
    """Ollama erişilebilir mi + model var mı."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            r.raise_for_status()
            models = [m.get("name", "") for m in r.json().get("models", [])]
            has = any(m == RAG_MODEL or m.startswith(RAG_MODEL + ":") for m in models)
            return {"ok": True, "host": OLLAMA_HOST, "model": RAG_MODEL,
                    "model_yuklu": has, "mevcut_modeller": models}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "host": OLLAMA_HOST, "hata": str(e)}
