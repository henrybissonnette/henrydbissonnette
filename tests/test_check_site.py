from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.check_site import validate_site


ROOT = Path(__file__).resolve().parents[1]


class CheckSiteTests(unittest.TestCase):
    def copy_site(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        destination = Path(temporary.name) / "site"
        shutil.copytree(ROOT / "site", destination)
        return temporary, destination

    def test_checked_in_site_passes(self) -> None:
        self.assertEqual(validate_site(ROOT / "site"), [])

    def test_broken_reference_reports_source_and_target(self) -> None:
        temporary, site = self.copy_site()
        self.addCleanup(temporary.cleanup)
        page = site / "about.html"
        page.write_text(
            page.read_text(encoding="utf-8").replace("styles/main.css", "styles/missing.css"),
            encoding="utf-8",
        )

        errors = validate_site(site)

        self.assertTrue(
            any("site/about.html" in error and "styles/missing.css" in error for error in errors),
            errors,
        )

    def test_missing_image_alt_reports_source(self) -> None:
        temporary, site = self.copy_site()
        self.addCleanup(temporary.cleanup)
        page = site / "index.html"
        page.write_text(page.read_text(encoding="utf-8").replace(' alt=""', "", 1), encoding="utf-8")

        errors = validate_site(site)

        self.assertTrue(any("site/index.html" in error and "alt text intent" in error for error in errors), errors)

    def test_path_escape_is_rejected(self) -> None:
        temporary, site = self.copy_site()
        self.addCleanup(temporary.cleanup)
        page = site / "projects.html"
        page.write_text(
            page.read_text(encoding="utf-8").replace("styles/main.css", "../../outside.css"),
            encoding="utf-8",
        )

        errors = validate_site(site)

        self.assertTrue(any("site/projects.html" in error and "escapes site/" in error for error in errors), errors)

    def test_secondary_page_requires_explicit_html_url(self) -> None:
        temporary, site = self.copy_site()
        self.addCleanup(temporary.cleanup)
        page = site / "index.html"
        page.write_text(
            page.read_text(encoding="utf-8").replace('href="about.html"', 'href="about"', 1),
            encoding="utf-8",
        )

        errors = validate_site(site)

        self.assertTrue(any("secondary page link 'about' must end in .html" in error for error in errors), errors)

    def test_external_image_dependency_is_rejected(self) -> None:
        temporary, site = self.copy_site()
        self.addCleanup(temporary.cleanup)
        page = site / "index.html"
        page.write_text(
            page.read_text(encoding="utf-8").replace("images/morphogenesis.svg", "https://cdn.example/morphogenesis.svg"),
            encoding="utf-8",
        )

        errors = validate_site(site)

        self.assertTrue(any("external asset dependency" in error for error in errors), errors)

    def test_missing_navigation_dot_reports_page(self) -> None:
        temporary, site = self.copy_site()
        self.addCleanup(temporary.cleanup)
        page = site / "about.html"
        page.write_text(
            page.read_text(encoding="utf-8").replace('class="nav-dot nav-dot-about"', 'class="nav-dot-about"'),
            encoding="utf-8",
        )

        errors = validate_site(site)

        self.assertTrue(any("site/about.html" in error and "navigation dots" in error for error in errors), errors)

    def test_changed_topic_sequence_reports_page(self) -> None:
        temporary, site = self.copy_site()
        self.addCleanup(temporary.cleanup)
        page = site / "404.html"
        page.write_text(
            page.read_text(encoding="utf-8").replace('data-topic="PHILOSOPHY"', 'data-topic="THOUGHT"'),
            encoding="utf-8",
        )

        errors = validate_site(site)

        self.assertTrue(any("site/404.html" in error and "canonical sequence" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
