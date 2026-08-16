# Visual system

## North star

Build a site whose structure is intellectually rigorous and whose visual world
is alive enough to escape complete control. It should feel contemporary and
aspirational without borrowing old visions of the future.

The core tension is:

> disciplined editorial clarity inside an ecology of emergent form

The visual quality is a product requirement, not optional decoration. The site
should feel thoroughly designed, bespoke, luxurious, sumptuous, ornate, and
baroquely deep—as though its level of detail would be impractical to construct
by hand. Use AI image generation deliberately where it enables that finish.
Accessibility and performance are delivery constraints to solve without
cheapening the art direction.

## Design grammar

### Ground and clearing

Use a luminous peach/bone field as the ordinary environment. Important copy
lives in calm, mostly untextured clearings. Negative space is active: it gives
the living structures room to grow and the reader room to think.

Do not fill every viewport. A page may be visually ambitious while leaving
half of its area quiet.

### Cellular-to-graph transition

The signature motif is a continuous phase transition:

1. large cellular membranes or colonies;
2. progressively smaller cells near an ecotone;
3. particles or nuclei detach;
4. particles become graph nodes;
5. sparse edges expose computational structure.

The motif should read simultaneously as tissue, culture, computation, and
emergence. Avoid literal organs, brains, leaves with circuits, or geographic
maps.

On an ordinary content page, use one or two edge territories. On an
interactive page, the cellular field may become the content itself. Never use
complex motif art behind body copy.

### Graph meaning

Graph-like structures can be decorative at low contrast near a boundary, but
prominent graphs must carry meaning. In technical diagrams, every strong node,
edge, axis, or label should correspond to real information.

Decorative leader lines, target dots, map pins, fake telemetry, and arbitrary
indicators are prohibited.

### Navigation dots

Small colored dots beside global navigation labels are a selected signature.
They can reinforce section identity:

- Essays — coral.
- Projects — violet.
- Notes — blue.
- About — ink or moss.

Dots supplement labels; they never replace them or carry state alone. Active,
hover, and focus treatments must remain distinguishable without color.

### Topic band

The black band with large multicolored topic names is another selected
signature. The canonical sequence is:

`AI • COMPUTATION • LIFE • PHILOSOPHY • LEARNING`

It may operate as a footer, topic navigator, or contextual boundary between
sections. Keep it intentional and spacious. Do not turn it into a stock ticker
or animate it continuously without purpose.

## Typography

Use roles rather than blindly copying generated letterforms:

- **Display grotesk:** condensed or space-efficient, assertive, used for the
  name, page titles, project names, numbers, and UI labels.
- **Editorial serif:** warm and highly readable, used for essay titles, decks,
  body copy, reflective statements, and select project descriptions.
- **UI sans/mono:** optional and restrained for controls, metadata, dates, and
  technical annotations.

Provisional open-source candidates for testing are Barlow Condensed or Archivo
Narrow for display, Newsreader or Source Serif 4 for editorial text, and Inter
or the system sans stack for controls. This is not a final font decision.

Display scale should be bold, but body measures remain conservative: roughly
55–75 characters per line, generous line height, and no texture behind text.

## Color

Use `assets/design-tokens.css` as a provisional starting point. The palette is
ecological rather than a simple warm/cool binary:

- warm ground and black text;
- coral/vermilion for energy and origin;
- violet/cobalt/blue for abstraction and graph structure;
- turquoise, gold, and moss for diversity and secondary cultures.

Do not flatten the identity into the familiar purple-blue startup gradient.
Use discrete pigment-like territories, translucent boundaries, and stippled
transitions.

## Page behavior

### Homepage

Allow the cellular territories to dominate the lower edges while a central
clearing carries a concise statement. Preserve the strong name, dotted nav,
and topic band. Do not copy fabricated labels from the mockup. Prefer newly
generated, site-specific raster fields informed by the selected references;
never ship the reference mockups themselves or generated interface text.

### Essay

Prioritize reading. Keep the cellular motif in the margins and allow the
article to become visually quieter as the reader moves down-page. Pull quotes
may use coral or violet, but avoid magazine-like decoration.

### Archive

Prefer aligned editorial rows over cards. Subject filters use labels and dots.
Spacing, rules, and type hierarchy do most of the organizational work.

### Projects

Treat projects as substantial systems, not product tiles. Use bands, numbers,
short descriptions, status, and clear links. Each project may have a distinct
territorial color while remaining in one system.

### Technical case study

Turn the cellular-to-graph transition into real explanatory structure. Label
actual stages and components. Decorative life should not make architecture
harder to inspect.

### Interactive application

Keep controls, canvas, and analytics clearly separated without enclosing
everything in rounded SaaS cards. The living field may be interactive state.
Charts use the same spectrum and must remain interpretable independently of
color.

## Motion

Motion should suggest metabolism, permeability, and learning rather than
spectacle:

- slow boundary drift;
- occasional cell division or absorption;
- graph nodes appearing as cells disperse;
- subtle local response to pointer or scroll;
- state transitions with continuity rather than explosions.

Avoid ambient particle storms, perpetual ticker motion, parallax for its own
sake, and motion behind text. Honor `prefers-reduced-motion` with a complete
static composition rather than a degraded blank state.

## Responsive behavior

- Content remains primary; decorative territories may crop, simplify, or
  disappear.
- Do not shrink desktop art until text becomes illegible.
- Convert side navigation to a clear accessible menu.
- Let archive and project rows stack semantically.
- Let the topic band wrap into two or more deliberate rows on small screens.
- Interactive applications should move controls into a drawer or stacked
  section while keeping essential state visible.

## Accessibility

- Meet WCAG AA contrast for all text and controls.
- Never communicate category, state, or graph series by color alone.
- Provide visible keyboard focus that is not merely a color change.
- Use semantic landmarks and headings; maintain logical reading order when art
  is removed.
- Mark decorative SVG/canvas layers as hidden from assistive technology.
- Provide text alternatives or summaries for meaningful diagrams.
- Keep touch targets at least 44 by 44 CSS pixels.
- Test 200% zoom, reduced motion, forced colors, and common color-vision
  deficiencies.

## Anti-patterns

Avoid:

- cyberpunk, vaporwave, retrofuturism, steampunk, and chrome;
- robots, android faces, glowing brains, Matrix code, and circuit-board leaves;
- generic purple-blue gradients and glossy startup blobs;
- meaningless HUDs, telemetry, callouts, targets, or diagram furniture;
- animal or botanical literalism that weakens the metaphor;
- sterile monastic geometry as the dominant visual world;
- old blueprint aesthetics;
- generic SaaS cards, excessive glassmorphism, and admin-dashboard density;
- generated-image text or entire screenshot mockups shipped as UI.
