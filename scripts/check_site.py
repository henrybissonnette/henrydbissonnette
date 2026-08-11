#!/usr/bin/env python3
"""Validate the checked-in static publication without network access."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


REQUIRED_PAGES = ("index.html", "about.html", "projects.html", "contact.html", "404.html")
REQUIRED_ASSETS = ("styles/main.css", "images/favicon.svg", "images/workbench.svg")
LANDMARKS = ("header", "nav", "main", "footer")
APEX = "https://henrybissonnette.com"


@dataclass
class Document:
    attrs: dict[str, list[dict[str, str | None]]] = field(default_factory=dict)
    references: list[tuple[str, str, str]] = field(default_factory=list)
    headings: list[tuple[int, str]] = field(default_factory=list)
    title_parts: list[str] = field(default_factory=list)
    _heading_level: int | None = None
    _heading_parts: list[str] = field(default_factory=list)
    _in_title: bool = False


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.document = Document()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.document.attrs.setdefault(tag, []).append(values)
        for name in ("href", "src"):
            if name in values and values[name] is not None:
                self.document.references.append((tag, name, values[name] or ""))
        if tag == "title":
            self.document._in_title = True
        if len(tag) == 2 and tag[0] == "h" and tag[1].isdigit():
            self.document._heading_level = int(tag[1])
            self.document._heading_parts = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.document._in_title = False
        if self.document._heading_level is not None and tag == f"h{self.document._heading_level}":
            text = " ".join("".join(self.document._heading_parts).split())
            self.document.headings.append((self.document._heading_level, text))
            self.document._heading_level = None
            self.document._heading_parts = []

    def handle_data(self, data: str) -> None:
        if self.document._in_title:
            self.document.title_parts.append(data)
        if self.document._heading_level is not None:
            self.document._heading_parts.append(data)


def canonical_for(relative: str) -> str:
    return f"{APEX}/" if relative == "index.html" else f"{APEX}/{relative}"


def parse_html(path: Path) -> Document:
    parser = SiteParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser.document


def local_target(site_root: Path, source: Path, raw_reference: str) -> tuple[Path | None, str | None]:
    parsed = urlsplit(raw_reference)
    if parsed.scheme or parsed.netloc:
        return None, None
    if not parsed.path:
        return None, None

    decoded = unquote(parsed.path)
    if "\\" in decoded or "\x00" in decoded:
        return None, "contains a forbidden path character"
    relative = decoded.lstrip("/") if decoded.startswith("/") else str(source.parent.relative_to(site_root) / decoded)
    candidate = (site_root / relative).resolve()
    try:
        candidate.relative_to(site_root.resolve())
    except ValueError:
        return None, "escapes site/"
    return candidate, None


def validate_site(site_root: Path) -> list[str]:
    site_root = site_root.resolve()
    errors: list[str] = []
    if not site_root.is_dir():
        return [f"{site_root}: deployable site directory does not exist"]

    for relative in (*REQUIRED_PAGES, *REQUIRED_ASSETS):
        if not (site_root / relative).is_file():
            errors.append(f"site/{relative}: required publication file is missing")

    for relative in REQUIRED_PAGES:
        path = site_root / relative
        if not path.is_file():
            continue
        try:
            document = parse_html(path)
        except (OSError, UnicodeError) as exc:
            errors.append(f"site/{relative}: cannot parse as UTF-8 HTML: {exc}")
            continue

        html_elements = document.attrs.get("html", [])
        if len(html_elements) != 1 or html_elements[0].get("lang") != "en":
            errors.append(f"site/{relative}: expected exactly one <html lang=\"en\">")

        title = " ".join("".join(document.title_parts).split())
        if not title:
            errors.append(f"site/{relative}: document <title> must be non-empty")

        for landmark in LANDMARKS:
            if len(document.attrs.get(landmark, [])) != 1:
                errors.append(f"site/{relative}: expected exactly one <{landmark}> landmark")

        h1s = [text for level, text in document.headings if level == 1 and text]
        if len(h1s) != 1:
            errors.append(f"site/{relative}: expected exactly one non-empty <h1>")
        previous = 0
        for level, text in document.headings:
            if not text:
                errors.append(f"site/{relative}: h{level} heading must not be empty")
            if previous and level > previous + 1:
                errors.append(f"site/{relative}: heading order skips from h{previous} to h{level}")
            previous = level

        canonicals = [
            attrs.get("href")
            for attrs in document.attrs.get("link", [])
            if "canonical" in (attrs.get("rel") or "").split()
        ]
        expected_canonical = canonical_for(relative)
        if canonicals != [expected_canonical]:
            errors.append(
                f"site/{relative}: canonical must be exactly {expected_canonical!r}; found {canonicals!r}"
            )

        if document.attrs.get("form"):
            errors.append(f"site/{relative}: forms are outside the static publication contract")
        if document.attrs.get("script"):
            errors.append(f"site/{relative}: scripts are outside this dependency-free publication")

        for image in document.attrs.get("img", []):
            source = image.get("src") or "<missing src>"
            if "alt" not in image:
                errors.append(f"site/{relative}: image {source!r} must declare alt text intent")
            elif image.get("alt") == "" and image.get("aria-hidden") != "true" and image.get("role") != "presentation":
                errors.append(
                    f"site/{relative}: decorative image {source!r} needs aria-hidden=\"true\" or role=\"presentation\""
                )

        for tag, attr, reference in document.references:
            parsed = urlsplit(reference)
            label = f"{tag}[{attr}]={reference!r}"
            if parsed.scheme == "mailto":
                continue
            if parsed.scheme and parsed.scheme not in {"http", "https"}:
                errors.append(f"site/{relative}: {label} uses unsupported URI scheme {parsed.scheme!r}")
                continue
            if (parsed.scheme or parsed.netloc) and (attr == "src" or tag == "link"):
                if reference != expected_canonical:
                    errors.append(f"site/{relative}: {label} is an external asset dependency")
                continue
            if parsed.scheme or parsed.netloc:
                continue
            target, problem = local_target(site_root, path, reference)
            if problem:
                errors.append(f"site/{relative}: {label} {problem}")
                continue
            if target is not None and not target.is_file():
                errors.append(f"site/{relative}: {label} resolves to missing {target.relative_to(site_root)!s}")

            if tag == "a" and parsed.path:
                decoded_path = unquote(parsed.path)
                destination = Path(decoded_path).name
                secondary_stems = {Path(page).stem for page in REQUIRED_PAGES[1:]}
                if destination in secondary_stems or (
                    target is not None
                    and target.is_file()
                    and target.name in REQUIRED_PAGES[1:]
                    and not decoded_path.endswith(".html")
                ):
                    errors.append(f"site/{relative}: secondary page link {reference!r} must end in .html")

    contact = site_root / "contact.html"
    if contact.is_file():
        document = parse_html(contact)
        mail_links = [ref for tag, attr, ref in document.references if tag == "a" and attr == "href" and ref.startswith("mailto:")]
        if mail_links != ["mailto:henrydbissonnette@gmail.com"]:
            errors.append(
                "site/contact.html: expected one curated mailto link to henrydbissonnette@gmail.com"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", nargs="?", type=Path, default=Path(__file__).resolve().parents[1] / "site")
    args = parser.parse_args(argv)
    errors = validate_site(args.site)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Static site check failed with {len(errors)} error(s).", file=sys.stderr)
        return 1
    file_count = sum(1 for path in args.site.rglob("*") if path.is_file())
    print(f"Static site check passed: {len(REQUIRED_PAGES)} pages, {file_count} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
