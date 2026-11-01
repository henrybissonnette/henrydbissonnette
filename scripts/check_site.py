#!/usr/bin/env python3
"""Validate the checked-in static publication without network access."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


REQUIRED_PAGES = (
    "index.html",
    "about.html",
    "essays.html",
    "you-must-solve-problems.html",
    "phase-shift.html",
    "projects.html",
    "holmes-balwani-texts.html",
    "contact.html",
    "404.html",
)
REQUIRED_ASSETS = (
    "styles/main.css",
    "styles/holmes-texts.css",
    "images/favicon.svg",
    "images/morphogenesis-home-generated.png",
    "images/morphogenesis-home-mobile-generated.png",
    "images/morphogenesis-about-generated.png",
    "images/morphogenesis-about-mobile-generated.png",
    "images/morphogenesis-projects-generated.png",
    "images/morphogenesis-projects-mobile-generated.png",
    "images/morphogenesis-contact-generated.png",
    "images/morphogenesis-contact-mobile-generated.png",
    "images/morphogenesis-essays-generated.png",
    "images/morphogenesis-essays-mobile-generated.png",
    "images/morphogenesis-essay-problems-v2-generated.png",
    "images/morphogenesis-essay-problems-v2-mobile-generated.png",
    "images/morphogenesis-404-generated.png",
    "images/morphogenesis-404-mobile-generated.png",
    "images/essay-you-must-solve-problems/segment-01-title-and-question.png",
    "images/essay-you-must-solve-problems/segment-02-answer-opening.png",
    "images/essay-you-must-solve-problems/segment-03-answer-development.png",
    "images/essay-you-must-solve-problems/segment-04-answer-conclusion.png",
    "images/essay-you-must-solve-problems/segment-05-comments.png",
    "scripts/favicon-preview.js",
)
LANDMARKS = ("header", "nav", "main", "footer")
APEX = "https://henrybissonnette.com"
TOPICS = ("AI", "COMPUTATION", "LIFE", "PHILOSOPHY", "LEARNING")
HOME_TOPICS = (*TOPICS[:-1], "CULTURE")
ESSAY_CAPTURE_SEGMENTS = tuple(
    f"images/essay-you-must-solve-problems/segment-{number:02d}-{name}.png"
    for number, name in (
        (1, "title-and-question"),
        (2, "answer-opening"),
        (3, "answer-development"),
        (4, "answer-conclusion"),
        (5, "comments"),
    )
)
ESSAY_CAPTURE_STYLES = (
    "--panel-aspect: 766 / 587; --crop-y: 0%;",
    "--panel-aspect: 766 / 534; --crop-y: -18.721461%;",
    "--panel-aspect: 766 / 593; --crop-y: -9.741248%;",
    "--panel-aspect: 766 / 593; --crop-y: -9.741248%;",
    "--panel-aspect: 766 / 421; --crop-y: -13.195876%;",
)


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

        nav_dots = [
            attrs
            for attrs in document.attrs.get("span", [])
            if "nav-dot" in (attrs.get("class") or "").split()
        ]
        if len(nav_dots) != 4 or any(attrs.get("aria-hidden") != "true" for attrs in nav_dots):
            errors.append(
                f"site/{relative}: expected four aria-hidden navigation dots; found {len(nav_dots)}"
            )

        topic_bands = [
            attrs
            for attrs in document.attrs.get("div", [])
            if "topic-band" in (attrs.get("class") or "").split()
        ]
        topic_words = [
            attrs
            for attrs in document.attrs.get("span", [])
            if "topic-word" in (attrs.get("class") or "").split()
        ]
        if (
            len(topic_bands) != 1
            or topic_bands[0].get("role") != "group"
            or topic_bands[0].get("aria-label") != "Topics"
        ):
            errors.append(f"site/{relative}: expected one topic band labelled Topics")
        expected_topics = HOME_TOPICS if relative == "index.html" else TOPICS
        if [attrs.get("data-topic") for attrs in topic_words] != list(expected_topics):
            errors.append(
                f"site/{relative}: topic band must contain the canonical sequence {' • '.join(expected_topics)}"
            )

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

        favicon_links = [
            attrs
            for attrs in document.attrs.get("link", [])
            if "icon" in (attrs.get("rel") or "").split()
        ]
        if (
            len(favicon_links) != 1
            or favicon_links[0].get("id") != "site-favicon"
            or favicon_links[0].get("href") != "images/favicon.svg"
        ):
            errors.append(
                f"site/{relative}: expected one site-favicon fallback link for the preview rotator"
            )

        scripts = document.attrs.get("script", [])
        if (
            len(scripts) != 1
            or scripts[0].get("src") != "scripts/favicon-preview.js"
            or "defer" not in scripts[0]
        ):
            errors.append(
                f"site/{relative}: expected exactly one deferred local favicon preview script"
            )

        if document.attrs.get("form"):
            errors.append(f"site/{relative}: forms are outside the static publication contract")

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

    essay = site_root / "you-must-solve-problems.html"
    if essay.is_file():
        document = parse_html(essay)
        capture_panels = [
            attrs
            for attrs in document.attrs.get("a", [])
            if "capture-panel" in (attrs.get("class") or "").split()
        ]
        capture_hrefs = tuple(attrs.get("href") for attrs in capture_panels)
        if capture_hrefs != ESSAY_CAPTURE_SEGMENTS:
            errors.append(
                "site/you-must-solve-problems.html: capture panels must link the five ordered native segments"
            )
        capture_styles = tuple(attrs.get("style") for attrs in capture_panels)
        if capture_styles != ESSAY_CAPTURE_STYLES:
            errors.append(
                "site/you-must-solve-problems.html: capture panels must preserve the pixel-registered overlap trims"
            )

        transcripts = [
            attrs
            for attrs in document.attrs.get("details", [])
            if "transcript" in (attrs.get("class") or "").split()
        ]
        if len(transcripts) != 1:
            errors.append(
                "site/you-must-solve-problems.html: expected one accessible transcript disclosure"
            )

        external_links = {
            attrs.get("href")
            for attrs in document.attrs.get("a", [])
            if (attrs.get("href") or "").startswith(("http://", "https://"))
        }
        required_attribution_links = {
            "https://math.stackexchange.com/questions/33656/whats-better-strategy-to-handle-tons-of-formulas-definitions/33987#33987",
            "https://creativecommons.org/licenses/by-sa/3.0/",
            "https://stackoverflow.com/help/licensing",
        }
        if not required_attribution_links.issubset(external_links):
            errors.append(
                "site/you-must-solve-problems.html: source and CC BY-SA attribution links are incomplete"
            )

    phase_shift = site_root / "phase-shift.html"
    if phase_shift.is_file():
        document = parse_html(phase_shift)
        external_links = {
            attrs.get("href")
            for attrs in document.attrs.get("a", [])
            if (attrs.get("href") or "").startswith(("http://", "https://"))
        }
        required_source_links = {
            "http://www.economist.com/blogs/graphicdetail/2012/02/daily-chart-0",
            "http://www.huffingtonpost.com/robert-reich/worker-productivity_b_1315814.html",
            "http://www.theatlantic.com/magazine/archive/2012/01/making-it-in-america/8844/",
        }
        if not required_source_links.issubset(external_links):
            errors.append("site/phase-shift.html: source document hyperlinks are incomplete")

    texts = site_root / "holmes-balwani-texts.html"
    if texts.is_file():
        document = parse_html(texts)
        external_links = {
            attrs.get("href")
            for attrs in document.attrs.get("a", [])
            if (attrs.get("href") or "").startswith(("http://", "https://"))
        }
        required_record_links = {
            "https://files.cand.uscourts.gov/files/18-CR-258%20USA%20v.%20Holmes/",
            "https://www.cnbc.com/2021/08/28/elizabeth-holmes-plans-to-claim-at-trial-that-ex-boyfriend-and-theranos-business-partner-abused-her.html",
        }
        if not required_record_links.issubset(external_links):
            errors.append(
                "site/holmes-balwani-texts.html: the court's exhibit folder and the source for Balwani's denial must stay linked"
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
