"""Inline web/{styles.css, app.js, products.json} into single-file builds.

    python3 web/build.py

Outputs (both self-contained; the only external request is Google Fonts):
  web/dist/index.html            complete document - open via file:// or host anywhere
  web/dist/index.fragment.html   headless fragment - paste target for a Claude Artifact

Re-running is idempotent: same inputs produce byte-identical output.
"""

import re
from pathlib import Path

WEB = Path(__file__).resolve().parent
DIST = WEB / "dist"

_WRAPPERS = (
    r"(?is)<!doctype html>\s*",
    r"(?is)</?html[^>]*>\s*",
    r"(?is)</?head[^>]*>\s*",
    r"(?is)</?body[^>]*>\s*",
    r"(?is)<meta charset[^>]*>\s*",
    r'(?is)<meta name="viewport"[^>]*>\s*',
)


def build() -> None:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    data = (WEB / "products.json").read_text(encoding="utf-8").strip().replace("</", "<\\/")

    html = html.replace(
        '<link rel="stylesheet" href="styles.css">',
        f"<style>\n{css}\n</style>",
    )
    html = html.replace(
        '<script src="app.js" defer></script>',
        f"<script>\nwindow.__CATALOG__ = {data};\n{js}\n</script>",
    )

    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "index.html").write_text(html, encoding="utf-8")

    fragment = html
    for pattern in _WRAPPERS:
        fragment = re.sub(pattern, "", fragment)
    fragment = fragment.strip() + "\n"
    (DIST / "index.fragment.html").write_text(fragment, encoding="utf-8")

    for name, text in (("index.html", html), ("index.fragment.html", fragment)):
        print(f"built web/dist/{name} ({len(text):,} bytes)")


if __name__ == "__main__":
    build()
