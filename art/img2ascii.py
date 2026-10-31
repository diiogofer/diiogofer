#!/usr/bin/env python3
"""
img2ascii.py — converte uma imagem (PNG, JPG ou SVG) em ascii.txt.

  pip install pillow            (e cairosvg, se quiseres usar .svg)
  python img2ascii.py imagem.png                 # 38 colunas, escreve ascii.txt
  python img2ascii.py foto.jpg -w 40 --invert    # para fotos com fundo claro
  python img2ascii.py icon.svg --contrast 1.8

Zonas escuras/opacas da imagem viram caracteres densos (@#%), zonas claras viram espaço.
Usa --invert se o resultado sair "em negativo".
"""
import argparse
import io
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

RAMP = " .:-=+*#%@"
CELL_RATIO = 9.7 / 20      # largura/altura de cada caractere no SVG (CHAR_W / LINE_H)


def load(path: Path, size: int = 1200) -> Image.Image:
    if path.suffix.lower() == ".svg":
        import cairosvg
        png = cairosvg.svg2png(url=str(path), output_width=size)
        return Image.open(io.BytesIO(png))
    return Image.open(path)


def to_gray(img: Image.Image) -> Image.Image:
    """Imagem em tons de cinza onde 255 = 'muita tinta'."""
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    return ImageOps.invert(img.convert("L"))


def convert(path: Path, width: int, invert: bool, contrast: float) -> list[str]:
    gray = to_gray(load(path))
    if invert:
        gray = ImageOps.invert(gray)
    bbox = gray.point(lambda v: 255 if v > 10 else 0).getbbox()
    if bbox:
        gray = gray.crop(bbox)
    gray = ImageEnhance.Contrast(gray).enhance(contrast)
    height = max(1, round(width * gray.height / gray.width * CELL_RATIO))
    gray = gray.resize((width, height), Image.LANCZOS)
    px = gray.load()
    n = len(RAMP) - 1
    return ["".join(RAMP[px[x, y] * n // 255] for x in range(width)).rstrip()
            for y in range(height)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", type=Path)
    ap.add_argument("-w", "--width", type=int, default=38, help="colunas (default 38)")
    ap.add_argument("-o", "--out", type=Path, default=Path(__file__).with_name("ascii.txt"))
    ap.add_argument("--invert", action="store_true", help="inverte claro/escuro")
    ap.add_argument("--contrast", type=float, default=1.3)
    a = ap.parse_args()
    lines = convert(a.image, a.width, a.invert, a.contrast)
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n✓ {a.out.name}: {a.width}x{len(lines)}")


if __name__ == "__main__":
    main()
