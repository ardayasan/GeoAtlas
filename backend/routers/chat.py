"""
/api/chat — Yerel LLM asistanı (yapısal veri üzerinde sorgu-araçlı Q&A).

Akış: sistem promptu + kullanıcı geçmişi → Ollama (qwen2.5 + kısıtlı araçlar)
→ araç(lar) çalışır (salt-okunur SQLite) → final Türkçe cevap
→ çalışan araç/argümanlardan deterministik 'map_action' türetilir.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Literal, Optional

from services import query_tools
from services import llm_service
from services.llm_service import LLMUnavailable

router = APIRouter()

SYSTEM_PROMPT = (
    "Sen Türkiye GIS uygulamasının demografi asistanısın. Verilere YALNIZCA "
    "sağlanan araçlarla erişebilirsin.\n"
    "KURALLAR:\n"
    "1) YANITINI HER ZAMAN VE YALNIZCA TÜRKÇE YAZ. Başka hiçbir dil (İngilizce, "
    "Çince vb.) kullanma; tek bir kelime veya karakter bile başka dilde olmasın.\n"
    "2) Eğer araçtan kesin bir sayı geliyorsa aynen kullan. Eğer veri yoksa veya araç hata döndürüyorsa, "
    "doğrudan 'Bu veriye sahip değilim' deyip kesip atma. Elindeki genel ve bölgesel bilgilerden faydalanarak "
    "'Kesin resmi veriye sahip değilim ancak genel duruma bakıldığında tahminen...' şeklinde mantıklı yorumlar "
    "ve çıkarımlar yap. Eğer konu hakkında hiçbir tahmin üretemeyecek durumdaysan kibarca yorum yapamayacağını belirt.\n"
    "3) Aracın döndürdüğü sonuçtaki değerleri aynen kullan; tahmin etme (eğer değer varsa).\n"
    "4) Konu hakkında doğrudan bilgin yoksa, diğer elindeki metriklerden yola çıkarak bir şeyler söylemeye çalış. "
    "Kısaca, panikleyip kestirip atma, konuşkan ve analiz yapabilen bir asistan ol.\n"
    "5) Asla kendi başına matematik/oran/yüzde hesaplama yapma. Yalnızca araç "
    "sonucunda HAZIR gelen değerleri olduğu gibi sun.\n"
    "6) Kısa, net ve doğrudan yanıtla. Sayıları okunur biçimde yaz (ör. 15.754.053).\n"
    "7) Veri kaynağı TÜİK 2025 veya OpenStreetMap'tir; uygunsa kaynağı belirt.\n"
    "8) Birden çok il/metrik gerekiyorsa uygun aracı uygun argümanlarla çağır.\n"
    "9) Eğer kullanıcı okul, cami vb. noktaları (POI) sorarsa MUTLAKA 'poi_say' ARACINI KULLAN (JSON tool call). Aracı metin olarak (ör. 'poi_say {...}') yazma, doğrudan çalıştır.\n"
    "10) Harita aksiyonları otomatik üretilecektir, senin sadece uygun aracı çağırman yeterlidir."
)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


def _collect_codes(used):
    codes = []
    for u in used:
        for c in (u.get("result") or {}).get("_codes", []) or []:
            if c not in codes:
                codes.append(c)
    return codes


def _build_map_action(used):
    """Çalışan araçlardan deterministik harita aksiyonu üret."""
    
    # 1) Eğer POI sorgulandıysa doğrudan POI gösterme aksiyonu döndür
    for u in used:
        if u["name"] == "poi_say":
            res = u.get("result", {})
            if "hata" in res:
                continue # Hata aldıysa haritada katman açmaya çalışmasın
            args = u.get("args") or {}
            kategori = args.get("kategori")
            if kategori:
                return {
                    "type": "show_poi",
                    "category": kategori,
                    "country": args.get("ulke", "TR")
                }

    codes = _collect_codes(used)
    if not codes:
        return None
    names = [u["name"] for u in used]

    # Sıralama/özet + chip metriği → choropleth (+ ilk kodları vurgula)
    for u in used:
        res = u.get("result") or {}
        metric = res.get("_metric")
        if u["name"] in ("siralama", "turkiye_ozet") and metric in query_tools.CHIP_METRICS:
            return {"type": "choropleth", "metric": metric, "highlight": codes[:10]}

    # Tek il/ilçe → odaklan
    if names and names[-1] in ("il_istatistik", "ilce_istatistik") and len(codes) == 1:
        return {"type": "focus", "codes": codes}

    # Karşılaştırma / ilçe listesi / çoklu → vurgula
    return {"type": "highlight", "codes": codes[:20]}


@router.get("/health")
async def chat_health():
    return await llm_service.health()


@router.post("")
async def chat(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="Mesaj yok.")

    convo = [{"role": "system", "content": SYSTEM_PROMPT}]
    convo += [{"role": m.role, "content": m.content} for m in req.messages]

    try:
        answer, used = await llm_service.chat_with_tools(
            convo, query_tools.TOOLS, query_tools.execute_tool)
    except LLMUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    return {
        "answer": answer,
        "map_action": _build_map_action(used),
        "used": [{"arac": u["name"], "args": u["args"]} for u in used],
    }
