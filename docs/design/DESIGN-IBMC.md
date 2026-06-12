# Design System Inspired by IBM

## 1. Visual Theme & Atmosphere

IBM's design system embodies enterprise sophistication with a forward-thinking, technology-driven aesthetic. The visual language balances precision and clarity with accessible, human-centered design. Deep navy and pure whites create professional contrast, while the signature IBM Blue (`#0F62FE`) serves as the beacon for primary interactions and forward momentum. The system favors clean lines, generous whitespace, and a minimalist approach that prioritizes content hierarchy and user confidence. This is a design philosophy built for global audiences, complex systems, and mission-critical applications—where clarity and trustworthiness are paramount.

**Key Characteristics**
- Enterprise-grade professionalism with approachable accessibility
- Bold primary blue as the primary call-to-action driver
- Neutral, high-contrast foundation enabling clear content hierarchy
- Minimal ornamentation; form follows function
- Global-ready typography and inclusive color semantics
- Emphasis on white space and structured breathing room
- Clear distinction between interactive and static elements
- Semantic color coding for system feedback and status

## 2. Color Palette & Roles

### Primary
- **IBM Blue** (`#0F62FE`): Primary brand color; primary CTAs, links, active states, and key interactive elements. Highest usage across the system.
- **Bright Blue** (`#4589FF`): Secondary interactive blue for hover states, lighter emphasis, and secondary actions.
- **Deep Navy** (`#0043CE`): Darkened primary for high-contrast text on light backgrounds and deep interactive states.

### Accent Colors
- **Light Blue** (`#78A9FF`): Tertiary accent; subtle highlights, disabled states, and lighter interactive surfaces.
- **Pale Blue** (`#A6C8FF`): Lightest accent blue for backgrounds, low-emphasis overlays, and decorative elements.
- **Very Pale Blue** (`#D0E2FF`): Minimal accent for very light backgrounds and subtle section dividers.
- **Critical Red** (`#FA4D56`): Alert and destructive action emphasis; secondary error indicator.

### Interactive
- **Error Red** (`#DA1E28`): Primary error states, validation failures, and critical warnings; dark variant for high contrast.
- **Warning Yellow** (`#F1C21B`): Warning states, caution indicators, and attention-requiring notifications.
- **Success Green** (`#24A148`): Success confirmations, positive state indicators, and completed actions.

### Neutral Scale
- **Off-Black** (`#161616`): Primary text color; dominant for headings, body copy, and UI text requiring high contrast.
- **Dark Gray** (`#393939`): Secondary text; supporting information and secondary UI labels.
- **Medium Gray** (`#525252`): Tertiary text; muted labels, metadata, and low-emphasis copy.
- **Light Medium Gray** (`#8D8D8D`): Disabled text, placeholder text, and very low-emphasis content.
- **Light Gray** (`#C6C6C6`): Subtle borders, light dividers, and minimal decorative strokes.

### Surface & Borders
- **Pure White** (`#FFFFFF`): Primary surface color; card backgrounds, modals, and main content areas.
- **Off-White** (`#F4F4F4`): Secondary surface; subtle background sections and contained component backgrounds.
- **Light Border Gray** (`#E0E0E0`): Border color for cards, inputs, and container edges; primary divider.
- **Very Light Gray** (`#C6C6C6`): Secondary border; softer dividers and inactive field borders.

## 3. Typography Rules

### Font Family
**Primary Font:** IBM Plex Sans, sans-serif  
**Fallback Stack:** -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif

Secondary or code applications default to IBM Plex Sans Mono if available, otherwise monospace.

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|-----------------|-------|
| Display / H1 | IBM Plex Sans | 53px | 300 | 63px | `0em` | Hero headlines; maximum visual impact |
| Heading 2 / H2 | IBM Plex Sans | 42px | 400 | 52px | `0em` | Major section heads; inferred |
| Heading 3 / H3 | IBM Plex Sans | 28px | 400 | 36px | `0em` | Section subheadings and card titles |
| Heading 4 / H4 | IBM Plex Sans | 20px | 400 | 28px | `0em` | Subsection headers and component titles |
| Heading 5 / H5 | IBM Plex Sans | 16px | 600 | 24px | `0em` | Bold labels and emphasis headings |
| Body / Paragraph | IBM Plex Sans | 16px | 400 | 24px | `0em` | Primary body text; default paragraph copy |
| Large Display | IBM Plex Sans | 32px | 400 | 40px | `0em` | Large feature text and prominent callouts |
| Link / Interaction | IBM Plex Sans | 14px | 400 | 18px | `0em` | Inline links and clickable text |
| Button | IBM Plex Sans | 14px | 600 | 18px | `0em` | CTA and button text |
| Label / Caption | IBM Plex Sans | 12px | 400 | 16px | `0em` | Form labels, captions, and metadata |
| List Item | IBM Plex Sans | 16px | 400 | 16px | `0em` | Bulleted and numbered list content |

### Principles
- **Weight as hierarchy:** Use weight (300, 400, 600) to establish visual priority; avoid extremes beyond this range.
- **Line height for breathing:** Generous line-height (1.5–1.75x font size) ensures readability at all scales.
- **Semantic sizing:** Size jumps follow a logical progression; avoid arbitrary increments.
- **Accessibility-first:** Minimum `12px` for all user-facing text; `14px` for interactive elements.
- **Global readiness:** IBM Plex Sans supports Latin, Cyrillic, Arabic, and Asian languages for international deployment.

## 4. Component Stylings

### Buttons

**Primary Button**
- **Background:** `#0F62FE`
- **Text Color:** `#FFFFFF`
- **Font Size:** `14px`
- **Font Weight:** `600`
- **Padding:** `16px 24px`
- **Border Radius:** `0px`
- **Border:** `1px solid #0F62FE`
- **Min Height:** `48px`
- **Hover State:** Background `#4589FF`, Text `#FFFFFF`
- **Active State:** Background `#0043CE`, Text `#FFFFFF`
- **Disabled State:** Background `#E0E0E0`, Text `#8D8D8D`

**Secondary Button**
- **Background:** `#FFFFFF`
- **Text Color:** `#0F62FE`
- **Font Size:** `14px`
- **Font Weight:** `600`
- **Padding:** `16px 24px`
- **Border Radius:** `0px`
- **Border:** `1px solid #0F62FE`
- **Min Height:** `48px`
- **Hover State:** Background `#F4F4F4`, Text `#0043CE`, Border `#0043CE`
- **Active State:** Background `#E0E0E0`, Text `#0043CE`, Border `#0043CE`
- **Disabled State:** Background `#F4F4F4`, Text `#8D8D8D`, Border `#C6C6C6`

**Ghost Button (Tertiary)**
- **Background:** `transparent`
- **Text Color:** `#0F62FE`
- **Font Size:** `14px`
- **Font Weight:** `600`
- **Padding:** `16px 24px`
- **Border Radius:** `0px`
- **Border:** `1px solid transparent`
- **Min Height:** `48px`
- **Hover State:** Background `transparent`, Text `#4589FF`, Border `1px solid #78A9FF`
- **Active State:** Background `transparent`, Text `#0043CE`, Border `1px solid #0043CE`
- **Disabled State:** Background `transparent`, Text `#8D8D8D`, Border `1px solid transparent`

**Danger Button**
- **Background:** `#DA1E28`
- **Text Color:** `#FFFFFF`
- **Font Size:** `14px`
- **Font Weight:** `600`
- **Padding:** `16px 24px`
- **Border Radius:** `0px`
- **Border:** `1px solid #DA1E28`
- **Min Height:** `48px`
- **Hover State:** Background `#FA4D56`, Text `#FFFFFF`
- **Active State:** Background `#BA1B23`, Text `#FFFFFF`
- **Disabled State:** Background `#E0E0E0`, Text `#8D8D8D`

### Cards & Containers

**Card (Default)**
- **Background:** `#FFFFFF`
- **Text Color:** `#161616`
- **Padding:** `24px`
- **Border Radius:** `0px`
- **Border:** `1px solid #E0E0E0`
- **Box Shadow:** `none`
- **Font Size:** `16px`
- **Font Weight:** `400`
- **Line Height:** `24px`

**Card (Elevated/Feature)**
- **Background:** `#FFFFFF`
- **Text Color:** `#161616`
- **Padding:** `32px`
- **Border Radius:** `0px`
- **Border:** `1px solid #E0E0E0`
- **Box Shadow:** `0px 8px 16px rgba(0, 0, 0, 0.08)`
- **Font Size:** `16px`
- **Font Weight:** `400`
- **Line Height:** `24px`
- **Hover State:** Box Shadow `0px 12px 24px rgba(0, 0, 0, 0.12)`

**Card (Subtle Background)**
- **Background:** `#F4F4F4`
- **Text Color:** `#161616`
- **Padding:** `24px`
- **Border Radius:** `0px`
- **Border:** `none`
- **Box Shadow:** `none`
- **Font Size:** `16px`
- **Font Weight:** `400`
- **Line Height:** `24px`

### Inputs & Forms

**Text Input (Default)**
- **Background:** `#F4F4F4`
- **Text Color:** `#161616`
- **Placeholder Color:** `#8D8D8D`
- **Font Size:** `14px`
- **Font Weight:** `400`
- **Padding:** `12px 16px`
- **Border Radius:** `0px`
- **Border:** `1px solid #E0E0E0`
- **Min Height:** `48px`
- **Focus State:** Border `2px solid #0F62FE`, Background `#FFFFFF`, Outline `none`
- **Error State:** Border `2px solid #DA1E28`, Background `#FFFFFF`
- **Disabled State:** Background `#E0E0E0`, Text Color `#8D8D8D`, Border `1px solid #C6C6C6`

**Label**
- **Font Size:** `12px`
- **Font Weight:** `400`
- **Color:** `#161616`
- **Line Height:** `16px`
- **Margin Bottom:** `8px`
- **Display:** `block`

**Helper Text**
- **Font Size:** `12px`
- **Font Weight:** `400`
- **Color:** `#525252`
- **Line Height:** `16px`
- **Margin Top:** `4px`

**Error Message**
- **Font Size:** `12px`
- **Font Weight:** `400`
- **Color:** `#DA1E28`
- **Line Height:** `16px`
- **Margin Top:** `4px`

### Navigation

**Header Navigation Item**
- **Font Size:** `14px`
- **Font Weight:** `400`
- **Color:** `#161616`
- **Padding:** `12px 16px`
- **Border Radius:** `0px`
- **Border Bottom:** `3px solid transparent`
- **Hover State:** Color `#0F62FE`, Border Bottom `3px solid #0F62FE`
- **Active State:** Color `#0F62FE`, Border Bottom `3px solid #0F62FE`, Font Weight `600`

**Dropdown Menu Item**
- **Font Size:** `14px`
- **Font Weight:** `400`
- **Color:** `#161616`
- **Padding:** `12px 16px`
- **Background:** `#FFFFFF`
- **Hover State:** Background `#F4F4F4`, Color `#0F62FE`
- **Active State:** Background `#F4F4F4`, Color `#0F62FE`, Font Weight `600`

### Links

**Inline Link**
- **Font Size:** `14px`
- **Font Weight:** `400`
- **Color:** `#0F62FE`
- **Text Decoration:** `none`
- **Border Bottom:** `1px solid transparent`
- **Hover State:** Text Decoration `underline`, Color `#4589FF`
- **Visited State:** Color `#002D9C`
- **Focus State:** Outline `2px solid #0F62FE`, Outline Offset `2px`

**Secondary Link**
- **Font Size:** `14px`
- **Font Weight:** `600`
- **Color:** `#525252`
- **Text Decoration:** `none`
- **Border Bottom:** `1px solid transparent`
- **Hover State:** Color `#0F62FE`, Border Bottom `1px solid #0F62FE`

### Badges

**Badge (Information)**
- **Background:** `#D0E2FF`
- **Text Color:** `#0043CE`
- **Font Size:** `12px`
- **Font Weight:** `600`
- **Padding:** `4px 12px`
- **Border Radius:** `12px`
- **Border:** `none`

**Badge (Success)**
- **Background:** `#D3F6D3`
- **Text Color:** `#24A148`
- **Font Size:** `12px`
- **Font Weight:** `600`
- **Padding:** `4px 12px`
- **Border Radius:** `12px`
- **Border:** `none`

**Badge (Warning)**
- **Background:** `#F9E3BA`
- **Text Color:** `#B8860B`
- **Font Size:** `12px`
- **Font Weight:** `600`
- **Padding:** `4px 12px`
- **Border Radius:** `12px`
- **Border:** `none`

**Badge (Error)**
- **Background:** `#FFDBDB`
- **Text Color:** `#DA1E28`
- **Font Size:** `12px`
- **Font Weight:** `600`
- **Padding:** `4px 12px`
- **Border Radius:** `12px`
- **Border:** `none`

### Modals & Dialogs

**Modal Container**
- **Background:** `#FFFFFF`
- **Border Radius:** `0px`
- **Border:** `1px solid #E0E0E0`
- **Box Shadow:** `0px 20px 48px rgba(0, 0, 0, 0.16)`
- **Max Width:** `512px` (typical); responsive to viewport
- **Padding:** `32px`

**Modal Header**
- **Font Size:** `28px`
- **Font Weight:** `400`
- **Color:** `#161616`
- **Line Height:** `36px`
- **Margin Bottom:** `24px`

**Modal Body**
- **Font Size:** `14px`
- **Font Weight:** `400`
- **Color:** `#525252`
- **Line Height:** `18px`
- **Margin Bottom:** `24px`

**Modal Footer (Button Group)**
- **Padding Top:** `24px`
- **Border Top:** `1px solid #E0E0E0`
- **Display:** `flex`
- **Gap:** `12px`
- **Justify Content:** `flex-end`

### Tabs

**Tab (Inactive)**
- **Font Size:** `14px`
- **Font Weight:** `400`
- **Color:** `#525252`
- **Padding:** `12px 16px`
- **Border Bottom:** `2px solid transparent`
- **Background:** `transparent`

**Tab (Active)**
- **Font Size:** `14px`
- **Font Weight:** `600`
- **Color:** `#0F62FE`
- **Padding:** `12px 16px`
- **Border Bottom:** `2px solid #0F62FE`
- **Background:** `transparent`

**Tab (Hover)**
- **Color:** `#0F62FE`
- **Border Bottom:** `2px solid #78A9FF`

## 5. Layout Principles

### Spacing System

IBM's spacing system uses `8px` as the fundamental unit, with a modular scale for predictable, consistent gaps:

- **Micro spacing:** `4px`, `8px` — tight grouping of related elements (button icon-to-text, nested form controls)
- **Small spacing:** `12px`, `16px` — padding within components, margins between closely related items
- **Base spacing:** `24px`, `32px` — padding for cards, gaps between sections, standard container padding
- **Large spacing:** `40px`, `48px` — vertical separation between major content blocks
- **Extra large spacing:** `64px`, `72px` — hero spacing, full-width section gaps

**Usage Context:**
- Component padding: `16px`, `24px`
- Card/container padding: `24px`, `32px`
- Section margins: `48px`, `64px`
- Stack gaps: `12px` (tight), `16px` (default), `24px` (loose)
- Grid gutters: `24px`, `32px`

### Grid & Container

- **Max Container Width:** `1440px` (desktop optimal reading width)
- **Typical Content Max:** `1200px` (narrower for text-heavy pages)
- **Column Structure:** 12-column grid system; flexible and responsive
- **Gutter Width:** `24px` between columns on desktop; `16px` on tablet; `12px` on mobile
- **Section Patterns:** Full-bleed hero (no max width constraint); contained sections (max-width with horizontal padding)
- **Padding:** `32px–64px` horizontal on large screens; `24px` on medium; `16px` on small

### Whitespace Philosophy

IBM's design prioritizes breathing room and cognitive clarity. Whitespace is not emptiness—it is an active design element that guides the eye, separates concerns, and reduces cognitive load. Generous margins between sections prevent visual fatigue. Nested components maintain consistent internal spacing. Whitespace increases with screen size; mobile layouts use tighter but still deliberate spacing. This approach reflects IBM's enterprise heritage: precision, trust, and clarity above visual density.

### Border Radius Scale

- **None (sharp corners):** `0px` — default for all components; aligns with IBM's structured, minimalist aesthetic
- **Subtle:** `2px` — very minor rounding for images or decorative elements only
- **Mild:** `4px` — inferred for lightweight UI refinement where needed (infrequent)
- **Medium:** `8px` — used for isolated decorative elements or special containers
- **Full (pill):** `24px–48px` — badges, pills, and fully rounded elements (e.g., `border-radius: 50%` for circular avatars)

**Default:** All interactive and static components use `0px` (sharp corners) unless explicitly styled otherwise.

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| **Base (0)** | `box-shadow: none` | Flat surfaces: text, inputs on off-white backgrounds, default cards |
| **Level 1** | `box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.06)` | Subtle lift for contained components, popovers, tooltips |
| **Level 2** | `box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.08)` | Elevated cards, feature sections, callouts |
| **Level 3** | `box-shadow: 0px 12px 24px rgba(0, 0, 0, 0.12)` | Modals, overlays, significant elevation |
| **Level 4** | `box-shadow: 0px 20px 48px rgba(0, 0, 0, 0.16)` | Full-screen modals, critical overlays, highest prominence |

**Depth Philosophy:** IBM uses subtle shadow hierarchy to communicate layering without visual noise. Shadows are soft, using low-opacity black, allowing backgrounds to remain visible. Elevation typically increases on hover (e.g., cards rising from Level 2 to Level 3). Shadow treatment is muted compared to other design systems, aligning with the professional, understated aesthetic.

## 7. Do's and Don'ts

### Do
- **Use the primary IBM Blue (`#0F62FE`) for all primary CTAs.** It is the visual anchor and instantly recognized.
- **Maintain sharp corners (`0px` border-radius) as the default.** This defines IBM's structural, precise identity.
- **Pair buttons with adequate whitespace.** Minimum `16px` padding; avoid button clusters without separation.
- **Leverage the neutral gray scale for secondary content.** Use `#525252` for supporting text, `#161616` for primary.
- **Apply consistent padding multiples.** Use values from the spacing scale (`16px`, `24px`, `32px`, `40px`).
- **Use semantic colors for status.** Red for error, green for success, yellow for warnings—never arbitrary color assignments.
- **Ensure interactive elements meet 48px minimum height.** Supports accessibility and touch targets.
- **Build responsive layouts with mobile-first thinking.** Test spacing and typography at all breakpoints.
- **Use IBM Plex Sans exclusively** for consistency across all platforms and languages.

### Don't
- **Avoid using secondary or accent blues in place of the primary.** Reserve `#4589FF` and `#78A9FF` for specific hover/disabled states only.
- **Don't introduce rounded corners beyond isolated decorative use.** Sharp corners are the IBM standard.
- **Avoid dark mode without explicit semantic color mapping.** The current palette is light-mode optimized.
- **Don't exceed three font weights in a single design.** IBM Plex Sans: 300, 400, 600 are the canon.
- **Avoid mixing typography sizes arbitrarily.** Stick to the defined hierarchy table; incremental scaling maintains rhythm.
- **Don't add drop shadows to all elements.** Reserve shadows for elevation layers only (cards, modals, overlays).
- **Avoid text smaller than 12px** in user-facing interfaces; accessibility requires minimum readability.
- **Don't use high-contrast color combinations without testing for WCAG AA compliance.** All text must meet 4.5:1 contrast.
- **Avoid nesting more than two levels of navigation without a clear visual hierarchy.** Simplicity aids usability.
- **Don't deviate from the color palette without documented justification.** Consistency drives recognition and trust.

## 8. Responsive Behavior

### Breakpoints

| Breakpoint Name | Width | Key Changes |
|-----------------|-------|-------------|
| **Small (Mobile)** | `320px` | Single column; `16px` horizontal padding; `12px` gutters; font sizes reduced by 2–4px for smaller screens |
| **Medium (Tablet)** | `640px` | 2–4 column grid; `24px` horizontal padding; `16px` gutters; normal typography |
| **Large (Desktop)** | `1024px` | 8–12 column grid; `32px–48px` horizontal padding; `24px` gutters; full typography scale |
| **Extra Large (Wide Desktop)** | `1440px` | 12 column grid; max-width containers enforce `1440px` limit; `48px–64px` horizontal padding; `32px` gutters |

### Touch Targets
- **Minimum interactive element size:** `48px × 48px` (height × width)
- **Recommended spacing between touch targets:** `8px` minimum
- **Button padding on mobile:** `12px 16px` (min height maintained at `48px`)
- **Form inputs:** `48px` min height on all devices for consistent touch affordance

### Collapsing Strategy
- **Navigation:** Desktop horizontal menu → tablet dropdown menu → mobile hamburger menu (collapsible sidebar)
- **Grid layout:** Desktop 12-column → tablet 4–6 column → mobile single column (stacked)
- **Spacing:** Large (`48px`–`64px`) → Medium (`24px`–`32px`) → Small (`12px`–`16px`)
- **Typography:** Display text reduces by 6–8px on tablet; 10–12px on mobile (from `53px` → `38px` → `28px` example)
- **Cards:** Multi-column grid → 2-column → single column stacked
- **Padding/margins:** Containers reduce by 25–33% as screen shrinks; internal component padding stays consistent
- **Images:** Responsive sizing with `max-width: 100%`; aspect-ratio preservation via CSS or intrinsic sizing

## 9. Agent Prompt Guide

### Quick Color Reference

- **Primary CTA:** IBM Blue (`#0F62FE`)
- **Secondary CTA:** Bright Blue (`#4589FF`) for hover; Secondary Button with white background
- **Headings & Body Text:** Off-Black (`#161616`)
- **Secondary Text / Muted:** Medium Gray (`#525252`)
- **Borders & Dividers:** Light Border Gray (`#E0E0E0`)
- **Card/Container Background:** Pure White (`#FFFFFF`)
- **Secondary Surface:** Off-White (`#F4F4F4`)
- **Error State:** Error Red (`#DA1E28`)
- **Warning State:** Warning Yellow (`#F1C21B`)
- **Success State:** Success Green (`#24A148`)
- **Disabled Elements:** Light Gray (`#C6C6C6`) background; Light Medium Gray (`#8D8D8D`) text

### Iteration Guide

1. **All buttons default to `border-radius: 0px`** (sharp corners). Apply IBM Blue (`#0F62FE`) for primary, white background with blue text for secondary, transparent ghost variant.

2. **Typography foundation:** IBM Plex Sans, weights 300/400/600 only. H1 = `53px` / 300 weight. H3–H5 = `28px`/`20px`/`16px` @ 400 weight. Body = `16px` @ 400. Links = `14px` @ 400. Labels = `12px` @ 400.

3. **Spacing multiples:** Use only `4px`, `8px`, `12px`, `16px`, `24px`, `32px`, `40px`, `48px`, `64px`, `72px`. No arbitrary values.

4. **Color contrast:** All text must meet WCAG AA (4.5:1 minimum). Off-Black (`#161616`) on Pure White (`#FFFFFF`) or Light surfaces; Light Medium Gray (`#8D8D8D`) reserved for disabled/placeholder only.

5. **Shadows only for elevation:** Use the provided box-shadow values (Level 0–4) keyed to component depth. No custom shadows.

6. **Interactive element minimum:** `48px` height/width for all buttons, inputs, and clickable targets. Padding inside that envelope as needed.

7. **Cards & containers:** Default `background: #FFFFFF`, `border: 1px solid #E0E0E0`, `padding: 24px`, `border-radius: 0px`. Add shadow (Level 2+) only when elevation is intended.

8. **Forms:** Input background = `#F4F4F4`, focus state = blue border (`2px solid #0F62FE`). Error state = red border (`#DA1E28`). Maintain `12px` label font, `14px` input text.

9. **Responsive:** At `640px` breakpoint, shift to 2–4 column grid, reduce padding by 25%. At `320px` (mobile), use single column, `16px` padding, reduce typography by 4–6px. Always test touch targets remain ≥ `48px`.

10. **Component consistency:** Every button, input, card, and link must follow the palette and typography rules above. No exceptions without documented design rationale and stakeholder approval.