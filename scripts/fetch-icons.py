#!/usr/bin/env python3
"""Fetch each app's favicon / apple-touch icon and cache under public/icons/."""

from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
APPS_JSON = ROOT / "public" / "apps.json"
ICONS_DIR = ROOT / "public" / "icons"
UA = "Mozilla/5.0 (compatible; app-portal-icon-fetch/1.0)"
FALLBACKS = (
    "/favicon.svg",
    "/apple-touch-icon.png",
    "/favicon-32x32.png",
    "/favicon.ico",
)

CTX = ssl.create_default_context()


def slug_for(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def fetch(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=CTX, timeout=30) as resp:
        ctype = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        return resp.read(), ctype


def score_icon(tag: str, rel: str, href: str) -> int:
    rel_l = rel.lower()
    href_l = href.lower()
    tag_l = tag.lower()
    score = 50
    if "svg" in href_l or "svg" in tag_l:
        score = 400
    elif "apple-touch-icon" in rel_l:
        score = 300
    elif "32x32" in href_l or "32x32" in tag_l:
        score = 200
    elif href_l.endswith(".ico") or "favicon" in href_l:
        score = 100
    sizes = re.search(r"""\bsizes=["']([^"']+)["']""", tag, re.I)
    if sizes and "x" in sizes.group(1).lower():
        try:
            score += min(int(sizes.group(1).lower().split("x", 1)[0]), 180)
        except ValueError:
            pass
    return score


def pick_icon_href(html: str) -> str | None:
    scored: list[tuple[int, str]] = []
    for m in re.finditer(r"""<link\b[^>]*>""", html, re.I):
        tag = m.group(0)
        rel_m = re.search(r"""\brel=["']([^"']+)["']""", tag, re.I)
        href_m = re.search(r"""\bhref=["']([^"']+)["']""", tag, re.I)
        if not rel_m or not href_m:
            continue
        rel = rel_m.group(1)
        if "icon" not in rel.lower():
            continue
        href = href_m.group(1)
        scored.append((score_icon(tag, rel, href), href))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]


def looks_like_image(data: bytes, ctype: str) -> bool:
    if ctype.startswith("image/"):
        return True
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if data.startswith(b"\xff\xd8\xff"):
        return True
    if data[:4] in (b"RIFF", b"GIF8") or data.startswith(b"\x00\x00\x01\x00"):
        return True
    head = data.lstrip()[:200].lower()
    return head.startswith(b"<svg") or b"<svg" in head[:50]


def ext_for(url: str, ctype: str, data: bytes) -> str:
    path = urlparse(url).path.lower()
    for suffix, ext in (
        (".svg", "svg"),
        (".png", "png"),
        (".ico", "ico"),
        (".jpg", "jpg"),
        (".jpeg", "jpg"),
        (".webp", "webp"),
    ):
        if path.endswith(suffix):
            return ext
    mapping = {
        "image/svg+xml": "svg",
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "image/x-icon": "ico",
        "image/vnd.microsoft.icon": "ico",
    }
    if ctype in mapping:
        return mapping[ctype]
    if data.lstrip().startswith(b"<svg") or b"<svg" in data[:80].lower():
        return "svg"
    if data.startswith(b"\x89PNG"):
        return "png"
    return "bin"


def resolve_icon_url(base: str, href: str) -> str:
    if href.startswith("//"):
        return "https:" + href
    return urljoin(base.rstrip("/") + "/", href)


def fetch_best_icon(base: str) -> tuple[str, bytes, str]:
    candidates: list[str] = []
    try:
        html, _ = fetch(base.rstrip("/") + "/")
        href = pick_icon_href(html.decode("utf-8", errors="ignore"))
        if href:
            candidates.append(resolve_icon_url(base, href))
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  warning: could not load HTML ({exc})", file=sys.stderr)

    for path in FALLBACKS:
        url = base.rstrip("/") + path
        if url not in candidates:
            candidates.append(url)

    last_error: Exception | None = None
    for url in candidates:
        try:
            data, ctype = fetch(url)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            continue
        if looks_like_image(data, ctype):
            return url, data, ctype
        print(f"  skipping non-image {url} ({ctype or 'unknown type'})", file=sys.stderr)

    raise RuntimeError(f"no usable icon for {base}: {last_error}")


def main() -> int:
    apps = json.loads(APPS_JSON.read_text())
    if not isinstance(apps, list) or not apps:
        print("apps.json is empty or invalid", file=sys.stderr)
        return 1

    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    updated = []

    for app in apps:
        name = app["name"]
        url = app["url"]
        slug = slug_for(name)
        print(f"Fetching icon for {name} ({url})…")
        icon_url, data, ctype = fetch_best_icon(url)
        ext = ext_for(icon_url, ctype, data)
        for old in ICONS_DIR.glob(f"{slug}.*"):
            old.unlink()
        dest = ICONS_DIR / f"{slug}.{ext}"
        dest.write_bytes(data)
        print(f"  cached {dest.relative_to(ROOT)} (from {icon_url})")
        updated.append(
            {
                "name": name,
                "url": url,
                "description": app.get("description", ""),
                "icon": f"/icons/{slug}.{ext}",
            }
        )

    APPS_JSON.write_text(json.dumps(updated, indent=2) + "\n")
    print(f"Updated {APPS_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
