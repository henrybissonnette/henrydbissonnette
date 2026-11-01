# LFS implementation brief

## Objective

Translate the selected Chromatic Morphogenesis direction into a maintainable,
responsive, accessible website system. Preserve the existing AWS ownership and
deployment boundaries. This guide steers UI work; it does not authorize
infrastructure redesign.

## Source hierarchy

When sources conflict, use this order:

1. Approved product requirements and current user instructions.
2. `conversation-synthesis.md` and the durable decisions in this guide.
3. `visual-system.md`.
4. Reference 06 and studies 10–14.
5. Secondary references 01–03.
6. Exploratory mockup copy and diagrams.

Mockup text is not a content database. Verify names, dates, claims, project
status, metrics, and links before publishing them.

## Recommended execution spine

1. **Establish tokens and primitives.** Adopt or refine the provisional color,
   type, spacing, rule, focus, and motion tokens. Create semantic page,
   masthead, navigation-dot, topic-band, editorial-row, and project-row
   primitives.
2. **Build a production visual field.** Use image generation with the selected
   studies as references to create new, text-free raster artwork with the
   density, material depth, and finish of the guide. Art-direct desktop and
   mobile crops separately. Keep content and interaction in semantic HTML/CSS;
   use SVG, Canvas, or WebGL only where they improve real behavior rather than
   as lower-fidelity substitutes for the flagship artwork.
3. **Rebuild the homepage.** Use 06 as the visual reference while replacing all
   exploratory copy with approved content.
4. **Build the reading system.** Implement the essay and archive patterns from
   10 and 11, including typography, metadata, focus behavior, and small-screen
   layouts.
5. **Build project storytelling.** Implement the project index and a reusable
   technical case-study pattern inspired by 12 and 13.
6. **Prove application compatibility.** Build a small interactive prototype in
   the 14 layout. The point is to validate that controls, charts, and canvas
   can share the site identity—not to publish fictional metrics.
7. **Harden and review.** Test responsive layouts, keyboard navigation,
   contrast, reduced motion, content zoom, performance, and exact static-site
   publication behavior.

## Implementation constraints

- Do not use the reference PNGs as page backgrounds or embedded interface
  screenshots. They are inputs for generating new site-specific production
  artwork, not production assets themselves.
- Prefer semantic HTML and CSS for content and layout.
- Use generated raster artwork for flagship visual surfaces when code-native
  motifs cannot match the reference quality. Generated art must contain no UI,
  labels, logos, or body copy; real content remains accessible HTML.
- Use Canvas/WebGL only when simulation scale or interaction makes it useful;
  provide a meaningful static fallback.
- Keep visual layers isolated from content and use responsive art direction at
  narrow breakpoints. Performance work should optimize delivery and cropping,
  not reduce the visual ambition or replace rich artwork with generic blobs.
- Avoid framework adoption solely for decorative motion. Introduce runtime code
  only when it provides real behavior.
- Keep the site's current deployment checks and exact publication contract
  green unless a separately approved change modifies them.

## Visual acceptance checks

At minimum, capture and review desktop and mobile screenshots for each new page.
The review should ask:

- Is there a clear, quiet content region?
- Is the cellular-to-graph transition recognizable without becoming noise?
- Are graph elements meaningful when visually prominent?
- Are the dotted navigation and topic band consistent?
- Does the page still work when decorative art is hidden?
- Are all interactive states clear without relying on color alone?
- Does the page avoid every anti-pattern in `visual-system.md`?

Compare desktop work to the references at a similar 16:10 viewport and compare
mobile work at matching narrow viewports. Judge not only component presence but
also material richness, density, asymmetry, hierarchy, atmosphere, and overall
finish. The site should feel bespoke, sumptuous, ornate, and futuristically
lavish—never like a schematic or inexpensive approximation.

## Favicon workflow

The four cropped Living H round-3 previews currently rotate on page load.
Henry has not selected a final icon. After he chooses one:

1. refine its silhouette and internal divisions, using vector or raster as
   appropriate to preserve both legibility and the selected living character;
2. test it at 16, 24, 32, 48, 180, and 512 pixels;
3. remove detail that muddies at 16 pixels;
4. verify it on light and dark browser chrome;
5. produce SVG plus required PNG/ICO variants;
6. update markup and tests through the normal LFS workflow.
