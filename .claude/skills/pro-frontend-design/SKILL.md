---
name: pro-frontend-design
description: Produce professional, cohesive, high-end front-end interfaces that do not look like generic templates or stock AI output. Use this skill whenever the user asks to build, design, redesign, restyle, polish or improve any front-end interface — a landing page, marketing site, dashboard, admin panel, web app screen, form, pricing page, portfolio, or a single UI component (card, navbar, hero, modal, table, button set) — in HTML/CSS, React, Tailwind or similar, including Arabic / RTL interfaces, and even when the user only says "make it look better", "make it modern", "make it premium", "صمم لي صفحة" or "حسّن الواجهة". If the project already has its own design system or a project-specific UI skill, that system wins; use this skill to fill gaps, not to override it.
---

# Pro Frontend Design

The goal is an interface that feels **designed**: one clear visual idea, a strict token system, careful details. Every decision below exists to stop the drift toward "default Tailwind template with a purple gradient".

Work in this order: **concept → tokens → layout → details → checklist**. Do not start writing markup until steps 1 and 2 are written down (in a short comment block or in your reply).

## 0. Existing projects come first

Before anything else, check whether the project already has a design system: CSS custom properties in `:root`, a Tailwind theme, a component library, or a project-specific UI skill (for example one in `.claude/skills/`). If it has one:

- **Reuse it.** Take colours, fonts, spacing, radii and components from what is already there, even where they differ from the rules below (raw hex values, off-scale spacing, other fonts). Match the neighbouring code.
- **Use this skill only to fill gaps:** a state the project hasn't designed (empty, error, loading), an accessibility fix, or a new component with no existing pattern. Build that from the project's existing values.
- **Don't migrate or restyle existing code** to this skill's tokens, type scale or spacing, and don't write a new design brief for an existing product, unless the user asks for a redesign.
- If the project skill and this one disagree, the project skill wins.

Sections 1–2 (brief and token system) apply in full only to new projects or to explicit redesigns.

---

## 1. Pre-coding conceptualization

Before any code, write a 4–6 line design brief:

1. **Visual direction** — pick exactly one and commit to it:
   - *Luxury / minimal* — lots of air, serif or high-contrast display headings, muted palette, one precious accent.
   - *Editorial* — strong typographic hierarchy, columns, rules/dividers, big numerals, print-magazine feel.
   - *Dark-tech* — near-black surfaces, one electric primary, monospace-flavoured details, grid lines, glow used sparingly.
   - *Soft / organic* — warm off-whites, earthy tones, large radii, gentle shapes, friendly rounded type.
   - *Bold / brutalist* — hard edges, thick borders, oversized type, flat high-contrast colour blocks.
   Mixing directions is the most common cause of a "template" look. If two feel right, choose the one that serves the user better and drop the other.
2. **Who is the user?** (role, context, device, language — Arabic? mixed?)
3. **Intended emotion** — e.g. trust, calm, excitement, exclusivity, competence.
4. **The signature element** — the one thing a visitor remembers: an oversized headline, an unusual grid, a custom illustration style, a striking data visual, a distinctive hover effect. Exactly one; everything else supports it.
5. **Primary action per screen** — what the user must do or see first.

---

## 2. Design system (design tokens) — mandatory

All visual values live in CSS custom properties in `:root`. Components reference **semantic** tokens (`--color-text`, `--color-surface`), which point to **primitive** tokens (`--neutral-900`). Never hard-code a hex value, pixel spacing or shadow inside a component.

### 2.1 Color

- **One strong primary** (brand, primary buttons, key links, focus).
- **One accent** (highlights, badges, the signature element — used sparingly, ≤10% of the surface).
- **Nine neutrals** `--neutral-100` … `--neutral-900` (backgrounds, surfaces, borders, text). Tint them slightly toward the primary or toward warm/cool — pure grey looks cheap.
- **Status colors**: `--color-success`, `--color-warning`, `--color-error` (plus optional `-subtle` background variants).
- **Contrast**: at least WCAG AA — **4.5:1** for body text, **3:1** for large text (≥24px, or ≥18.66px bold) and for UI boundaries/icons/focus rings. Check every text/background pair you actually use, in both light and dark themes. If the brand primary fails as text, add a darker `--color-primary-text` variant rather than using a failing color.

### 2.2 Typography

- **Two typefaces maximum per script**: a characterful display face for headings + a highly readable face for body. A monospace face for code/data is allowed only when the product genuinely shows code or tabular figures.
- Do not default to Inter, Arial or Roboto. Use them only with a stated reason (e.g. the product's existing brand).
- Good Latin pairings: Fraunces + Manrope, Cormorant Garamond + Manrope, Space Grotesk + IBM Plex Sans, Playfair Display + Source Sans 3, DM Serif Display + DM Sans, Syne + Work Sans.
- **Arabic**: IBM Plex Sans Arabic, Tajawal, Cairo, Noto Kufi Arabic, Readex Pro (Noto Naskh Arabic for long-form reading). Increase Arabic `line-height` (≈1.7–1.9 for body) and never apply `letter-spacing` to Arabic text — it breaks letter joining.
- **Modular type scale** with a ratio of **1.25** (Major Third) or **1.333** (Perfect Fourth) from a 16px base:

| Token | 1.25 | 1.333 |
| --- | --- | --- |
| `--text-xs` | 0.8rem | 0.75rem |
| `--text-sm` | 0.875rem* | 0.875rem* |
| `--text-base` | 1rem | 1rem |
| `--text-lg` | 1.25rem | 1.333rem |
| `--text-xl` | 1.563rem | 1.777rem |
| `--text-2xl` | 1.953rem | 2.369rem |
| `--text-3xl` | 2.441rem | 3.157rem |
| `--text-4xl` | 3.052rem | 4.209rem |

\* `--text-sm` is a practical off-scale step for UI labels. Use `clamp()` for display sizes, e.g. `font-size: clamp(var(--text-2xl), 5vw, var(--text-4xl));`. Headings: tight line-height (1.1–1.25), slight negative tracking for Latin display sizes. Body: 1.5–1.7, measure 60–75 characters (`max-width: 65ch`).

### 2.3 Spacing

Strict 4px / 8px grid. Only these values:

```css
--space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px; --space-5: 24px;
--space-6: 32px; --space-7: 48px; --space-8: 64px; --space-9: 96px;
```

Section padding comes from the top of the scale (64–96px desktop, 48–64px mobile); component internals from the bottom (4–24px). Related items sit closer together than unrelated ones.

### 2.4 Radius & elevation

- One radius family, used consistently: e.g. `--radius-sm` (inputs, chips), `--radius-md` (buttons, cards), `--radius-lg` (modals, hero panels), `--radius-full` (pills, avatars). Nested elements use a smaller radius than their parent.
- **Three elevation levels**, each made of 2–3 soft, layered shadows tinted with the darkest neutral (never pure black at high opacity):

```css
--shadow-1: 0 1px 2px rgb(var(--shadow-rgb) / 0.05), 0 1px 3px rgb(var(--shadow-rgb) / 0.07);
--shadow-2: 0 2px 4px rgb(var(--shadow-rgb) / 0.04), 0 6px 16px rgb(var(--shadow-rgb) / 0.08),
            0 12px 32px rgb(var(--shadow-rgb) / 0.05);
--shadow-3: 0 4px 8px rgb(var(--shadow-rgb) / 0.05), 0 16px 32px rgb(var(--shadow-rgb) / 0.10),
            0 32px 64px rgb(var(--shadow-rgb) / 0.10);
```

Level 1: cards at rest. Level 2: hover / dropdowns. Level 3: modals / popovers. In dark mode, rely more on lighter surfaces and a 1px inner highlight (`inset 0 1px 0 rgb(255 255 255 / 0.04)`) than on shadows.

### 2.5 Token template

Start every project from this skeleton and fill in values (see the three ready-made identities at the end):

```css
:root {
  /* primitives */
  --neutral-100: ; --neutral-200: ; --neutral-300: ; --neutral-400: ; --neutral-500: ;
  --neutral-600: ; --neutral-700: ; --neutral-800: ; --neutral-900: ;
  --brand-primary: ; --brand-accent: ;

  /* semantic */
  --color-bg: ;            --color-surface: ;       --color-surface-raised: ;
  --color-text: ;          --color-text-muted: ;    --color-border: ;
  --color-primary: ;       --color-on-primary: ;    --color-primary-hover: ;
  --color-accent: ;        --color-accent-text: ;
  --color-success: ;       --color-warning: ;       --color-error: ;
  --color-focus: var(--color-primary);
  --shadow-rgb: ;

  /* type */
  --font-display: ;  --font-body: ;
  /* --text-*, --space-*, --radius-*, --shadow-* as above */

  /* motion */
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
  --dur-fast: 150ms; --dur-base: 200ms; --dur-slow: 300ms;
}
```

---

## 3. Layout rules

- **Grid**: a 12-column grid on desktop (4 on mobile, 8 on tablet) with consistent gutters from the spacing scale. Use CSS Grid for page structure, Flexbox for components.
- **Container**: `max-width: 1200px` (≈1280px for data-dense dashboards), centred, with `padding-inline: var(--space-4)` on mobile and `var(--space-6)` and up on larger screens.
- **White space is a feature**. When in doubt, add space rather than another divider or box.
- **Hierarchy**: exactly one primary element per screen (hero headline, key metric, main CTA). Secondary content is visibly quieter (size, weight, color), not just "also there".
- **Mobile-first**: write base styles for small screens, then add `min-width` breakpoints:

```css
/* sm 640px · md 768px · lg 1024px · xl 1280px */
@media (min-width: 768px)  { … }
@media (min-width: 1024px) { … }
```

- **RTL-ready by default**:
  - Set `<html lang="ar" dir="rtl">` for Arabic (and `lang`/`dir` on mixed-language blocks).
  - Use logical properties everywhere: `margin-inline-start`, `padding-inline`, `inset-inline-end`, `border-inline-start`, `text-align: start`. Never `left`/`right` for layout.
  - Mirror directional icons (arrows, chevrons, "back") with `[dir="rtl"] .icon-directional { transform: scaleX(-1); }`; do not mirror logos, media controls, checkmarks or numbers.
  - Flexbox and Grid follow `dir` automatically — do not fight them with `row-reverse`.
  - Test with real Arabic copy; it is often longer and taller than English.

---

## 4. Touches of luxury

- **Motion**: 150–300ms, `ease-out` (or the `--ease-out` curve). Animate `transform` and `opacity` only. Typical patterns: button hover lift of 1–2px + shadow level up; card hover; staggered fade-up on scroll using `IntersectionObserver` (offset 8–16px, 40–80ms stagger). Always:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}
```

- **Backgrounds with depth** (pick one or two, consistent with the direction):
  - Soft radial gradients from the brand palette at low opacity (`radial-gradient(60% 50% at 80% 0%, color-mix(in oklch, var(--brand-primary) 18%, transparent), transparent)`).
  - Subtle grain: an inline SVG `feTurbulence` noise at 3–6% opacity over the background.
  - Geometric shapes or grid/dot patterns drawn with CSS or inline SVG, low contrast.
  - Glassmorphism only where content sits over something rich (a sticky header over a hero image): `backdrop-filter: blur(12px) saturate(140%)`, a translucent surface and a 1px light border. Never as the default card style, and never at the cost of text contrast.
- **Icons**: one library only — Lucide or Phosphor (one weight/style). Size icons on the scale (16/20/24px), align them optically with text, give decorative icons `aria-hidden="true"` and icon-only buttons an `aria-label`.
- **Craft details**:
  - Loading: skeletons that match the final layout (with a gentle shimmer that respects reduced motion), not a lone spinner on an empty page.
  - Empty states: an icon or small illustration, one sentence explaining why it is empty, and the action that fills it.
  - Error states: say what happened and how to fix it, in plain language, next to the thing that failed; inline field errors linked with `aria-describedby`.
  - Focus: a visible ring on every interactive element — `outline: 2px solid var(--color-focus); outline-offset: 2px;` via `:focus-visible`. Never `outline: none` without a replacement.
  - Micro-interactions: pressed state (`scale(0.98)`), success confirmation on submit, toggles that animate, copy-to-clipboard feedback.
  - Real-looking content: realistic names, numbers, dates and copy that fits the product.

---

## 5. Anti-patterns — never ship these

- Generic purple-to-blue gradients on a white background (or any "AI startup" gradient blob hero).
- Harsh shadows (`0 0 10px rgba(0,0,0,.5)`), or shadows on everything.
- More than two typefaces (per script).
- Arbitrary colors outside the token system; one-off hex values in components.
- Inconsistent spacing (13px here, 22px there) — only the scale.
- "Lorem ipsum" or obvious placeholder copy ("Feature 1", "John Doe", "Your text here").
- Emojis used as icons.
- Also avoid: centring every block of text, three identical feature cards as the only idea on the page, low-contrast grey-on-grey text, borders *and* shadows *and* backgrounds on the same card, and full-width text lines over 80 characters.

---

## 6. Technical implementation

- **Default stack**: modern semantic HTML + CSS with tokens in `:root`. Use **React + Tailwind** only when requested or when the project already uses it — then map the tokens into the Tailwind theme (Tailwind v4: `@theme { --color-primary: …; }`; v3: `theme.extend` pointing at `var(--…)`), and still never use arbitrary values like `p-[13px]`.
- **Component-based**: small, reusable pieces (button, card, field, nav, section) with variants driven by tokens, not copy-pasted styles. One CSS class naming approach, applied consistently.
- **Semantic HTML**: `header`, `nav`, `main`, `section` (with a heading), `article`, `footer`, `button` for actions, `a` for navigation, real `label`s for inputs, one `h1` per page and no skipped heading levels.
- **Accessibility**: meaningful `alt` text (empty `alt=""` for decorative images), ARIA only where native semantics are not enough (`aria-expanded`, `aria-controls`, `aria-current`, `aria-live` for async messages), full keyboard navigation (logical tab order, Escape closes overlays, focus trapped inside modals and returned afterwards), touch targets of at least 24×24px (the WCAG 2.2 AA minimum, 2.5.8) and preferably 44×44px (WCAG AAA 2.5.5 and platform guidance) for primary actions and mobile, a skip link.
- **Dark mode via CSS variables**: only the semantic tokens change; components never know which theme is active.

```css
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* dark semantic tokens */ }
}
:root[data-theme="dark"] { /* same dark semantic tokens */ }
```

  Also set `color-scheme: light dark;` so native controls and scrollbars follow. Re-check contrast for the dark theme; lighten the primary for dark backgrounds instead of reusing the light-theme value.
- **Performance**: `font-display: swap`, preconnect to font hosts, at most 2 font families × 2–3 weights, images with `width`/`height` and `loading="lazy"` below the fold.

---

## 7. Pre-delivery checklist

Go through this before handing anything over, and fix what fails:

- [ ] All colors and spacing come from the token system — no stray hex or px values
- [ ] Contrast meets WCAG AA (4.5:1 text, 3:1 large text / UI) in light **and** dark
- [ ] Works on mobile (≈375px) and desktop (≈1440px), no horizontal scroll
- [ ] Layout uses logical properties; if the UI has Arabic or other RTL text, RTL is correct — mirrored directional icons, real Arabic copy checked
- [ ] Hover, focus-visible, active, disabled, loading, empty and error states are included
- [ ] Reduced motion is respected; animations are 150–300ms ease-out
- [ ] Keyboard-only navigation works end to end; images have alt text
- [ ] Two typefaces maximum; one icon library; no emojis as icons; no lorem ipsum
- [ ] One clear primary element per screen and one signature element on the page
- [ ] It does **not** look like a generic template — if it could be any product's page, push the concept further

---

## Example identities (ready-to-use tokens)

All text/background pairs below were checked: body text, muted text, primary/accent text, status colors and text-on-primary all meet ≥ 4.5:1 on both background and surface, in both themes. `--color-accent` reaches ≥ 3:1 (icons, borders, large text); use `--color-accent-text` for small text. Add the shared `--text-*`, `--space-*`, `--shadow-*` and motion tokens from section 2. To make the alternate theme follow the OS setting, copy its block into a media query for **that** theme:

- Light-default identities (A, C): the alternate is dark, so use the section 6 query, `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { … } }`.
- Dark-default identity (B): the alternate is light, so use `@media (prefers-color-scheme: light) { :root:not([data-theme="dark"]) { … } }`.

Each identity sets `color-scheme` on `:root` (its default) and in its alternate block, so native controls and scrollbars match the active theme.

### A. "Atelier" — luxury / minimal

Warm ivory, deep emerald, brass accent. Serif display headings, generous air, hairline borders. Signature: an oversized serif headline with a thin brass rule.

```css
/* Fonts: Cormorant Garamond (600) + Manrope (400/500/600) · Arabic: Noto Kufi Arabic + IBM Plex Sans Arabic */
:root {
  --neutral-100: #F7F4EE; --neutral-200: #EDE8DF; --neutral-300: #DDD6CA;
  --neutral-400: #BFB6A7; --neutral-500: #9A9081; --neutral-600: #6F665A;
  --neutral-700: #4F483F; --neutral-800: #2F2A25; --neutral-900: #1A1714;
  --brand-primary: #1F4D3F; --brand-accent: #A88238;

  --color-bg: var(--neutral-100);  --color-surface: #FFFDF9;  --color-surface-raised: #FFFFFF;
  --color-text: var(--neutral-900); --color-text-muted: var(--neutral-600); --color-border: var(--neutral-300);
  --color-primary: #1F4D3F; --color-primary-hover: #173B30; --color-on-primary: #F7F4EE;
  --color-accent: #A88238;  --color-accent-text: #7A5A1C;
  --color-success: #2F6B3F; --color-warning: #8A5A00; --color-error: #A3312A;
  --color-focus: #1F4D3F;   --shadow-rgb: 26 23 20;
  color-scheme: light;

  --font-display: "Cormorant Garamond", "Noto Kufi Arabic", Georgia, serif;
  --font-body: "Manrope", "IBM Plex Sans Arabic", system-ui, sans-serif;
  --radius-sm: 2px; --radius-md: 4px; --radius-lg: 8px; --radius-full: 999px;
}
:root[data-theme="dark"] {
  --color-bg: #1A1714; --color-surface: #24201C; --color-surface-raised: #2F2A25;
  --color-text: #F2EDE4; --color-text-muted: #BFB6A7; --color-border: #3A342D;
  --color-primary: #7FBFA6; --color-primary-hover: #95CDB7; --color-on-primary: #10261F;
  --color-accent: #D4AE5E; --color-accent-text: #D4AE5E;
  --color-success: #7CC48D; --color-warning: #E3B04B; --color-error: #F08A80;
  --color-focus: #7FBFA6;  --shadow-rgb: 0 0 0;
  color-scheme: dark;
}
```

### B. "Signal" — dark-tech

Near-black blue-grey, acid-lime primary, cyan accent. Grotesk headings, fine grid lines, restrained glow on the primary CTA only. Signature: a live-looking data panel with a 1px grid background.

```css
/* Fonts: Space Grotesk (500/700) + IBM Plex Sans (400/500) · Arabic: Readex Pro + IBM Plex Sans Arabic */
:root {
  --neutral-100: #E8ECF2; --neutral-200: #C9D1DC; --neutral-300: #A3AEBE;
  --neutral-400: #7C889B; --neutral-500: #5A6578; --neutral-600: #3D4656;
  --neutral-700: #272E3A; --neutral-800: #171C25; --neutral-900: #0C0F14;
  --brand-primary: #C8F04A; --brand-accent: #5CD3F2;

  /* dark is the default theme for this identity */
  --color-bg: var(--neutral-900);   --color-surface: var(--neutral-800); --color-surface-raised: var(--neutral-700);
  --color-text: var(--neutral-100); --color-text-muted: var(--neutral-300); --color-border: var(--neutral-700);
  --color-primary: #C8F04A; --color-primary-hover: #D6F570; --color-on-primary: #0C0F14;
  --color-accent: #5CD3F2;  --color-accent-text: #5CD3F2;
  --color-success: #5EE69A; --color-warning: #F5B841; --color-error: #FF6B6B;
  --color-focus: #C8F04A;   --shadow-rgb: 0 0 0;
  color-scheme: dark;
  --glow-primary: 0 0 0 1px rgb(200 240 74 / 0.35), 0 8px 32px rgb(200 240 74 / 0.18);

  --font-display: "Space Grotesk", "Readex Pro", system-ui, sans-serif;
  --font-body: "IBM Plex Sans", "IBM Plex Sans Arabic", system-ui, sans-serif;
  --radius-sm: 4px; --radius-md: 6px; --radius-lg: 12px; --radius-full: 999px;
}
:root[data-theme="light"] {
  --color-bg: #F5F7FA; --color-surface: #FFFFFF; --color-surface-raised: #FFFFFF;
  --color-text: #0C0F14; --color-text-muted: #3D4656; --color-border: #C9D1DC;
  --color-primary: #4D6B00; --color-primary-hover: #3E5700; --color-on-primary: #FFFFFF;
  --color-accent: #0A6E8A; --color-accent-text: #0A6E8A;
  --color-success: #17713F; --color-warning: #8A5B00; --color-error: #C0262D;
  --color-focus: #4D6B00;  --shadow-rgb: 12 15 20;
  color-scheme: light;
}
```

### C. "Grove" — soft / organic

Warm stone neutrals, terracotta primary, sage accent. Rounded serif headings, large radii, soft blobs and grain in the background. Signature: organic SVG shapes framing a photo with a gentle parallax.

```css
/* Fonts: Fraunces (500/600, soft optical size) + Nunito Sans (400/600) · Arabic: Tajawal (headings) + Cairo (body) */
:root {
  --neutral-100: #F6F5F0; --neutral-200: #ECEAE2; --neutral-300: #DAD7CB;
  --neutral-400: #B8B4A5; --neutral-500: #8F8B7D; --neutral-600: #67645A;
  --neutral-700: #48463F; --neutral-800: #2E2D28; --neutral-900: #1C1B18;
  --brand-primary: #A4471F; --brand-accent: #6E8B6B;

  --color-bg: var(--neutral-100);  --color-surface: #FFFFFF;  --color-surface-raised: #FFFFFF;
  --color-text: var(--neutral-900); --color-text-muted: var(--neutral-600); --color-border: var(--neutral-300);
  --color-primary: #A4471F; --color-primary-hover: #8C3C1A; --color-on-primary: #FFFFFF;
  --color-accent: #6E8B6B;  --color-accent-text: #4E6A4B;
  --color-success: #3C7A4A; --color-warning: #8C5D00; --color-error: #B3261E;
  --color-focus: #A4471F;   --shadow-rgb: 46 45 40;
  color-scheme: light;

  --font-display: "Fraunces", "Tajawal", Georgia, serif;
  --font-body: "Nunito Sans", "Cairo", system-ui, sans-serif;
  --radius-sm: 8px; --radius-md: 14px; --radius-lg: 28px; --radius-full: 999px;
}
:root[data-theme="dark"] {
  --color-bg: #1C1B18; --color-surface: #262521; --color-surface-raised: #2E2D28;
  --color-text: #F1EFE8; --color-text-muted: #B8B4A5; --color-border: #3A3833;
  --color-primary: #E8956C; --color-primary-hover: #EEAA88; --color-on-primary: #2A140A;
  --color-accent: #A9C3A5; --color-accent-text: #A9C3A5;
  --color-success: #86C795; --color-warning: #E2B45A; --color-error: #F28B82;
  --color-focus: #E8956C;  --shadow-rgb: 0 0 0;
  color-scheme: dark;
}
```
