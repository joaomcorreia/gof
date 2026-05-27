# PRINT & DESIGN Investigation

## Scope of this pass

This is a stabilization and planning pass only.

No print product engine, customizer, payments, or customer-facing print flows are added in this phase.

## Current implementation checkpoint

This repository now has a first isolated private foundation in the `print_design` app.

Current private route base:

- `/admin/print-design/`

Current protection model:

- staff-only via Django admin access rules

Current placeholder scope:

- Business Cards
- Flyers
- Banners
- Stickers
- Menus
- Vehicle Graphics
- Custom Print Request

## Current architecture notes

### 1. Public navigation and page registration

- Public site navigation is hardcoded in `templates/includes/site_header.html`.
- Main page/url registration is split across:
  - `config/urls.py`
  - `core/urls.py`
  - `content/urls.py`
  - `blog/urls.py`
  - `ai_starter/urls.py`
- There is no generalized internal "module registry" or grouped tools menu in this repository.
- There is also no full JCW Tools sidebar/menu framework present in this codebase today, despite references in project planning.

### 2. Private/hidden content logic that already exists

- The strongest reusable visibility system is `content.Article` in `content/models.py`.
- Existing visibility states:
  - `public`
  - `logged_in`
  - `customer_only`
  - `admin_only`
- Section placement flags already exist:
  - `show_in_help_center`
  - `show_on_blog`
  - `show_in_dashboard`
- Access filtering is implemented in:
  - `content/views.py`
- Important limitation:
  - `customer_only` currently behaves the same as `logged_in` in `content/views.py`.
  - There is no true customer-vs-admin capability split yet.
- `blog/views.py` also has a simpler private pattern via `@login_required(login_url='/admin/login/')` for guides.

### 3. Placeholder page patterns

- Generic placeholder shell exists in `core/templates/core/placeholder_page.html`.
- Generic structured offer/detail shell exists in `core/templates/core/detail_page.html`.
- These are public-theme templates and should not be used as the long-term basis for a private tools module unless a very small placeholder is needed temporarily.

### 4. Forms and request capture

- Contact flow:
  - `core/forms.py`
  - `core/views.py`
- AI starter onboarding flow:
  - `ai_starter/forms.py`
  - `ai_starter/views.py`
  - `ai_starter/models.py`
- Current forms are text-only.
- No reusable file upload flow exists yet.
- No `FileField` or `ImageField` storage model exists in the active app code for user-submitted assets.

### 5. Media and image handling

- `MEDIA_ROOT` / `MEDIA_URL` are configured in `config/settings.py`.
- Existing content/blog "images" are URL-based, not uploaded files:
  - `blog/models.py`
  - `content/models.py`
- Admin preview of remote images exists in:
  - `blog/admin.py`
  - `content/admin.py`
- There is no dedicated media permission layer.

## Reusable systems already present

### Most reusable now

- `content.Article` visibility + placement model for private placeholder entries.
- `blog` login-gated guide pattern for protected pages.
- `ai_starter` request/edit flow as a reference for future multi-step request handling.
- Django admin registrations in:
  - `content/admin.py`
  - `blog/admin.py`
  - `ai_starter/admin.py`

### Weakly reusable

- `core.ContactForm` is only useful as a very basic anti-spam form pattern.
- `ai_starter.Site` / `SiteContent` show a workable pattern for staged edits and later regeneration, but they are website-preview-specific, not suitable as-is for print product logic.

### Not present in this repo

- No visible Promote module implementation.
- No Portfolio module.
- No Projects module.
- No structured quote-request system.
- No customer dashboard/sidebar capability framework beyond login-gated guide pages.
- No upload manager for customer files.

## Stability assessment

### Stable enough for next phase?

Yes, but only if the PRINT & DESIGN work starts as an isolated private app or admin-only content section.

That is now the recommended and implemented direction for this repository state.

### Stable enough for full customer-facing print expansion?

Not yet.

The current repository is missing:

- a true module/menu registry
- real role/capability separation
- upload storage and validation primitives
- structured quote/request models
- partner/reseller workflow models
- a customer-facing authenticated tools area distinct from Django admin

## Recommended safe foundation

### Best short-term approach

For the next implementation phase, keep PRINT & DESIGN private and isolated.

Recommended direction:

1. Create a dedicated app later, for example `print_design`.
2. Keep first URLs private/admin-only.
3. Start with placeholder entries/pages only.
4. Avoid public theme integration until role visibility and upload strategy are defined.

This approach has now been applied with a staff-only route namespace instead of public theme integration.

### Why not use the public templates directly?

- The current public navigation is static.
- Private tools visibility is not centrally managed there.
- Mixing future print workflows into public templates too early will increase risk while client-viewer rules are still unsettled.

## Recommended future structure

### V1: Private/admin-only foundation

- Dedicated `print_design` app
- Admin-registered models only
- Private placeholder pages for:
  - Business Cards
  - Flyers
  - Banners
  - Stickers
  - Menus
  - Vehicle Graphics
  - Custom Print Request
- Visibility restricted to staff/admin only
- Placeholder copy:
  - "This service is being prepared and is not available yet."

Recommended model direction for V1:

- `PrintCategory`
  - slug
  - title
  - description
  - sort_order
  - is_active
- `PrintService`
  - category
  - slug
  - title
  - status
  - visibility
  - internal_notes
  - public_summary
- Optional later:
  - `PrintServiceContent` if flexible modular content is needed

### V2: Quote requests + uploads

Introduce structured request handling before any product/pricing engine.

Recommended models:

- `PrintRequest`
  - requester
  - company_name
  - contact_name
  - email
  - phone
  - category
  - service
  - quantity_notes
  - size_notes
  - finish_notes
  - deadline
  - delivery_location
  - status
  - source
  - assigned_partner
  - created_at
- `PrintRequestFile`
  - print_request
  - file
  - original_name
  - mime_type
  - uploaded_by
  - created_at

Key requirement before V2:

- use real file storage with validation, not URL fields
- define file size/type limits
- define whether uploads are admin-only, customer-authenticated, or token-based

### V3: Preview/customizer V2

Do not build this until request intake and upload flow are proven.

Recommended eventual split:

- simple configuration preview
- artwork upload + proof review
- revision workflow
- approval state

Do not couple the future preview/customizer to the current `ai_starter` preview system directly.

Reuse concepts from `ai_starter` only:

- staged edits
- structured section data
- regeneration/version thinking

Do not reuse its current models as the print customizer base.

### Future print product categories

Recommended top-level structure:

- Business Cards
- Flyers
- Banners
- Stickers
- Menus
- Vehicle Graphics
- Custom Print Request

Each should eventually support:

- default specification schema
- quote-only mode first
- later optional fixed-price presets

### Partner/reseller workflow

Recommended future model direction:

- `PrintPartner`
  - company_name
  - region
  - contact_name
  - email
  - phone
  - specialties
  - supports_delivery
  - supports_installation
  - active
- `PartnerCapability`
  - partner
  - category
  - material_or_service
  - notes
- `PartnerQuote`
  - print_request
  - partner
  - quoted_price
  - turnaround_days
  - notes
  - status

Portugal-focused needs to decide early:

- local pickup vs shipping
- installation-capable partners
- mainland vs islands handling
- Portuguese invoicing expectations
- VAT handling responsibilities

## Risks and problems to solve before full build

### 1. Role separation is not real enough yet

`customer_only` is not truly separate from `logged_in` today.

Before public/customer PRINT & DESIGN work:

- define customer roles
- define staff/admin roles
- define module visibility per role

### 2. No internal tools menu framework

There is no reusable grouped tools sidebar or registry in this repository.

Before expansion:

- decide whether private tools live in Django admin
- or in a custom authenticated tools area
- or in a future JCW dashboard app

### 3. No upload foundation

Print requests will depend on uploads very early.

Before V2:

- choose storage strategy
- define allowed formats
- define proof/download access rules

### 4. No quote pipeline yet

There is no structured quote/request lifecycle:

- submitted
- reviewing
- waiting for files
- partner pricing
- proofing
- approved
- production
- delivered

### 5. Media is URL-oriented today

Current image handling is remote-link based. That is insufficient for artwork intake, proofs, and production files.

### 6. Public/private boundaries are still easy to blur

Because the public site and authenticated content patterns are relatively simple, it would be easy to expose PRINT & DESIGN too early without a strict namespace and role plan.

## Recommended implementation order

### V1

- Private app scaffolding
- Staff-only routes
- Placeholder service pages
- Admin model registration
- No uploads
- No customer access

### V2

- Structured print requests
- File uploads
- Internal statuses
- Admin processing workflow
- Optional partner assignment

### V3

- Customer-facing request tracking
- Proofing/revision flow
- Bundle logic with website services
- Partner/reseller automation
- Preview/customizer V2

## Open questions for Portugal printing partner

- Which products are truly launch-ready first?
- Which products need installation vs shipping only?
- What artwork formats are acceptable?
- Who checks print readiness?
- Who owns proof approval?
- What turnaround times are realistic per category?
- Do prices come from fixed tables or partner quotes?
- Are there white-label/reseller requirements?
- Which geographic areas are supported first?
- How should Portuguese VAT/invoicing be handled operationally?

## Recommended next technical move

When implementation begins, prefer:

- a new isolated `print_design` app
- staff-only URLs first
- admin-managed placeholder/service records
- no public navigation exposure
- no customer-facing upload flow until the role and storage model are explicit
