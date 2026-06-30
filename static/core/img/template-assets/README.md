# Template Assets

Canonical reusable template image folder:

`static/core/img/template-assets/`

Place reusable demo/template images for GOF templates and starting designs here.

Recommended reusable structure:

`static/core/img/template-assets/<template-slug>/logo/`

`static/core/img/template-assets/<template-slug>/hero/`

`static/core/img/template-assets/<template-slug>/services/`

`static/core/img/template-assets/<template-slug>/portfolio/`

`static/core/img/template-assets/<template-slug>/backgrounds/`

Planned category folders:

- `generic-business`
- `gof-platform`
- `construction-trades`
- `auto-garage`
- `print-shop`
- `security`
- `taxi-transport`
- `food-restaurant`
- `beauty-wellness`
- `technology`
- `creative-premium`

Templates should only use images from their assigned category folders once the image library is organized.

Example:

`static/core/img/template-assets/axial-pagina/logo/logo-main.png`

`static/core/img/template-assets/axial-pagina/hero/hero-01.jpg`

`static/core/img/template-assets/axial-pagina/services/service-01.jpg`

`static/core/img/template-assets/axial-pagina/portfolio/portfolio-01.jpg`

`static/core/img/template-assets/axial-pagina/backgrounds/bg-01.jpg`

Recommended file names:

- `logo-main.png`
- `hero-01.jpg`
- `service-01.jpg`
- `portfolio-01.jpg`
- `bg-01.jpg`

Allowed folders:

- `logo`
- `hero`
- `services`
- `portfolio`
- `backgrounds`

Allowed image formats for now:

- `.jpg`
- `.jpeg`
- `.png`

Current template-asset note:

- `.png`, `.jpg`, and `.jpeg` are the standard reusable template image formats for the current workflow.
- `.webp` can be added later as an optional format, but it is not required now.
- `project-assets` is not the canonical folder name for reusable template images.

`creative-premium` intended use:

- creative/editorial/premium-style templates
- parallax-ready images
- strong hero/background images
- portfolio/detail visuals
- later this can support premium visual effects

Suggested `creative-premium` subfolders:

- `hero`
- `parallax`
- `portfolio`
- `backgrounds`
- `details`

Parallax notes for later:

- V1 parallax should be simple and safe.
- Use solid fallback backgrounds.
- Disable or fallback parallax on mobile if needed.
- More advanced parallax or scroll effects can come later as premium visual sections.

Before live launch, the customer should confirm permission to use:

- logo files
- photos
- portfolio/work examples
- business details shown together with those assets

This folder system is for staff/manual template preparation only.

Customer/public uploads and a real media manager are future work and are not part of this pass.

Future WordPress handoff compatibility:

- Django-side helpers return both:
  - a Django preview/static path or URL
  - a stable relative template asset path such as `template-assets/axial-pagina/hero/hero-01.jpg`
- A later WordPress handoff/import can use that relative path to:
  - copy selected files from `template-assets/<template-slug>/...`
  - upload/import them into the WordPress Media Library
  - replace Django static paths with WordPress attachment IDs or WordPress media URLs
  - assign those imported assets to JCW Tools logo, hero, services, portfolio, and background fields

WordPress import is not implemented in this pass.
