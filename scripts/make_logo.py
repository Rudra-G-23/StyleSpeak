"""Generate the StyleSpeak logo / favicon.

Produces two PNGs under assets/:
  * logo.png  - 512x512 rounded-square monogram, used by st.logo() and as the
    browser-tab favicon (page_icon).
  * logo_wide.png - 960x260 wordmark for the top of the sidebar.

Run once (committed to the repo):
    uv run python scripts/make_logo.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parents[1] / "assets"
INK = (17, 24, 39)  # near-black indigo
ACCENT = (99, 102, 241)  # indigo-500
PAPER = (255, 255, 255)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rounded(size: int, radius_frac: float = 0.22) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = int(size * radius_frac)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=INK)
    # accent bar
    draw.rounded_rectangle(
        [int(size * 0.18), int(size * 0.79), int(size * 0.82), int(size * 0.875)],
        radius=int(size * 0.025),
        fill=ACCENT,
    )
    return img


def make_icon(size: int = 512) -> Image.Image:
    img = _rounded(size)
    draw = ImageDraw.Draw(img)
    font = _font(int(size * 0.62))
    text = "S"
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.text(
        ((size - tw) / 2 - box[0], (size - th) / 2 - box[1] - size * 0.08),
        text,
        font=font,
        fill=PAPER,
    )
    return img


def make_wordmark(height: int = 260) -> Image.Image:
    font = _font(int(height * 0.40))
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    box = tmp.textbbox((0, 0), "StyleSpeak", font=font)
    text_w = box[2] - box[0]
    width = height + 28 + text_w + 24
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    img.alpha_composite(make_icon(height).resize((height, height), Image.LANCZOS), (0, 0))
    draw = ImageDraw.Draw(img)
    draw.text(
        (height + 28 - box[0], (height - (box[3] - box[1])) / 2 - box[1]),
        "StyleSpeak",
        font=font,
        fill=INK,
    )
    return img


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    make_icon().save(ASSETS / "logo.png")
    make_wordmark().save(ASSETS / "logo_wide.png")
    print(f"wrote {ASSETS / 'logo.png'} and {ASSETS / 'logo_wide.png'}")


if __name__ == "__main__":
    main()
