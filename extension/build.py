"""Build the form helper for the Chrome Web Store (decision 030).

    python extension/build.py

Draws the icons (icons/*.png) and writes dist/job-copilot-helper-<version>.zip with only the
files the extension needs (no tests, no README). Upload that zip in the Chrome Web Store
developer dashboard; STORE.md has the listing text and the privacy answers.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ["manifest.json", "popup.html", "popup.js", "match.js", "fill.js"]
SIZES = (16, 32, 48, 128)
TEAL = (15, 118, 110, 255)  # --color-primary in apps/web
WHITE = (255, 255, 255, 255)


def draw_icon(size: int) -> "Image.Image":
    from PIL import Image, ImageDraw

    scale = 8  # draw large, then shrink, for smooth edges
    s = size * scale
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=s // 5, fill=TEAL)
    # A page with a check mark: "filled and checked, never submitted".
    left, top, right, bottom = s * 0.27, s * 0.18, s * 0.73, s * 0.82
    d.rounded_rectangle((left, top, right, bottom), radius=s // 24, fill=WHITE)
    width = max(scale, round(s * 0.075))
    d.line([(s * 0.36, s * 0.52), (s * 0.46, s * 0.63), (s * 0.64, s * 0.40)], fill=TEAL, width=width, joint="curve")
    return image.resize((size, size), Image.LANCZOS)


def build() -> Path:
    icons = HERE / "icons"
    icons.mkdir(exist_ok=True)
    for size in SIZES:
        draw_icon(size).save(icons / f"icon{size}.png")
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    dist = HERE.parent / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / f"job-copilot-helper-{manifest['version']}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            z.write(HERE / name, name)
        for size in SIZES:
            z.write(icons / f"icon{size}.png", f"icons/icon{size}.png")
    return out


if __name__ == "__main__":
    print(build())
