# Balik-Lamig Landing Page Redesign Prompt

Redesign the Balik-Lamig main landing page at `/balik-lamig/` into a premium, visually polished air-conditioning and refrigeration services website.

## Step 0: Inspect first, then plan

1. Identify the framework and templating engine.
2. Locate the landing-page template, stylesheets, base layout/nav/footer templates, existing brand assets, prototype disclaimers, and coverage-area data.
3. Check whether the landing stylesheet is shared with `/balik-lamig/book` or staff pages.
4. Reply with a short plan listing files to touch, files not to touch, and assumptions.
5. Then proceed.

## Design direction

Use the existing Balik-Lamig dark identity:

- Deep navy/charcoal background
- Cyan/teal interface accents
- Warm orange brand highlights
- System fonts only
- High contrast and generous spacing
- CSS-only technical/blueprint texture
- Premium operations-dashboard quality

## Landing-page structure

Use one `<h1>`, logical heading order, and `<section aria-labelledby="...">` for each section.

### 1. Hero

- Use the existing Balik-Lamig brand image with meaningful alt text, explicit dimensions, and no lazy-loading.
- If unavailable, create a CSS-only hero graphic.
- Headline: **Reliable Aircon Service for Comfortable Spaces**
- Use neutral supporting text with no claims about speed, certifications, guarantees, or superiority.
- Primary CTA: **Request a service** → `/balik-lamig/book`
- Secondary CTA: **Explore our services** → `#services`
- Use smooth scrolling only under `prefers-reduced-motion: no-preference`.

### 2. Services

Create cards for Cleaning, Repair, Installation, Dismantle, Reprocess, Reconditioning, Replacement, Maintenance, Electrical, and Mechanical.

Each card must contain a CSS-drawn icon or existing asset, a title, and one neutral sentence. Do not use words such as “expert,” “same-day,” “certified,” or “best.” Cards may link to `/balik-lamig/book` without query parameters or prefilled data.

### 3. How it works

Show this four-step journey with CSS connectors:

`Request service → Staff review → Team scheduling → Service progress`

Use a horizontal layout on desktop and vertical layout on mobile.

### 4. Why Balik-Lamig

Show four neutral highlights: careful review, organized scheduling, local service workflow, and transparent process. Do not claim certifications, guarantees, reviews, real customer results, or production automation.

### 5. Service coverage

Use existing project data/configuration/templates for the fictional coverage area. Do not invent new areas without asking. Keep all data synthetic and non-sensitive.

### 6. Automation preview

Explain the controlled internal workflow and synthetic n8n staging automation. Clearly state:

> No customer messages, payments, or real bookings are processed.

### 7. Final CTA

Encourage a fictional service request and link to `/balik-lamig/book`.

## Safety and wording

- Preserve all existing prototype/synthetic-only safety language.
- Add a visible concise prototype notice in the landing page header or footer.
- Do not edit shared base templates unless unavoidable.
- Do not add production claims, real contact details, testimonials, pricing, or payment features.

## Technical constraints

- Change only the landing-page template and its CSS.
- Use a dedicated stylesheet such as `landing.css`, or scope styles under `.bl-landing`.
- Do not modify global selectors or shared CSS.
- Do not change backend routes, form behavior, database models, workflow logic, n8n integration, or automation behavior.
- Keep `/balik-lamig/book` unchanged in functionality and appearance.
- Use no external libraries, fonts, images, CDNs, or tracking.
- Use CSS-only animations/transitions and disable them under `prefers-reduced-motion: reduce`.
- Support approximately 375px, 768px, and 1280px layouts with no horizontal scrolling.

## Accessibility requirements

- WCAG AA contrast: 4.5:1 body text and 3:1 large text/UI components.
- Verify orange-on-navy and cyan-on-navy combinations.
- Add a skip-to-content link.
- Add visible `:focus-visible` styles.
- Use minimum 44px tap targets.
- Use semantic header, navigation if present, main, and footer landmarks.
- Hide decorative icons with `aria-hidden="true"`.
- Add meaningful alt text to meaningful images.
- Ensure keyboard operability.

## Verification required before finishing

1. Run the existing test suite and report results.
2. Report HTTP status for `/balik-lamig/`, `/balik-lamig/book`, and every existing staff route.
3. Confirm the booking form still renders and its fields, action, and method are unchanged.
4. Show `git diff --stat` proving only intended template/CSS files changed.
5. Check layouts at approximately 375px, 768px, and 1280px.
6. Report layout issues, assumptions, and anything that could not be verified.

## Goal

Create a credible portfolio-quality landing page and polished future service brand while keeping the project clearly local, synthetic-only, and safe.
