"""GeoAtlas app ikonu oluşturur: 1024×1024 PNG → ICNS."""
from PIL import Image, ImageDraw, ImageFilter
import math, os, subprocess, shutil, sys

SIZE = 1024
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "GeoAtlas.app", "Contents", "Resources")
ICONSET = os.path.join(OUT_DIR, "AppIcon.iconset")
ICNS = os.path.join(OUT_DIR, "AppIcon.icns")


def gradient_bg(draw, size):
    """Koyu lacivert → orta mavi dikey gradyan."""
    for y in range(size):
        t = y / size
        r = int(10  + t * 18)
        g = int(20  + t * 55)
        b = int(80  + t * 110)
        draw.rectangle([(0, y), (size, y + 1)], fill=(r, g, b, 255))


def rounded_mask(size, radius_frac=0.22):
    """macOS ikon köşe yuvarlama maskesi."""
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    r = int(size * radius_frac)
    md.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=r, fill=255)
    return mask


def draw_globe(draw, cx, cy, R):
    """Beyaz küre: dış çember + enlem/boylam çizgileri."""
    lw_outer = max(6, R // 28)
    lw_inner = max(3, R // 52)
    alpha_grid = 160

    # Küre dolgusu (yarı şeffaf mavi)
    draw.ellipse(
        [(cx - R, cy - R), (cx + R, cy + R)],
        fill=(40, 90, 200, 110),
    )

    # Dış çember
    draw.ellipse(
        [(cx - R, cy - R), (cx + R, cy + R)],
        outline=(255, 255, 255, 230),
        width=lw_outer,
    )

    # Enlem çizgileri (3 adet)
    for frac in (-0.55, 0.0, 0.55):
        y_off = int(frac * R)
        x_half = int(math.sqrt(max(0, R**2 - y_off**2)) * 0.97)
        if x_half < 10:
            continue
        ry = max(6, int(x_half * 0.30))
        draw.arc(
            [(cx - x_half, cy + y_off - ry), (cx + x_half, cy + y_off + ry)],
            start=0, end=360,
            fill=(255, 255, 255, alpha_grid),
            width=lw_inner,
        )

    # Boylam çizgileri (3 adet)
    for frac in (-0.48, 0.0, 0.48):
        x_off = int(frac * R)
        y_half = int(math.sqrt(max(0, R**2 - x_off**2)) * 0.97)
        if y_half < 10:
            continue
        rx = max(6, int(y_half * 0.28))
        draw.arc(
            [(cx + x_off - rx, cy - y_half), (cx + x_off + rx, cy + y_half)],
            start=0, end=360,
            fill=(255, 255, 255, alpha_grid),
            width=lw_inner,
        )


def make_icon_png(size) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg = Image.new("RGBA", (size, size))
    gradient_bg(ImageDraw.Draw(bg), size)
    img.paste(bg, mask=rounded_mask(size))

    draw = ImageDraw.Draw(img)
    cx = cy = size // 2
    R = int(size * 0.365)

    # Hafif parlama (glow)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gr = int(R * 1.15)
    gd.ellipse([(cx - gr, cy - gr), (cx + gr, cy + gr)], fill=(80, 140, 255, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=size // 22))
    img = Image.alpha_composite(img, glow)

    draw = ImageDraw.Draw(img)
    draw_globe(draw, cx, cy, R)
    return img


def build_iconset():
    os.makedirs(ICONSET, exist_ok=True)
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    base = make_icon_png(1024)
    for s in sizes:
        icon = base.resize((s, s), Image.LANCZOS)
        icon.save(os.path.join(ICONSET, f"icon_{s}x{s}.png"))
        if s <= 512:
            icon2 = base.resize((s * 2, s * 2), Image.LANCZOS)
            icon2.save(os.path.join(ICONSET, f"icon_{s}x{s}@2x.png"))
    print(f"  Iconset oluşturuldu: {ICONSET}")


def convert_to_icns():
    result = subprocess.run(
        ["iconutil", "-c", "icns", ICONSET, "-o", ICNS],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("  UYARI: iconutil hatası:", result.stderr)
    else:
        print(f"  İkon oluşturuldu: {ICNS}")
    shutil.rmtree(ICONSET, ignore_errors=True)


if __name__ == "__main__":
    print("GeoAtlas ikonu oluşturuluyor...")
    build_iconset()
    convert_to_icns()
    print("Tamamlandı.")
