# Design System Specification: High-End Editorial

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Digital Archivist."** 

We are moving away from the "disposable" feel of modern SaaS and toward the permanence of a high-end print publication like *Monocle* or *The Gentlewoman*. This system rejects the generic "tech" aesthetic (neon, heavy rounding, floating blobs) in favor of **Organic Authority**. 

To break the "template" look, we utilize **Intentional Asymmetry**. Key layouts should avoid perfect centering; instead, use the wide margins of our spacing scale to push content into "editorial columns." Overlap serif typography across background shifts to create a sense of physical layering, treating the browser more like a curated page and less like a software dashboard.

---

## 2. Colors & Surface Philosophy
The palette is rooted in warmth and tactile credibility, avoiding the sterile "blue-white" of standard tech platforms.

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders to define sections. Layout boundaries must be established through color blocking. Use a transition from `surface` to `surface-container-low` to signify a new content block. If a visual break is needed, use a wide gap (e.g., `spacing-12`) rather than a stroke.

### Surface Hierarchy & Nesting
Treat the UI as a series of stacked, fine-paper sheets. 
- **Base Layer:** `surface` (#fbf9f4)
- **Secondary Sectioning:** `surface-container-low` (#f5f3ee)
- **Interactive Containers (Cards):** `surface-container-lowest` (#ffffff) to provide a subtle "pop" against the warm background.

### The Glass & Gradient Rule
For primary CTAs and hero highlights, move beyond flat fills. Use a **Signature Gradient** transitioning from `primary` (#823b18) to `primary-container` (#a0522d) at a 135-degree angle. For floating navigation or context menus, apply `surface_low` with a 12px `backdrop-blur` and 85% opacity to create a "frosted glass" effect that feels integrated into the environment.

---

## 3. Typography
The system relies on the tension between a high-character serif and a technical, modern sans-serif.

| Level | Token | Font Family | Size | Intent |
| :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | Newsreader | 3.5rem | High-impact editorial moments; use with tight letter-spacing. |
| **Headline** | `headline-md`| Newsreader | 1.75rem | Section titles that require an authoritative, "journalistic" tone. |
| **Title** | `title-lg` | Plus Jakarta Sans | 1.375rem | Functional headers; provides a modern, "Stripe-like" clarity. |
| **Body** | `body-md` | Plus Jakarta Sans | 0.875rem | Primary reading; generous line height (1.6) for readability. |
| **Label** | `label-md` | Plus Jakarta Sans | 0.75rem | All-caps, tracked out (+5%) for metadata and small tags. |

---

## 4. Elevation & Depth
Depth is achieved through **Tonal Layering** rather than structural lines.

- **The Layering Principle:** To create hierarchy, place a `surface-container-highest` element on top of a `surface` background. The contrast in warmth provides enough "lift" without visual noise.
- **Ambient Shadows:** When a shadow is necessary for floating elements (e.g., a transcription popover), use an extra-diffused shadow: `box-shadow: 0 20px 40px rgba(27, 28, 25, 0.05)`. The color must be a tint of `on-surface`, never pure black.
- **The "Ghost Border" Fallback:** If a container requires a boundary (e.g., an input field), use the `outline-variant` token at **20% opacity**. This creates a suggestion of a border that disappears into the background, maintaining the "Monocle" minimalist aesthetic.

---

## 5. Components

### Buttons
- **Primary:** Gradient fill (`primary` to `primary-container`), white text (`on-primary`), `0.375rem` (md) radius.
- **Secondary:** `surface-container-high` background with `on-surface` text. No border.
- **Tertiary/Ghost:** `on-surface` text with no background. On hover, apply a `surface-variant` subtle fill.

### Input Fields
- **Styling:** Use a `surface-container-lowest` background with a "Ghost Border" (20% `outline-variant`). 
- **Focus State:** Shift the border to 100% `primary` (#823b18) but keep the stroke weight at 1px. Refined, not loud.

### Cards & Lists
- **Rule:** Forbid the use of divider lines. 
- **Implementation:** Separate list items using `spacing-4` vertical gaps. If content is dense, use alternating background tints (e.g., `surface` vs `surface-container-low`) instead of lines.

### Progress & Transcription States (App Specific)
- **Timeline:** Use a thick `3.5rem` (10) spacing for the left margin where "Time" labels reside in `label-sm`, creating a vertical gutter typical of manuscript editing software.
- **Active Transcription:** Highlight text using a subtle `primary-fixed` (#ffdbcd) background—a soft terracotta highlight that looks like a literal highlighter pen on paper.

---

## 6. Do’s and Don’ts

### Do:
- **Use "White Space as a Border":** Use `spacing-16` or `spacing-20` to separate high-level concepts.
- **Embrace Asymmetry:** Align descriptions to the right while headlines stay left to create "visual zig-zag."
- **Nesting Surfaces:** Place `surface-container-lowest` cards on `surface-container-low` sections for a premium, layered feel.

### Don't:
- **Don't use 100% black:** Always use `on-surface` (#1b1c19) for text to maintain the "ink on paper" warmth.
- **Don't use large corner radii:** Stay within `sm` (0.125rem) to `md` (0.375rem). Rounded "pill" buttons should be reserved only for tags/chips, never primary actions.
- **Don't use dividers:** If you feel the urge to draw a line, increase the spacing by `spacing-4` instead.