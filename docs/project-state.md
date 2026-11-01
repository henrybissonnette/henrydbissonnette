# Project state and handoff

Last updated: **2026-11-01**, by Hostside Codex with Henry's authorization, then
by Claude for the Holmes–Balwani texts.
This describes the source prepared for the November handoff; it is not proof
of a successful production deployment. GitHub Actions is the deployment record.

## Purpose and collaboration

Henry wants an intellectual home and a place to host his engineering projects,
including future applications that run code and access databases. AI is central,
connected to many fields by an interest in universal transcendence and the
convergence of nature and technology. See the
[conversation synthesis](../design-guide/conversation-synthesis.md) for the
full conceptual direction.

Most work has been coordinated through Living File System (LFS), Henry's agent
development system. The website is an **extraverted** project: its target is this
repository, not the LFS framework. Framework/control-plane changes belong in
the separate LFS project. Hostside Codex has also worked directly here,
particularly on visual design, browser review, generated assets, and content.
Other machines do not need a running LFS system to preview or edit this static
site. Tool capabilities differ by agent and account; do not assume a tool from
one session exists elsewhere. Reuse committed assets when generation is absent.

## Current implementation

- `site/` contains nine HTML pages, a shared stylesheet plus one page stylesheet
  (`holmes-texts.css`), local images, and one small favicon-preview script.
  There is no build step or application backend.
- Navigation: About, Essays, Projects, Contact. The homepage and archive contain
  local copy refinements included in this handoff: “Understanding the world,”
  “Longer reflections,” “Reporting my findings,” and the homepage “Reach out.”
- `site/styles/main.css` is the actual token/layout source. The token file in
  the design guide is provisional and is not imported into production.
- AWS hosting uses the checked-in Terraform and GitHub Actions workflow. See
  [deployment](aws-deployment.md) and [infrastructure](aws-infrastructure.md).
  Do not replace the deployment mechanism as a side effect of UI work.
- Only `site/` is deployed. References, prompts, and this handoff stay in Git.

## Content and provenance

**You Must Solve Problems** (`site/you-must-solve-problems.html`) reproduces
Henry's April 2011 Mathematics Stack Exchange answer, its question, and comments.
It is Math Stack Exchange, despite occasional conversational references to
Stack Overflow. Five screenshot segments are joined with explicit overlap trims;
an expandable transcript provides accessible text. Preserve source attribution
and CC BY-SA links. Capture instructions and originals are in
[`design-guide/assets/editorial-captures/`](../design-guide/assets/editorial-captures/math-stackexchange-formulas-answer-33987/README.md).

**The Holmes–Balwani Texts** (`site/holmes-balwani-texts.html`, linked from
the Projects grid as 04 · Records) is a reading edition of the seven
text-message exhibits (5387A–G) from *United States v. Holmes*, set out as
conversations with a note on how each exhibit and exchange was used at trial.
The court posted the exhibits as image-only scans; Claude transcribed them (a
model reading each row, checked against OCR and re-checked where they
disagreed) and drafted the notes from the transcripts, filings and news reports
listed on the page. The page says so, calls itself unofficial, and links every
conversation to its page of the court's scan. It was generated once outside this
repository and is checked in as finished HTML: corrections are direct edits.
It uses the essay frame (`page-essay`) with the essay art, Projects navigation,
and its own `styles/holmes-texts.css`. The check requires the court's exhibit
folder and the source for Balwani's denial of Holmes's abuse allegations to stay
linked. Added at Henry's request on November 1, 2026.

**Phase Shift** (`site/phase-shift.html`), subtitle *Enter the Entrepreneurial
Age*, was ported from Henry's Google Doc with that exact title, not the separate
“Phase Shift (Anna)” version. Henry supplied **May 2012** as the original date;
the Google file's later creation date is not the essay date. The port preserves
25 body paragraphs, four section headings, and the three inline links to the
Economist, Huffington Post, and Atlantic. Their original URLs were preserved;
the checks verify their presence, not that these old external destinations
still work. The Google Doc was not edited. Source document ID for authorized
future reconciliation: `1eFiVAHMh_-dBPIXhNMCxwJ_QvDzMw2rQqBS7jgWpCEs`.

## Visual decisions carried forward

- **06 — Chromatic Morphogenesis** remains the selected direction. Studies
  01–03 were admired; 03's terrarium had particular emotional resonance. Later
  studies 07–09 were too messy. Studies 10–14 show possible page families;
  their content and controls are examples, not an approved feature backlog.
- Use peach/bone clearings, ink text, coral-to-violet cellular fields turning
  into graphs, dotted navigation, and the black multicolor topic footer.
  Avoid fake pointer/callout lines, literal animals, generic sci-fi motifs,
  and visual noise behind prose.
- Generated text-free raster fields already live in `site/images/`. The mockup
  PNGs in `design-guide/reference-images/` are references, not deployable pages.
- Essay backgrounds now use separate top and bottom layers sized to page width.
  They must not stretch over the full article height or disappear when the
  transcript expands. Phase Shift adds a quiet serif reading surface using the
  shared essay frame.
- The homepage topic band now ends in **CULTURE**. Other pages still end in
  **LEARNING**. This handoff preserves the existing local difference and validates
  each; deciding whether to make CULTURE global remains open.
- The favicon rotates randomly among four cropped **Living H round 3** candidates
  per page load. Each received the same crop to leave a thin margin. Henry has
  not selected a final icon. Earlier options remain historical; the round-3
  README's recommendation of option 02 is an agent recommendation, not approval.

## Recent work and validation

- August 2026: selected the visual system, generated page art and favicon
  studies, added the captured mathematics essay, and improved its responsive
  top/footer framing (commit `81da6f7`).
- August 2026: added Phase Shift and its archive entry. At implementation time,
  desktop and mobile visual review and 30 Python tests passed.
- November 2026: collected previously local prompts, alternative/page-family
  references, favicon sources/previews, and exploration history into Git;
  introduced the root README, AGENTS instructions, and this handoff. Reconciled
  validation with the existing homepage CULTURE edit. Local preview uses the
  root README command on port 4173; server processes are machine-local.
  Validation: site check, all 30 Python tests, and local Markdown links passed.
  The full infrastructure script passed in the existing Linux LFS image
  (Terraform validation, two mocked Terraform tests, 13 edge-redirect tests).
  Its cached tool binaries are Linux executables and cannot run directly on
  macOS; use Linux/CI for that check. No infrastructure source changed.
- November 1, 2026 (Claude, on Henry's Windows machine): added The
  Holmes–Balwani Texts, its Projects card (04 · Records, a cobalt band that
  completes the grid), its page check and a test. Reviewed at 1024 px desktop
  and 375 px mobile in a local preview: no horizontal overflow, the exhibit list
  stays in view beside the threads, no broken in-page links. Site check passed
  (nine pages); 30 of 31 Python tests passed. The exception,
  `test_all_operation_traces_have_fixed_authority`, also fails on unchanged
  `main` under Windows, which has no POSIX file modes; CI runs on Linux.

## Next work / unresolved choices

1. Incorporate the work Henry is developing with another agent on another
   machine. The first piece, The Holmes–Balwani Texts, was integrated on
   November 1, 2026. Integrate anything further the same way: pull this
   handoff, compare against the shared design guide, and preserve existing
   prose and source links.
2. Choose a final favicon after Henry has experienced the rotating candidates.
   Optimize the chosen silhouette at actual tab sizes; retain its living quality.
3. Decide whether CULTURE replaces LEARNING everywhere, and refine remaining
   homepage/about/project copy with Henry. Do not publish mockup inventions as
   facts or invent essays to fill out the archive.
4. Add project case studies or dynamic applications when there is a concrete
   project to present. Database/server needs will require explicit architecture
   work beyond the current static publication.
5. Fonts, motion, portraits, and richer interactions remain future design
   choices. Preserve a complete accessible static experience as those evolve.

For the next handoff, revise the relevant section above and add a dated result
with verification and remaining work. Keep deep technical instructions in their
existing guides, and do not paste private chats, credentials, or machine state.
