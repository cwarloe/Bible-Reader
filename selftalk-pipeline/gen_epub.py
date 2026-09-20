#!/usr/bin/env python3
"""
Generate EPUB files from the self-talk library YAML content.

Produces one combined EPUB with all 33 tracks organized by category,
suitable for ElevenLabs Reader with chapter navigation.

Output: output/epub/selftalk-library.epub
        output/epub/selftalk-morning.epub   (11 morning tracks only)
        output/epub/selftalk-evening.epub   (11 evening tracks only)

Daytime tracks are included in the combined EPUB as a single-read-through
(no repetitions — Reader can't replicate the 3× drill format; use the
assembled MP3 for that).

Usage:
    python gen_epub.py                  # all three EPUBs
    python gen_epub.py --type morning   # morning-only EPUB
    python gen_epub.py --type daytime
    python gen_epub.py --type evening
    python gen_epub.py --combined       # combined EPUB only
"""
from __future__ import annotations

import argparse
import io
import re
import textwrap
import uuid
import zipfile
from datetime import date
from pathlib import Path

import yaml

# ── paths ─────────────────────────────────────────────────────────────────────

CONTENT_DIR = Path(__file__).parent / "content"
OUT_DIR = Path(__file__).parent / "output" / "epub"

CATEGORIES = [
    ("identity",      "Identity in Christ"),
    ("grace",         "Grace & Forgiveness"),
    ("fear",          "Fear & Anxiety"),
    ("mind",          "Renewing the Mind"),
    ("purpose",       "Purpose & Calling"),
    ("authority",     "Spiritual Authority"),
    ("strength",      "Strength & Perseverance"),
    ("relationships", "Relationships & Love"),
    ("work",          "Work as Holy Calling"),
    ("hope",          "Hope & Redemption"),
    ("community",     "Community & Vulnerability"),
]

TRACK_FILES = [
    ("morning", "01-morning.yaml",  "Morning"),
    ("daytime", "02-daytime.yaml",  "Daytime Drill"),
    ("evening", "03-evening.yaml",  "Evening"),
]

TRACK_DURATION = {"morning": "8 min", "daytime": "6 min", "evening": "5 min"}

# ── text helpers ───────────────────────────────────────────────────────────────

STAGE_DIR_RE = re.compile(r"^\s*\[.*\]\s*$")


def strip_stage(text: str) -> str:
    lines = [l for l in text.splitlines() if not STAGE_DIR_RE.match(l)]
    return "\n".join(lines).strip()


def normalize_reader_text(text: str) -> str:
    """Normalize text for clean TTS reading in Reader.

    Em dashes create variable-length pauses depending on the TTS engine;
    replacing them with a comma-space gives consistent, natural phrasing.
    """
    return text.replace("—", ", ")


def text_to_html_paras(text: str) -> str:
    """Convert multi-line block text to <p> tags."""
    cleaned = normalize_reader_text(strip_stage(text))
    result = []
    current: list[str] = []
    for line in cleaned.splitlines():
        if line.strip():
            current.append(line.strip())
        else:
            if current:
                result.append("<p>" + " ".join(current) + "</p>")
                current = []
    if current:
        result.append("<p>" + " ".join(current) + "</p>")
    return "\n".join(result)


def load_track(path: Path) -> dict:
    with open(path) as f:
        doc = yaml.safe_load(f)
    return doc


def chapter_html(doc: dict, track_type: str, cat_label: str) -> str:
    """Build the XHTML body content for one track chapter."""
    title = doc.get("title", "")
    source = doc.get("source", "")
    duration = TRACK_DURATION.get(track_type, "")

    blocks_html_parts: list[str] = []

    if track_type == "daytime":
        # Daytime: render as a drill list — statements once each (Reader reads
        # through; the 3× repetition is the audio track's job).
        statements: list[str] = []
        for block in doc.get("blocks", []):
            paras = text_to_html_paras(block.get("text", ""))
            if paras:
                statements.append(paras)

        blocks_html_parts.append('<div class="drill">')
        for stmt in statements:
            blocks_html_parts.append('<div class="stmt">' + stmt + '</div>')
        blocks_html_parts.append('</div>')

        # Synthesis coda
        synthesis = doc.get("synthesis")
        if synthesis:
            syn_html = text_to_html_paras(synthesis.get("text", ""))
            if syn_html:
                blocks_html_parts.append('<hr class="coda-rule"/>')
                blocks_html_parts.append('<div class="synthesis">')
                blocks_html_parts.append('<p class="coda-label">Synthesis</p>')
                blocks_html_parts.append(syn_html)
                blocks_html_parts.append('</div>')

    else:
        # Morning / evening: continuous prose
        for block in doc.get("blocks", []):
            html = text_to_html_paras(block.get("text", ""))
            if html:
                blocks_html_parts.append(html)

    blocks_html = "\n".join(blocks_html_parts)

    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE html>
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
        <head>
          <meta charset="UTF-8"/>
          <title>{_esc(title)}</title>
          <link rel="stylesheet" type="text/css" href="../style.css"/>
        </head>
        <body>
          <div class="chapter">
            <h1>{_esc(title)}</h1>
            <div class="content">
        {blocks_html}
            </div>
          </div>
        </body>
        </html>
    """)


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))


# ── EPUB assembly ──────────────────────────────────────────────────────────────

STYLESHEET = """\
body {
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1em;
  line-height: 1.7;
  margin: 0 auto;
  max-width: 36em;
  padding: 1.5em 1em;
  color: #1a1a1a;
}
h1 {
  font-size: 1.4em;
  font-weight: normal;
  margin: 0.2em 0 0.3em;
  line-height: 1.25;
}
p { margin: 0 0 0.9em; }
.content { margin-top: 1.5em; }

/* Daytime drill */
.drill { margin-top: 1.5em; }
.stmt {
  border-left: 2px solid #ccc;
  padding-left: 1em;
  margin-bottom: 1.4em;
}
.stmt p { margin: 0; }
hr.coda-rule {
  border: none;
  border-top: 1px solid #ddd;
  margin: 2em 0;
}
.synthesis { margin-top: 1em; }
.coda-label {
  font-size: 0.72em;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #888;
  margin-bottom: 1em;
}
"""

CONTAINER_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def build_opf(book_title: str, chapters: list[dict], book_uid: str) -> str:
    today = date.today().isoformat()
    manifest_items = [
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '    <item id="css" href="style.css" media-type="text/css"/>',
    ]
    spine_items = []
    for ch in chapters:
        cid = ch["id"]
        manifest_items.append(
            f'    <item id="{cid}" href="chapters/{cid}.xhtml" media-type="application/xhtml+xml"/>'
        )
        spine_items.append(f'    <itemref idref="{cid}"/>')

    manifest_str = "\n".join(manifest_items)
    spine_str = "\n".join(spine_items)

    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" xml:lang="en">
          <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
            <dc:title>{_esc(book_title)}</dc:title>
            <dc:language>en</dc:language>
            <dc:identifier id="uid">{book_uid}</dc:identifier>
            <dc:creator>Self-Talk Library</dc:creator>
            <meta property="dcterms:modified">{today}T00:00:00Z</meta>
          </metadata>
          <manifest>
        {manifest_str}
          </manifest>
          <spine toc="ncx">
        {spine_str}
          </spine>
        </package>
    """)


def build_nav(book_title: str, chapters: list[dict],
              by_category: bool = True) -> str:
    """EPUB 3 nav document. If by_category, nests tracks under category headings."""
    if by_category:
        # Group into nested ol
        from collections import defaultdict
        groups: dict[str, list[dict]] = {}
        group_order: list[str] = []
        for ch in chapters:
            cat = ch.get("cat_label", "")
            if cat not in groups:
                groups[cat] = []
                group_order.append(cat)
            groups[cat].append(ch)

        items = []
        for cat in group_order:
            chs = groups[cat]
            sub = "\n".join(
                f'          <li><a href="chapters/{ch["id"]}.xhtml">{_esc(ch["label"])}</a></li>'
                for ch in chs
            )
            items.append(
                f'        <li><span>{_esc(cat)}</span>\n          <ol>\n{sub}\n          </ol>\n        </li>'
            )
        toc_items = "\n".join(items)
    else:
        toc_items = "\n".join(
            f'        <li><a href="chapters/{ch["id"]}.xhtml">{_esc(ch["label"])}</a></li>'
            for ch in chapters
        )

    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE html>
        <html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
        <head>
          <meta charset="UTF-8"/>
          <title>{_esc(book_title)}</title>
        </head>
        <body>
          <nav epub:type="toc" id="toc">
            <h1>Contents</h1>
            <ol>
        {toc_items}
            </ol>
          </nav>
        </body>
        </html>
    """)


def build_ncx(book_title: str, chapters: list[dict], book_uid: str) -> str:
    """EPUB 2 NCX for backward compat."""
    nav_points = []
    for i, ch in enumerate(chapters, 1):
        nav_points.append(textwrap.dedent(f"""\
            <navPoint id="np{i}" playOrder="{i}">
              <navLabel><text>{_esc(ch["label"])}</text></navLabel>
              <content src="chapters/{ch['id']}.xhtml"/>
            </navPoint>"""))
    nav_str = "\n".join(nav_points)

    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
          <head>
            <meta name="dtb:uid" content="{book_uid}"/>
            <meta name="dtb:depth" content="1"/>
          </head>
          <docTitle><text>{_esc(book_title)}</text></docTitle>
          <navMap>
        {nav_str}
          </navMap>
        </ncx>
    """)


def write_epub(out_path: Path, book_title: str, chapters: list[dict],
               chapter_htmls: dict[str, str], by_category: bool = True) -> None:
    """Write a complete EPUB 3 file."""
    book_uid = str(uuid.uuid4())
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype must be first and uncompressed
        zf.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip",
                    compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", CONTAINER_XML)
        zf.writestr("OEBPS/style.css", STYLESHEET)
        zf.writestr("OEBPS/content.opf", build_opf(book_title, chapters, book_uid))
        zf.writestr("OEBPS/nav.xhtml",   build_nav(book_title, chapters, by_category))
        zf.writestr("OEBPS/toc.ncx",     build_ncx(book_title, chapters, book_uid))
        for ch in chapters:
            zf.writestr(f"OEBPS/chapters/{ch['id']}.xhtml", chapter_htmls[ch["id"]])

    size_kb = out_path.stat().st_size // 1024
    print(f"  {out_path.name}  ({len(chapters)} chapters, {size_kb} KB)")


# ── build helpers ──────────────────────────────────────────────────────────────

def collect_chapters(track_filter: str | None = None) -> tuple[list[dict], dict[str, str]]:
    """
    Return (chapters metadata list, {id: xhtml string}) for the requested
    track types. track_filter=None means all three.
    """
    chapters: list[dict] = []
    htmls: dict[str, str] = {}

    for cat_slug, cat_label in CATEGORIES:
        cat_dir = CONTENT_DIR / cat_slug
        for track_type, filename, track_label in TRACK_FILES:
            if track_filter and track_type != track_filter:
                continue
            yaml_path = cat_dir / filename
            if not yaml_path.exists():
                print(f"  missing: {yaml_path}")
                continue

            doc = load_track(yaml_path)
            slug = doc.get("slug", f"{cat_slug}-{track_type}")
            title = doc.get("title", f"{cat_label} — {track_label}")
            chap_id = slug.replace("-", "_")
            label = title

            chapters.append({
                "id": chap_id,
                "label": label,
                "cat_label": cat_label,
                "track_type": track_type,
                "slug": slug,
            })
            htmls[chap_id] = chapter_html(doc, track_type, cat_label)

    return chapters, htmls


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--type", choices=["morning", "daytime", "evening"],
                        help="generate a single-track-type EPUB only")
    parser.add_argument("--combined", action="store_true",
                        help="generate the combined EPUB only")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output: {OUT_DIR}\n")

    if args.type:
        # Single track type
        label_map = {"morning": "Morning", "daytime": "Daytime Drill", "evening": "Evening"}
        chapters, htmls = collect_chapters(track_filter=args.type)
        title = f"Self-Talk — {label_map[args.type]}"
        write_epub(OUT_DIR / f"selftalk-{args.type}.epub", title, chapters, htmls,
                   by_category=True)

    elif args.combined:
        # Combined only
        chapters, htmls = collect_chapters()
        write_epub(OUT_DIR / "selftalk-library.epub",
                   "Self-Talk Library", chapters, htmls, by_category=True)

    else:
        # All four: combined + three per-type
        print("Combined:")
        chapters, htmls = collect_chapters()
        write_epub(OUT_DIR / "selftalk-library.epub",
                   "Self-Talk Library", chapters, htmls, by_category=True)

        print("\nPer track type:")
        for tt, _, lbl in TRACK_FILES:
            chs, hts = collect_chapters(track_filter=tt)
            write_epub(OUT_DIR / f"selftalk-{tt}.epub",
                       f"Self-Talk — {lbl}", chs, hts, by_category=False)

    print("\nDone.")


if __name__ == "__main__":
    main()
