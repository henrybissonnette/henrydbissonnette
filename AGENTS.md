# Working on Henry's website

Read [README.md](README.md) and [docs/project-state.md](docs/project-state.md)
first. For visual work, read [design-guide/README.md](design-guide/README.md),
then its visual system and implementation brief. Current instructions from
Henry take precedence over historical notes and generated mockup copy.

## Project culture

- Preserve Henry's voice. Port essays faithfully, including headings, emphasis,
  hyperlinks, and original dates. Propose editorial changes separately.
- Keep the technology/life convergence and the selected Chromatic Morphogenesis
  identity. Living complexity belongs around clear content and usable controls.
- Use the reference images to judge visual quality. Generated artwork is part
  of the production approach; schematic SVG substitutes have failed to capture
  the desired richness. Real text and controls remain HTML.
- Long essays must work at any length: frame the header and footer with artwork,
  leaving the middle quiet. Check wide desktop and narrow mobile layouts.
- Keep implementation small. Today this is a static site without a build step;
  dynamic applications are a future intention, not a prohibition or a reason
  to introduce a framework before there is a concrete need.
- Inspect local changes before editing. Other agents and Henry may have work in
  the same checkout. Preserve unrelated work and avoid blanket staging.

## Checks and publication

Run `python3 scripts/check_site.py` and
`python3 -m unittest discover -s tests -v` for site changes. Review rendered
pages at desktop and mobile widths for layout changes. Infrastructure changes
also need `scripts/check_infrastructure.sh`; see the AWS docs before modifying
hosting. A push to `main` starts the existing deployment workflow.

## Git commit discipline

In an LFS-managed checkout, inspect `git config --get lfs.mainlineGuard`.
When enforcement is enabled, use the installed managed authority:

```sh
lfs git commit --expect-head <full-current-HEAD> \
  --message "Describe the change" --path <changed-file> --path <another-file>
```

Use `lfs git commit --help` for the installed version's identity requirements;
host-side/manual commits identify their author as Hostside Codex, not Henry or
an internal LFS agent. Do not bypass the reference-transaction guard. A normal
clone without this guard can use ordinary scoped Git commits. Fetch before
publishing; reconcile new remote work and push without forcing history.

Do not commit nested `.tracks/`, `.lfs-*-lanes/`, or dispatch worktrees. These
are local LFS machinery, not project content. Keep credentials, Terraform state,
plans, and runtime logs out of Git.

## Leave shared memory

Update [docs/project-state.md](docs/project-state.md) after a meaningful change:
date, result, relevant files, verification, and any unfinished next step. Keep
open ideas distinct from approved work. Update an existing design or technical
guide when a decision changes; link it rather than copying it into several
places. Git history supplies detailed chronology, so keep the handoff concise.
