#!/usr/bin/env python3
"""Régénère nouveautes.html (entre les marqueurs CHANGELOG) et le numéro de
version des footers, depuis les notes de version de l'app.

Source unique : ../Freenetic/Freenetic/Resources/notes-de-version.md
Usage : python3 scripts/generate-nouveautes.py   (depuis la racine du site)
À lancer quand la version est EN LIGNE sur le store, pas au build (la CI
uploade des jours avant la mise en ligne réelle).
"""
import html
import pathlib
import re
import sys

SITE = pathlib.Path(__file__).resolve().parent.parent
SOURCE = SITE.parent / "Freenetic" / "Freenetic" / "Resources" / "notes-de-version.md"
PAGE = SITE / "nouveautes.html"
INDEX = SITE / "index.html"
START, END = "<!-- CHANGELOG:START -->", "<!-- CHANGELOG:END -->"


def parse(text):
    """Miroir volontairement duplicatif du parseur Swift (spec : format trivial,
    contrat policé par les tests du kit)."""
    entries, current = [], None
    for line in text.split("\n"):
        if line.startswith("## "):
            parts = [p.strip() for p in line[3:].split(" — ")]
            if not re.fullmatch(r"\d+(\.\d+)*", parts[0]):
                current = None
                continue
            date = next((p for p in parts[1:] if "build" not in p), None)
            current = {"version": parts[0], "date": date, "lines": []}
            entries.append(current)
        elif current is not None and line.strip() != "---":
            current["lines"].append(line)
    for e in entries:
        e["body"] = "\n".join(e.pop("lines")).strip()
    return entries


BOLD = re.compile(r"\*\*(.+?)\*\*")


def render_paragraph(par):
    full = re.fullmatch(r"\*\*([^*]+)\*\*", par.strip())
    if full:
        return f"      <h3>{html.escape(full.group(1))}</h3>"
    text = html.escape(" ".join(l.strip() for l in par.split("\n") if l.strip()))
    text = BOLD.sub(r"<strong>\1</strong>", text)
    return f"      <p>{text}</p>"


def render(entries):
    blocks = []
    for i, e in enumerate(entries):
        classes = "rel latest" if i == 0 else "rel"
        when = f'<span class="when">{html.escape(e["date"])}</span>' if e["date"] else ""
        tag = '<span class="tagnew">DERNIÈRE</span>' if i == 0 else ""
        paragraphs = "\n".join(render_paragraph(p)
                               for p in e["body"].split("\n\n") if p.strip())
        blocks.append(
            f'    <article class="{classes}">\n'
            f'      <div class="ver"><span class="num">{html.escape(e["version"])}</span>{when}{tag}</div>\n'
            f"{paragraphs}\n"
            f"    </article>"
        )
    return "\n\n".join(blocks)


def splice(path, content):
    page = path.read_text(encoding="utf-8")
    if START not in page or END not in page:
        sys.exit(f"marqueurs CHANGELOG absents de {path.name}")
    before, rest = page.split(START, 1)
    _, after = rest.split(END, 1)
    path.write_text(before + START + "\n" + content + "\n" + END + after,
                    encoding="utf-8")


def bump_footer(path, version):
    page = path.read_text(encoding="utf-8")
    page = re.sub(r"(>v)\d+\.\d+(?:\.\d+)?( · macOS)", rf"\g<1>{version}\g<2>", page)
    path.write_text(page, encoding="utf-8")


def main():
    entries = parse(SOURCE.read_text(encoding="utf-8"))
    # Une section sans date est un brouillon : c'est la date, posée à la mise
    # en ligne, qui publie. (« Activer une release » = la dater.)
    entries = [e for e in entries if e["date"]]
    if not entries:
        sys.exit("aucune section datée dans la source")
    splice(PAGE, render(entries))
    for page in (PAGE, INDEX):
        bump_footer(page, entries[0]["version"])
    print(f"nouveautes.html : {len(entries)} versions, dernière {entries[0]['version']}")


if __name__ == "__main__":
    main()
