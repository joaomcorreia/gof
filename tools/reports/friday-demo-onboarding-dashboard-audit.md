# Friday Demo Onboarding / Dashboard Audit

Date: 2026-05-27
Project: `C:\projects\getonlinefast.eu`
WP junction inspected read-only: `C:\projects\getonlinefast.eu\jcw-wp-current`

## Scope

This pass was an audit only.

- No Django code was changed.
- No WordPress code was changed.
- No plugin or theme versions were changed.
- The only file created in this pass is this report.

## Executive summary

The current Friday demo path is viable, but only as a guided two-part flow.

Django already provides a credible public journey for:

- landing page entry
- onboarding form start
- immediate website preview generation
- basic preview editing

The richer customer dashboard, payment/setup, media, role/capability, and visual editor flow does not live in Django. It already exists in the WordPress JCW Tools engine.

Because there is no current automated bridge from the Django preview flow into the WordPress customer/dashboard system, the shortest safe Friday demo is:

1. Start on the Django homepage or `/start/`
2. Submit onboarding
3. Show the generated Django preview
4. Move into a prepared WordPress customer/admin demo account
5. Show dashboard status, payment/setup, preview-status or editor handoff, and Facebook Launch Posts from WordPress

That is realistic for a startup/gemeente meeting. A fully seamless account-confirmation-to-dashboard flow is not present yet.

## Files inspected

### Django

- `config/urls.py`
- `core/views.py`
- `core/templates/core/home.html`
- `templates/includes/onboarding_modal.html`
- `ai_starter/urls.py`
- `ai_starter/views.py`
- `ai_starter/forms.py`
- `ai_starter/models.py`
- `ai_starter/templates/ai_starter/start.html`
- `ai_starter/templates/ai_starter/preview.html`
- `ai_starter/templates/ai_starter/frame.html`
- `ai_starter/README.md`
- `blog/urls.py`
- `blog/views.py`
- `templates/dashboard/guides/index.html`
- `templates/dashboard/guides/detail.html`
- `content/models.py`
- `content/views.py`
- `print_design/urls.py`

### WordPress junction, read-only

- `jcw-wp-current/wp-content/plugins/jcw-ai-assistant/jcw-ai-assistant.php`
- `jcw-wp-current/wp-content/plugins/jcw-ai-assistant/includes/admin/class-jcw-ai-assistant-admin.php`
- `jcw-wp-current/wp-content/plugins/jcw-ai-assistant/includes/admin/class-jcw-ai-assistant-dashboard-page.php`
- `jcw-wp-current/wp-content/plugins/jcw-ai-assistant/includes/admin/class-jcw-ai-assistant-payment-setup-page.php`
- `jcw-wp-current/wp-content/plugins/jcw-ai-assistant/includes/admin/class-jcw-ai-assistant-visual-editor-page.php`
- `jcw-wp-current/wp-content/plugins/jcw-ai-assistant/includes/admin/class-jcw-ai-assistant-media-page.php`
- `jcw-wp-current/wp-content/plugins/jcw-ai-assistant/includes/class-jcw-ai-assistant-social-content.php`
- `jcw-wp-current/wp-content/plugins/jcw-ai-assistant/includes/frontend/class-jcw-ai-assistant-frontend.php`
- `jcw-wp-current/wp-content/themes/jcw_default/` (presence only, no edits)

## Current routes / URLs found

### Django public and private routes

- `/`
  - homepage via `core:home`
- `/start/`
  - onboarding start via `ai_starter:start`
- `/preview/<uuid>/`
  - preview/editor page via `ai_starter:preview`
- `/preview/<uuid>/frame/`
  - iframe preview render via `ai_starter:preview_frame`
- `/blog/`
- `/blog/category/<slug>/`
- `/blog/<slug>/`
- `/dashboard/guides/`
- `/dashboard/guides/<slug>/`
- `/help/`
- `/help/<slug>/`
- `/admin/`
- `/admin/print-design/`
- `/admin/print-design/<service_slug>/`

### WordPress admin / tools routes discovered

- `wp-admin/admin.php?page=jcw-dashboard`
  - main JCW dashboard
- `wp-admin/admin.php?page=jcw-preview-status`
  - preview-customer status page
- `wp-admin/admin.php?page=jcw-tools-builder&tab=editor`
  - visual editor landing
- `wp-admin/admin.php?page=jcw-tools-builder&tab=editor&builder_page=page&page_id=<id>`
  - specific page editor entry
- `wp-admin/admin.php?page=jcw-tools-builder&tab=editor&builder_page=service&service_id=<id>`
  - specific service editor entry
- `wp-admin/admin.php?page=jcw-tools-builder&tab=branding`
- `wp-admin/admin.php?page=jcw-tools-builder&tab=advanced`
- `wp-admin/admin.php?page=jcw-tools-builder&tab=sidebars`
- `wp-admin/admin.php?page=jcw-tools-builder&tab=global-content`
- `wp-admin/admin.php?page=jcw-tools-media`
  - media manager
- `wp-admin/admin.php?page=jcw-tools-payment-setup`
  - setup details before payment
- `wp-admin/admin.php?page=jcw-tools-payment-success`
  - payment success/status foundation
- `wp-admin/admin.php?page=jcw-tools-facebook-content-setup`
  - Facebook setup page
- `wp-admin/admin.php?page=jcw-tools-social-content`
  - promote/social content area
- `wp-admin/admin.php?page=jcw-tools-promote-facebook`
  - Facebook Launch Posts style page
- `wp-admin/admin.php?page=jcw-tools-promote-google-ads`
- `wp-admin/admin.php?page=jcw-tools-promote-tiktok-ads`
- `wp-admin/admin.php?page=jcw-tools-promote-places`
- `wp-admin/upload.php`
- `wp-admin/media-new.php`

## Current models and data flow

### Django flow today

#### Public entry

The homepage injects `StarterOnboardingForm` and opens the onboarding modal.

The modal posts directly to `ai_starter:start`.

#### Onboarding request creation

`ai_starter.views.start_onboarding()` currently:

- validates a 3-field form
- creates a `Site`
- stores generated site content
- redirects to `/preview/<uuid>/`

Current form fields in `StarterOnboardingForm`:

- `business_name`
- `service_type`
- `city`

#### Preview storage

Primary active preview storage:

- `ai_starter.models.Site`
  - `public_id`
  - nullable `user`
  - `template_slug`
  - `color_palette`
  - `business_name`
  - `service_type`
  - `city`
- `ai_starter.models.SiteContent`
  - per-section/per-field text content
  - language-aware

Important detail:

- `Site.user` is optional
- preview generation works without registration or login

#### Unused or incomplete onboarding data model

`StarterOnboardingSubmission` exists with richer fields:

- `short_description`
- `phone`
- `email`

But it is not currently used by the active start flow.

#### Preview editing

`ai_starter.views.preview()` supports:

- save text edits
- apply template
- apply palette
- regenerate suggestions

This is enough for a demo preview/edit moment.

### WordPress flow today

The deeper customer operations are already modeled in the JCW Tools WordPress plugin.

#### Role/capability system

Found in `class-jcw-ai-assistant-admin.php`:

- `jcw_client`
- `jcw_client_owner`
- `jcw_client_manager`
- `jcw_client_viewer`
- `jcw_preview_customer`
- `jcw_tools_access`

This is the role/capability system the Django project currently does not have.

#### Dashboard and preview-status structure

WordPress already has:

- a main dashboard page
- a preview-customer status page
- redirect logic that sends preview customers to `jcw-preview-status`

#### Payment/setup data

`class-jcw-ai-assistant-payment-setup-page.php` stores setup/payment-prep data in user meta:

- plan type
- domain choice
- requested domain
- backup domain
- email account names
- Facebook page URL
- setup notes

It also includes:

- payment success foundation page
- Facebook setup continuation
- a status progression model

#### Social / Promote data

`class-jcw-ai-assistant-social-content.php` already exposes a Facebook-oriented dashboard flow with:

- service selection/content direction
- preview routes
- explicit “nothing is published automatically” messaging

This is the most natural place for the “Facebook Launch Posts” page in the Friday demo.

## What already works

### Django

- Public homepage entry into onboarding
- Standalone `/start/` onboarding page
- Preview creation without login
- Generated preview URL with UUID
- Preview iframe rendering
- Basic preview editing/regeneration
- Private `print_design` routes exist, but they are unrelated to the Friday website demo path

### WordPress

- Real dashboard structure
- Real customer role/capability architecture
- Preview-customer status page concept
- Media manager route
- Visual editor route family
- Setup/payment foundation
- Payment success foundation page
- Facebook setup page
- Promote/Facebook page structure

## What is broken, missing, or misleading for the Friday story

### 1. No real Django registration flow

I did not find a custom registration/signup flow, confirmation flow, or customer login journey in Django.

There is no practical “user registers, confirms, then enters dashboard” implementation here.

### 2. No email confirmation implementation

No active email confirmation or verification flow was found in the Django project.

For Friday, requiring this would slow the demo down without giving a real benefit.

### 3. No real Django customer dashboard

The only current `/dashboard/...` pages in Django are login-gated blog guides.

This is not a website status dashboard and should not be presented as one.

### 4. No automated bridge from Django preview into WordPress customer tools

There is no observed linkage that:

- creates a WordPress customer from the Django onboarding
- maps a Django preview to a WordPress site/customer
- sends the user automatically into the correct WordPress dashboard/editor/status page

This is the main gap blocking a seamless demo.

### 5. Public copy overpromises current implementation

Examples from the homepage/modal imply future behavior that is not yet fully wired:

- “Available inside your dashboard whenever you need it”
- “Register, confirm your details, and your website is ready to go live.”
- modal saved-state text mentioning the next login/payment/dashboard step

Those statements are directionally aligned with the plan, but not fully true in the current Django-only flow.

### 6. Onboarding modal has a form/template mismatch

`templates/includes/onboarding_modal.html` checks for a `short_description` field layout case, but `StarterOnboardingForm` currently has only 3 fields.

This does not appear to break the form, but it shows the richer onboarding path was started and not finished.

### 7. Coupon / referral / source handling is not part of the current Django flow

I did not find active Django onboarding fields for:

- coupon
- referral
- source

WordPress does contain referral/discount-related language, but it is not part of the current Django onboarding path.

## Shortest Friday demo path

### Recommended live demo sequence

#### Part A: Public request and preview in Django

1. Open homepage `/`
2. Click the private preview CTA
3. Submit onboarding with:
   - business name
   - service type
   - city
4. Show redirect to `/preview/<uuid>/`
5. Demonstrate:
   - generated preview
   - simple text edit
   - regenerate suggestions

This is the strongest working proof on the Django side.

#### Part B: Assisted handoff into WordPress dashboard

6. Switch to a prepared WordPress user/session
7. Open:
   - `wp-admin/admin.php?page=jcw-dashboard`
8. Show:
   - customer dashboard
   - website module cards
   - any preview/status card you want to highlight
9. Open setup/payment area:
   - `wp-admin/admin.php?page=jcw-tools-payment-setup`
10. Show payment status foundation:
   - `wp-admin/admin.php?page=jcw-tools-payment-success`
11. Show editor handoff:
   - `wp-admin/admin.php?page=jcw-tools-builder&tab=editor`
12. Show Facebook Launch Posts next:
   - `wp-admin/admin.php?page=jcw-tools-promote-facebook`

### Best framing for the meeting

Frame it as:

- “The website request and instant preview happen here.”
- “After that, the customer enters their guided workspace/dashboard here.”

Do not claim it is already one seamless account system unless you add the bridge first.

## Recommended placement for requested Friday demo elements

### 1. `STARTUP50 / €275 + VAT` activation message

Best placement for Friday:

- WordPress dashboard card or payment/setup card
- optionally mirrored on the payment success foundation page

Reason:

- the activation/setup/payment conversation already exists there
- Django does not currently own activation state or payment flow

Recommendation:

- implement as a temporary dashboard/payment module message in WordPress, not in Django preview flow

### 2. Facebook Launch Posts dashboard page

Best placement:

- existing WordPress route `jcw-tools-promote-facebook`

Reason:

- that structure already exists
- it already matches the intended “next step after website” story

### 3. “Website ready for preview” dashboard card

Best placement:

- WordPress `jcw-dashboard`

Reason:

- this is the actual dashboard system
- it is already module/card-driven
- it is the most credible place to show readiness state

Secondary option:

- WordPress `jcw-preview-status` for restricted preview customers

## Email confirmation recommendation for Friday

Email confirmation should be bypassed or softened for the Friday demo.

Reason:

- there is no real Django confirmation flow in place
- adding one now would be new product logic, not stabilization
- it would slow the demo and add failure risk

Recommended Friday approach:

- no hard confirmation requirement
- either use direct preview creation only
- or use prepared demo accounts in WordPress after preview creation

If needed, present confirmation as:

- a planned follow-up step
- or a manual support-assisted step after preview approval

## What can be manual or assisted behind the scenes

For Friday, the following can safely be manual:

- logging into the prepared WordPress customer/admin account
- selecting the correct dashboard or preview-status view
- opening the editor URL directly
- setting the dashboard state to show “ready for preview”
- setting or presenting the activation offer manually
- preparing Facebook setup/demo content beforehand
- matching the Django preview business to a prepared WordPress demo site manually

This is acceptable for an MVP/meeting demo as long as it is presented honestly.

## Recommended next Codex tasks in priority order

### Priority 1

Create the shortest Django-to-WordPress handoff mechanism.

Best target:

- from Django preview page to a controlled “continue to dashboard” destination
- even if initially staff/demo-only

### Priority 2

Add a WordPress dashboard card:

- “Website ready for preview”
- linked to preview-status or editor entry

### Priority 3

Add the activation offer message in WordPress:

- `STARTUP50`
- `€275 + VAT`
- scope and validity text

This should live with setup/payment or the dashboard card, not as a Django-only message.

### Priority 4

Decide the Friday auth story:

- prepared shared demo account
- or lightweight demo-user creation

Avoid building full email confirmation before the meeting.

### Priority 5

Clean the public copy that currently implies a finished dashboard/account system if that language will be shown live.

Minimum target:

- homepage/dashboard wording
- onboarding modal saved-state wording

### Priority 6

Optionally extend Django onboarding with one extra safe field set for better demo realism:

- short description
- email
- phone

Only do this if it can be completed cleanly without delaying the dashboard bridge.

## Risks

- Risk: the audience assumes Django and WordPress are already one connected account flow.
  - Mitigation: present the handoff clearly, or build a minimal bridge first.

- Risk: public homepage copy implies registration/dashboard behavior that is not implemented.
  - Mitigation: soften the wording or avoid overexplaining those parts in the meeting.

- Risk: trying to add real registration, confirmation, coupons, and payment logic before Friday will create instability.
  - Mitigation: keep Friday focused on preview + guided dashboard handoff.

- Risk: the requested `STARTUP50 / €275 + VAT` message conflicts with current WordPress activation defaults.
  - Current code default found in plugin bootstrap: activation price option initializes to `325`.
  - Mitigation: decide whether Friday uses a temporary promotional override or a purely presentational message.

- Risk: there is no current automatic site/user synchronization between Django preview data and WordPress tools data.
  - Mitigation: use a prepared WordPress demo account and manual mapping for Friday.

## Recommended Friday positioning

For the meeting, the safest honest message is:

- “Customers can request and preview their website immediately.”
- “After that, they continue in their managed dashboard where setup, payment, editing, and launch support happen.”

That statement matches the current architecture direction even though the bridge is not fully automated yet.

## Whether any code changed

Yes, one non-runtime file was added:

- `tools/reports/friday-demo-onboarding-dashboard-audit.md`

No Django runtime code changed.
No WordPress files changed.
