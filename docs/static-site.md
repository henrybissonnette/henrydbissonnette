# Static publication

`site/` is the complete deployable artifact for henrybissonnette.com. It is
checked in as exact HTML, CSS, and SVG bytes: there is no build step, package
installation, environment substitution, application server, or network input.
A static server or deployment job should publish that directory unchanged.

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
