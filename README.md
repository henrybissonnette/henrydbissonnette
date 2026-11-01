# Henry Bissonnette's website

Personal essays and engineering projects at <https://henrybissonnette.com>.
The site explores artificial intelligence, computation, life, philosophy,
learning, economics, and culture. Its visual direction is **Chromatic
Morphogenesis**: living cellular territories becoming computational graphs,
with quiet space for reading.

## Run locally

From the repository root:

```sh
python3 -m http.server 4173 --bind 127.0.0.1 --directory site
```

Open <http://localhost:4173/>. No package install or build is needed. `site/`
is the complete static publication. Keep the server running while previewing.

## Start here when joining the project

- [AGENTS.md](AGENTS.md): working conventions for agents on any machine.
- [Current state and next work](docs/project-state.md): what exists, recent
  decisions, open choices, and how to leave a handoff.
- [Design guide](design-guide/README.md): visual principles, selected reference,
  exploration images, prompts, and favicon candidates.
- [Static site](docs/static-site.md): implementation and validation.
- [AWS deployment](docs/aws-deployment.md): publication and inspection workflow.
- [AWS infrastructure](docs/aws-infrastructure.md): architecture and ownership.
- [AWS prework](docs/aws-prework.md): historical bootstrap and domain setup.

## Validate and publish

```sh
python3 scripts/check_site.py
python3 -m unittest discover -s tests -v
```

For infrastructure changes, also run `scripts/check_infrastructure.sh` in Linux
(the pinned tool installer targets Linux; use a container or CI on macOS).
CI runs all three checks. A push to `main` triggers the AWS workflow and,
when the repository's bootstrap gate is enabled, deploys to production.
Pushing is therefore a publication action, not just backup. Publish only
`site/`; documentation, prompts, and source references are not public assets.

The repository is <https://github.com/henrybissonnette/henrydbissonnette>;
`main` is current and `master` is a legacy archive. A normal clone can use
ordinary Git. An LFS-managed checkout may enforce the scoped commit command
described in [AGENTS.md](AGENTS.md).
