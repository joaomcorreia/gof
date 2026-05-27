# PRINT & DESIGN Template Roadmap

## Purpose

This file outlines the future structure for a customer-facing print services layer without implementing it yet.

This is roadmap material only.

## Homepage structure ideas

Future PRINT & DESIGN public landing structure could include:

1. Intro banner
   - short trust statement
   - PT-focused print/signage positioning
   - website + print bundle mention
2. Category grid
   - Business Cards
   - Flyers
   - Banners
   - Stickers
   - Menus
   - Vehicle Graphics
   - Custom Print Request
3. How it works
   - request
   - upload artwork or ask for design help
   - receive quote/proof
   - approve and produce
4. Bundle section
   - website + print launch kits
   - local service starter bundle
   - restaurant/cafe bundle
   - van/signage bundle
5. Partner trust section
   - Portugal printing/signage fulfillment notes
   - turnaround and coverage expectations
6. CTA area
   - request quote
   - discuss bundle
   - ask for custom work

## Service categories

Recommended first public categories:

- Business Cards
- Flyers
- Banners
- Stickers
- Menus
- Vehicle Graphics
- Custom Print Request

Possible future second-wave categories:

- Posters
- Roll-up banners
- Window graphics
- Shop signage
- Brochures
- Labels

## Quote-request flow ideas

### V1 quote-only flow

1. Select category
2. Enter contact details
3. Add size/quantity/finish notes
4. Add deadline and delivery region
5. Optional artwork-ready flag
6. Internal review
7. Partner quote or manual pricing

### V2 richer request flow

1. Category + product intent
2. Upload artwork or request design support
3. Internal print-readiness check
4. Quote
5. Proof review
6. Approval
7. Production and delivery

## Future upload/customizer roadmap

### Upload roadmap

- V1: no customer uploads
- V2: authenticated or tokenized artwork uploads
- V3: proof attachments, revision uploads, final production files

### Customizer roadmap

- V1: none
- V2: simple preview/configuration helper for standard products
- V3: richer proofing/customizer for selected categories only

Recommended rule:

- do not build a generic design studio before request and upload flows are proven

## Website + print bundle ideas

Potential bundle directions:

- New business starter
  - website
  - business cards
  - flyer starter batch
- Local service launch
  - website
  - van graphics consultation
  - business cards
- Restaurant/cafe starter
  - website
  - menus
  - window/signage items
- Seasonal promotion bundle
  - website landing update
  - flyers
  - banners
  - Promote campaign tie-in later

## PT / NL / BE pricing placeholders

These are placeholders for planning only, not real pricing:

- PT:
  - local fulfillment assumptions
  - VAT-sensitive partner pricing
  - delivery/install split
- NL:
  - higher labor/install assumptions
  - potentially different signage partner costs
- BE:
  - bilingual considerations
  - delivery-region complexity

Recommended eventual pricing model:

- quote-first for signage and custom work
- optional fixed-price presets later for standard print items

## Possible dashboard integration points later

If a real customer dashboard/framework is introduced later, potential PRINT & DESIGN slots:

- Requests
- Files
- Proofs
- Quotes
- Bundles
- Promote-linked campaigns

Recommended internal grouping later:

- Website
- Promote
- Print & Design
- Support

## Possible Promote integration later

Potential safe future integrations:

- flyer campaign linked to landing page update
- banner/signage campaign tied to seasonal offers
- website + print asset campaign package
- print request follow-up inside Promote workflows

Do not implement this until:

- role/capability model is stable
- quote workflow exists
- partner routing exists

## Recommended rollout order

### V1

- admin/staff-only placeholders
- isolated app
- no public exposure

### V2

- internal quote workflow
- upload handling
- partner assignment

### V3

- customer-facing requests
- proofing and approval
- bundle packaging
- selected Promote links
