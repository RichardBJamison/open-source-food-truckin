"""Library (Settings › Library) and the Help tutor.

The manual lives in ``library/<lang>/*.md``: one chapter per file with a small front matter block
(id, section, title, summary, view) and one topic per ``## `` heading. Spanish headings carry an explicit
``{#topic-id}`` so links, paths and "Take me there" are the same in both languages.

Help answers from the manual in the browser when AI is off. When the owner has connected an AI
(Settings › AI), ``build_prompt`` turns the question, the matching manual pages and a read-only summary of
the truck into one message for that AI. Nothing here writes data.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LANGS = ("en", "es")
_cache: dict = {}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_chapter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError("chapter is missing its front matter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    for k in ("id", "section", "title", "summary"):
        if not meta.get(k):
            raise ValueError(f"chapter front matter needs '{k}'")
    topics, cur = [], None
    for line in text[m.end():].splitlines():
        h = re.match(r"^## (.+?)\s*(?:\{#([a-z0-9-]+)\})?\s*$", line)
        if h:
            cur = {"id": h.group(2) or slug(h.group(1)), "title": h.group(1).strip(), "body": []}
            topics.append(cur)
        elif cur is not None:
            cur["body"].append(line)
    for t in topics:
        t["body"] = "\n".join(t["body"]).strip()
    return {"id": meta["id"], "section": meta["section"], "title": meta["title"], "summary": meta["summary"],
            "view": meta.get("view") or "", "topics": topics}


def _stamp(folder: Path) -> tuple:
    return tuple(sorted((p.name, p.stat().st_mtime_ns) for p in folder.glob("*") if p.is_file()))


def load(base: Path, lang: str) -> dict:
    """The whole manual for one language (cached until a file changes)."""
    lang = lang if lang in LANGS else "en"
    folder = Path(base) / lang
    stamp = _stamp(folder)
    hit = _cache.get(str(folder))
    if hit and hit[0] == stamp:
        return hit[1]
    chapters = [parse_chapter(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("[0-9]*.md"))]
    meta = json.loads((folder / "_paths.json").read_text(encoding="utf-8"))
    sections = []
    for c in chapters:
        if c["section"] not in sections:
            sections.append(c["section"])
    by_id = {c["id"]: c for c in chapters}
    paths = []
    for p in meta.get("paths", []):
        items = []
        for ref in p.get("items", []):
            cid, _, tid = ref.partition("/")
            c = by_id.get(cid)
            t = next((x for x in c["topics"] if x["id"] == tid), None) if c and tid else None
            if c and (t or not tid):
                items.append({"chapter": cid, "topic": tid, "label": t["title"] if t else c["title"]})
        paths.append({"title": p.get("title", ""), "blurb": p.get("blurb", ""), "items": items})
    manual = {"lang": lang, "title": meta.get("title", ""), "intro": meta.get("intro", ""),
              "sections": sections, "paths": paths, "chapters": chapters}
    _cache[str(folder)] = (stamp, manual)
    return manual


def problems(base: Path) -> list[str]:
    """Everything that would break a link: used by the tests."""
    out = []
    mans = {lang: load(base, lang) for lang in LANGS}
    for lang, m in mans.items():
        ids = {c["id"]: {t["id"] for t in c["topics"]} for c in m["chapters"]}
        if len(ids) != len(m["chapters"]):
            out.append(f"{lang}: duplicate chapter id")
        raw = json.loads((Path(base) / lang / "_paths.json").read_text(encoding="utf-8"))
        for p in raw["paths"]:
            for ref in p["items"]:
                cid, _, tid = ref.partition("/")
                if cid not in ids or (tid and tid not in ids[cid]):
                    out.append(f"{lang}: path '{p['title']}' points at missing '{ref}'")
        for c in m["chapters"]:
            if not c["topics"]:
                out.append(f"{lang}: chapter '{c['id']}' has no topics")
            if len({t["id"] for t in c["topics"]}) != len(c["topics"]):
                out.append(f"{lang}: chapter '{c['id']}' repeats a topic id")
    en = {c["id"]: [t["id"] for t in c["topics"]] for c in mans["en"]["chapters"]}
    es = {c["id"]: [t["id"] for t in c["topics"]] for c in mans["es"]["chapters"]}
    if en != es:
        for cid in sorted(set(en) | set(es)):
            if en.get(cid) != es.get(cid):
                out.append(f"es: chapter '{cid}' topics {es.get(cid)} differ from en {en.get(cid)}")
    return out


def topics_for(manual: dict, refs: list) -> list[dict]:
    """Manual pages for 'chapter/topic' refs sent by the browser; unknown refs are ignored."""
    by_id = {c["id"]: c for c in manual["chapters"]}
    out, seen = [], set()
    for ref in refs or []:
        cid, _, tid = str(ref).partition("/")
        c = by_id.get(cid)
        if not c:
            continue
        for t in c["topics"]:
            if (not tid or t["id"] == tid) and (cid, t["id"]) not in seen:
                seen.add((cid, t["id"]))
                out.append({"chapter": cid, "chapter_title": c["title"], "topic": t["id"], "title": t["title"],
                            "view": c["view"], "body": t["body"]})
                if not tid and len(out) >= 6:
                    break
        if len(out) >= 8:
            break
    return out


PROMPT = {
    "en": (
        "You are Help, the built-in guide inside Open Source Food Truckin' (OSFT), a free food-truck inventory program "
        "that runs on the owner's own computer. You teach owners and crew how to use the program and walk them "
        "through it.\n"
        "Rules:\n"
        "- Answer from the LIBRARY PAGES below and the TRUCK SUMMARY. If they don't cover the question, say so in one "
        "line and point to the closest Library page. Never invent buttons, screens or features.\n"
        "- Teach step by step: short numbered steps, exact screen and button names in **bold**, the menu path written "
        "like Settings › AI.\n"
        "- Use the truck summary to make the answer specific (for example, how many products are under PAR), but you "
        "can't click, change or save anything, and never say you did.\n"
        "- Keep it under 180 words unless they ask for more. Plain text with **bold** and lists only.\n"
        "- Reply in English."
    ),
    "es": (
        "Eres Ayuda, la guía integrada de Open Source Food Truckin' (OSFT), un programa gratis de inventario para food "
        "trucks que corre en la computadora del dueño. Enseñas a dueños y equipo a usar el programa y los guías paso a "
        "paso.\n"
        "Reglas:\n"
        "- Responde con las PÁGINAS DE LA BIBLIOTECA de abajo y el RESUMEN DEL CAMIÓN. Si no cubren la pregunta, dilo en "
        "una línea y señala la página más cercana. Nunca inventes botones, pantallas ni funciones.\n"
        "- Enseña paso a paso: pasos cortos numerados, nombres exactos de pantallas y botones en **negritas**, la ruta "
        "escrita así: Ajustes › IA.\n"
        "- Usa el resumen del camión para que la respuesta sea concreta (por ejemplo, cuántos productos están bajo "
        "PAR), pero no puedes tocar, cambiar ni guardar nada, y nunca digas que lo hiciste.\n"
        "- Menos de 180 palabras a menos que pidan más. Solo texto con **negritas** y listas.\n"
        "- Responde en español."
    ),
}


def build_prompt(lang: str, question: str, pages: list[dict], snapshot: dict, history: list | None = None,
                 view: str = "") -> str:
    lang = lang if lang in LANGS else "en"
    lib = "\n\n".join(f"[{p['chapter_title']} › {p['title']}]\n{p['body']}" for p in pages) or "(no matching pages)"
    convo = ""
    for turn in (history or [])[-4:]:
        if isinstance(turn, dict) and turn.get("q") and turn.get("a"):
            convo += f"User: {str(turn['q'])[:400]}\nHelp: {str(turn['a'])[:600]}\n"
    parts = [PROMPT[lang], "LIBRARY PAGES:\n" + lib,
             "TRUCK SUMMARY (read-only):\n" + json.dumps(snapshot, ensure_ascii=False)]
    if view:
        parts.append(f"The user is on the '{view}' screen.")
    if convo:
        parts.append("EARLIER IN THIS CHAT:\n" + convo.strip())
    parts.append("QUESTION:\n" + question.strip()[:1000])
    return "\n\n".join(parts)
