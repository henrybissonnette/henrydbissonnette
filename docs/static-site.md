# Static publication

`site/` is the complete deployable artifact for henrybissonnette.com. It is
checked in as exact HTML, CSS, SVG, and JavaScript bytes: there is no build
step, package installation, environment substitution, application server, or
network input. A static server or deployment job should publish that directory
unchanged. The only client-side script is the temporary, dependency-free
favicon concept rotator used during product selection; it embeds four local
32-pixel cropped Living H round-3 previews and never fetches or persists data.
See [project state](project-state.md) for content provenance and open decisions.

Preview from the repository root with
`python3 -m http.server 4173 --bind 127.0.0.1 --directory site`, then open
<http://localhost:4173/>. This serves the current files without AWS or LFS.

## Adding an essay

Use `site/phase-shift.html` as the current prose-page example. Preserve the
author's text, embedded links, original date, and heading structure; adapt only
the presentation. Reuse the shared `.page-essay` frame and `.essay-prose`
reading styles, add an archive row to `site/essays.html`, and add the new page
to `REQUIRED_PAGES` in `scripts/check_site.py`. Set its title, description,
canonical URL, and active Essays navigation. Keep local page links explicit
with `.html`. For screenshot-based content, retain an accessible transcript
and any required attribution (see `you-must-solve-problems.html`).

## Validation

Run the durable source check from the repository root:

```sh
python3 scripts/check_site.py
python3 -m unittest discover -s tests -v
```

The checker uses only the Python standard library. It verifies required files,
page metadata and landmarks, heading and image-alt intent, the curated contact
path, and every local HTML `href`/`src`. References must resolve to files inside
`site/`; missing targets and path escapes fail with the source file and
offending reference in the diagnostic. Work is linear in the files and local
references in the one publication tree and leaves no persistent state.

These checks deliberately cover only source-visible contracts. Product copy
and asset selection, rendered responsive behavior, keyboard navigation,
visible focus, contrast, alternative-text quality, and live link behavior are
reviewed on the real staging endpoint before domain cutover.
