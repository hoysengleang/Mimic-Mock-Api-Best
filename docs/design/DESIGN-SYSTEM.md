# Mimic design system

This is the method, not a gallery. It exists so the next screen someone adds
looks like it belongs, without anyone having to guess.

Everything here is enforced by tokens in
[`src/Mimic.UI/src/styles/main.css`](../../src/Mimic.UI/src/styles/main.css).
If you find yourself writing a raw colour or a magic pixel value, that is the
signal you have left the system.

---

## The three rules

Every decision below follows from these. If a new situation is not covered,
answer it with these rather than inventing a new pattern.

### 1. Monospace carries the interface

Anything that *is* data is set in JetBrains Mono: headings, labels, tab names,
navigation, counts, paths, status codes, durations, sizes, variable names.

Inter is used for prose only — descriptions, hints, empty-state explanations,
error messages.

**Why.** A tool whose entire subject is HTTP should look like it. Monospace
also aligns columns of numbers and paths for free, which matters in a list of
fifty mocks. The split is the single strongest reason the UI reads as
deliberate rather than generated.

### 2. Colour means something, or it is not there

The interface chrome is neutral. Colour appears in exactly three places:

| Use | Tokens |
|---|---|
| HTTP method | `--method-get`, `--method-post`, … |
| Pass / fail / warn state | `--chip-ok-*`, `--chip-danger-*`, `--chip-warn-*`, `--chip-info-*` |
| The one accent, on the primary action and the active nav item | `--accent` |

Nothing is tinted for decoration. When something in Mimic is coloured, it is
telling you something. A panel does not get a blue border because blue is
nice.

### 3. State is a tinted chip, not a border

Status reads as a soft filled chip — coloured text on a low-opacity wash of
the same hue, no border. Borders are reserved for *structure*: the edge of a
panel, the line between a header and its content.

**Why.** In a list of forty rows, forty outlined badges create forty competing
rectangles. Fills recede; outlines shout.

---

## Type

| Token | Size | Used for |
|---|---|---|
| `--text-2xs` | 11px | Labels, counters, chips |
| `--text-xs` | 12px | Secondary text, inputs, tabs, nav |
| `--text-sm` | 13px | Body default |
| `--text-base` | 14px | Emphasised body, empty-state titles |
| `--text-lg` | 16px | Panel headings |
| `--text-xl` | 20px | Page titles |
| `--text-2xl` | 26px | Rare — the largest thing on a screen |

Tracking matters and is not optional:

- `--tracking-mono` (`-0.03em`) on **every** monospace run. JetBrains Mono is
  wide by default and looks loose without it.
- `--tracking-tight` (`-0.02em`) on large Inter text.
- `--tracking-label` (`+0.07em`) on uppercase labels, which need opening up.

Weights: 500 for labels and nav, 600 for headings and emphasis, 700 only for
method badges and status codes. Never 800+ — `font-synthesis-weight: none` is
set, so a weight the variable font does not have will simply not render.

---

## Space

A 4px rhythm. Use the tokens; do not write `padding: 7px`.

```
--space-1   4px    icon gaps, hairline offsets
--space-2   8px    inside a control, between an icon and its label
--space-3  12px    control padding, gaps between related controls
--space-4  16px    panel padding, gaps between groups
--space-5  24px    section separation
--space-6  32px    major section separation
--space-8  48px    empty-state padding
--space-10 64px    page-level breathing room
```

**Density guidance.** Lists and tables are the dense part of the app — rows
get `--space-2` / `--space-3`. Everything else should breathe. If a screen
feels cramped, the fix is almost always moving one step up the scale, not
shrinking the type.

---

## Shape

```
--radius-sm    6px   chips, badges, small controls
--radius       8px   buttons, inputs, list rows
--radius-lg   12px   cards, panels
--radius-xl   16px   modals
--radius-pill 999px  scrollbar thumbs
```

Soft, but not playful. Above ~16px a developer tool starts to read as consumer
software; below ~4px it reads as a spreadsheet.

Elevation is deliberately weak — `--shadow-sm` on resting controls,
`--shadow-lg` only on modals. Depth comes from surface tokens
(`--surface` → `--surface-raised` → `--surface-hover`), not from drop shadows.

---

## Colour tokens

Never reference a raw hex value in a component. Always go through the semantic
layer, so all three themes work automatically.

```
--bg               the page
--surface          panels, cards, rows
--surface-raised   things sitting on a panel
--surface-hover    hover state
--surface-active   pressed / selected state
--border           structural lines
--border-strong    emphasised lines, hover borders
--text             primary
--text-muted       secondary
--text-subtle      tertiary, placeholders
--accent           the one saturated colour
--accent-soft      its wash, for active backgrounds
```

### Themes

Three, defined as `[data-theme]` blocks. Paper and Slate are one design at two
brightnesses; Terminal is a separate opinion.

| Theme | `data-theme` | Character |
|---|---|---|
| **Paper** | `light` | Default. Cool greys, blue accent, airy. |
| **Slate** | `dark` | Same design, dark surfaces. |
| **Terminal** | `terminal` | Near-black with a green cast, amber accent, denser controls. |

Adding a fourth means defining every token in the list above. If a token is
missing the component silently falls back to the `:root` value, which will
look wrong — so define the whole set or none of it.

---

## Components

### Buttons

`.btn` is the base. Modifiers: `--primary` (the accent; **one per screen
region**), `--danger`, `--ghost` (toolbars and row actions), `--sm`, `--icon`.

A screen with three primary buttons has no primary button.

### Inputs

`.input`, `.select`, and `.input--mono`. Use `--mono` whenever the content is
data the user will compare or scan: URLs, header names, JSON paths, variable
values. `font-feature-settings: 'calt' 0` is set on it, because ligatures in
an editable field move the caret in ways people find unsettling.

### Icons

`AppIcon`, drawn on a 24px grid at 1.75 stroke. **No emoji, ever** — emoji
render differently per platform, cannot take `currentColor`, and are the
fastest way to make a UI look unconsidered.

Add new glyphs to `components/common/icons.ts`. Keep the stroke weight
consistent or the new icon will sit visually heavier than its neighbours.

### Empty states

Every empty state gets three things: an icon, a title, and a sentence that
explains what would be here and how to make it appear. They carry more of the
product's voice than any other surface — a new user sees them before they see
anything else.

Write the hint as help, not as an apology.

---

## Adding something new

1. **Find the closest existing pattern** and copy its structure. Consistency
   beats local cleverness.
2. **Use tokens only.** No raw colours, no magic pixels.
3. **Decide whether your colour is meaningful.** If it is not signalling a
   method, a state, or the primary action, it should be neutral.
4. **Check all three themes.** The Terminal theme is the one that catches
   hard-coded assumptions.
5. **Check the narrow viewport.** Every view has a breakpoint already; follow
   the pattern in the neighbouring component.
6. **Check focus.** Keyboard users need `:focus-visible` to land somewhere
   obvious. It is styled globally — do not remove the outline.

---

## Do / Don't

| Don't | Do |
|---|---|
| Indigo/violet accent — the generated-UI default | The theme's `--accent`, used sparingly |
| Emoji as icons | `AppIcon` SVGs |
| A border on every element | Surface elevation, borders for structure only |
| Outlined status badges | Tinted borderless chips |
| Raw hex in a component | Semantic tokens |
| Default system font stack | Inter for prose, JetBrains Mono for data |
| A new radius or spacing value | The existing scale |
| Decorative colour | Neutral, unless it means something |
| Three primary buttons on one screen | One clear primary action |

---

## Verifying a change

```bash
cd src/Mimic.UI && yarn typecheck && yarn vite build
```

```bash
cd src/Mimic.UI && yarn test:e2e
```

The end-to-end suite covers the theme cycle, so a token you forget to define
in one theme will show up there rather than in front of a user.
