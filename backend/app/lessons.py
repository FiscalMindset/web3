"""Markdown curriculum loader. Lessons live in content/lessons/*.md with a
tiny frontmatter block (--- key: value ---)."""
from pathlib import Path

from .config import LESSONS_DIR


def _parse(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    meta = {"title": path.stem, "module": "General", "order": 999, "minutes": 10}
    body = raw
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            for line in raw[3:end].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = raw[end + 3:].lstrip("\n")
    try:
        meta["order"] = int(meta.get("order", 999))
    except ValueError:
        meta["order"] = 999
    return {"slug": path.stem, "body": body, **meta}


def list_lessons() -> list[dict]:
    items = []
    if LESSONS_DIR.exists():
        for p in sorted(LESSONS_DIR.glob("*.md")):
            d = _parse(p)
            d.pop("body")
            items.append(d)
    return sorted(items, key=lambda x: x["order"])


def get_lesson(slug: str) -> dict | None:
    safe = "".join(ch for ch in slug if ch.isalnum() or ch in "-_")
    p = LESSONS_DIR / f"{safe}.md"
    if not p.is_file():
        return None
    return _parse(p)
