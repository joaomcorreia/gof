# Visual Editor Audit: `jcw_wp` vs `jcw_construction_test`

Date: 2026-05-27

## Scope

This was a comparison pass only.

- No code was changed in either WordPress branch.
- No files were copied.
- No folders were merged.
- This report is the only file created.

Compared branches:

- Current branch under test:
  - junction: `C:\projects\getonlinefast.eu\jcw-wp-current`
  - real path: `C:\wamp64\www\jcw_construction_test`
- Old/reference branch:
  - `C:\wamp64\www\jcw_wp`

## Executive summary

The current `jcw_construction_test` Visual Editor is not a downgrade of the old `jcw_wp` editor overall. It is mostly a larger, more capable version of the same system.

The most important finding is:

- I did **not** find an old high-value direct-edit engine in `jcw_wp` that should replace the current branch.
- I **did** find a few smaller old UX traits that were more explicit or easier to discover.
- The current branch also adds several editor behaviors that should be preserved, especially section background controls and live background preview.

So the right next move is not replacement. It is a small UX cleanup pass inside the current branch.

## Files inspected

### Old/reference branch: `C:\wamp64\www\jcw_wp`

- `AGENTS.md`
- `wp-content/plugins/jcw-ai-assistant/includes/admin/class-jcw-ai-assistant-builder-page.php`
- `wp-content/plugins/jcw-ai-assistant/includes/admin/class-jcw-ai-assistant-visual-editor-page.php`
- `wp-content/plugins/jcw-ai-assistant/assets/js/jcw-ai-editor-panel.js`
- `wp-content/plugins/jcw-ai-assistant/assets/js/jcw-hero-image-field.js`

### Current branch: `C:\projects\getonlinefast.eu\jcw-wp-current`

- `wp-content/plugins/jcw-ai-assistant/includes/admin/class-jcw-ai-assistant-builder-page.php`
- `wp-content/plugins/jcw-ai-assistant/includes/admin/class-jcw-ai-assistant-visual-editor-page.php`
- `wp-content/plugins/jcw-ai-assistant/assets/js/jcw-ai-editor-panel.js`
- `wp-content/plugins/jcw-ai-assistant/assets/js/jcw-hero-image-field.js`

## Render path found

In both branches, the Visual Editor is still entered through the Builder page and rendered from the same main class path:

- Builder entry:
  - `includes/admin/class-jcw-ai-assistant-builder-page.php`
  - `tab=editor`
- Visual Editor implementation:
  - `includes/admin/class-jcw-ai-assistant-visual-editor-page.php`

The standalone helper JS files checked here are unchanged between branches:

- `jcw-ai-editor-panel.js`
- `jcw-hero-image-field.js`

That means the meaningful UX differences are mostly inside the large PHP Visual Editor page and its inline script, not those shared helper files.

## Comparison by requested area

### 1. Field-focused drawer behavior

Assessment:

- Current branch is stronger.
- Old branch already had a contextual drawer with:
  - unsaved state
  - cancel
  - save
  - AI suggest button slot
  - fallback section link
- Current branch keeps that and expands it with:
  - grouped drawer panels
  - richer field UI metadata
  - background-specific controls
  - service card icon support
  - more structured contextual field handling

Useful old behavior worth noting:

- The old branch was slightly more straightforward in how the editor introduced the drawer.
- The current branch is more powerful, but the surrounding UI makes some of that power less immediately obvious unless the user opens Help or Advanced.

Conclusion:

- No old drawer engine needs to be ported.
- Only discoverability polish is worth porting back in spirit.

### 2. Direct text click behavior

Assessment:

- Core direct text click behavior is still present in the current branch.
- The current branch explicitly documents it in the Help menu:
  - “Click text to edit that exact field.”

Difference:

- Old branch used always-visible instructional text above the preview:
  - use the site menu
  - click a section to edit
- Current branch compresses this into a cleaner toolbar and Help dropdown.

What is better in old branch:

- Immediate discoverability.

What is better in current branch:

- More precise contextual routing once the user already understands the workflow.

Recommendation:

- Restore a small always-visible hint line in the current branch.

### 3. Direct image click behavior

Assessment:

- Current branch is stronger.
- Both branches support mapped image fields and the image picker flow.
- Current branch keeps the direct image-target handling and adds more structure for preview metadata and grouped field handling.

Important current-only advantage:

- background/image editing is much broader now because section background controls are part of the same system.

Conclusion:

- No old image-click behavior appears missing in the current branch.

### 4. Button/link editing behavior

Assessment:

- Current branch is at least as capable as the old branch.
- Both branches map:
  - `button_text`
  - `button_url`
  - `cta_primary_text`
  - `cta_primary_url`
  - `cta_secondary_text`
  - `cta_secondary_url`
  - `link_url`

Current branch appears better because:

- field UI metadata is richer
- contextual grouping is broader
- more page/section combinations are covered

Conclusion:

- Nothing from old button/link editing needs restoration.

### 5. Section settings behavior

Assessment:

- Current branch is significantly stronger.

Current-only behavior found:

- admin-only section background controls
- background reset-to-default intent
- richer section settings grouping
- background preset/default resolution
- live background preview application in the iframe

This is one of the main areas that must be preserved.

### 6. Hero / slider editing behavior

Assessment:

- Current branch is stronger overall.
- Old branch already had grouped hero handling for:
  - eyebrow
  - title
  - subtitle
  - description/body
  - hero buttons
  - hero image
  - slide image/button fields
- Current branch keeps and expands this, while also adding background behavior and wider mapping.

Potential old advantage:

- The old UI framing around hero editing was more explicit.

But functionally:

- current branch is not worse.

### 7. AI suggestion availability per field

Assessment:

- No evidence that `jcw_wp` has broader standalone AI field support than the current branch.
- Shared helper file `jcw-ai-editor-panel.js` is unchanged.
- Current branch keeps AI metadata wiring and extends the editor field ecosystem.

Conclusion:

- No old AI suggestion behavior stands out as missing.

### 8. Save / cancel behavior

Assessment:

- Both branches support:
  - cancel
  - save
  - unsaved-changes indicator
- Current branch retains the same core flow.

Current branch additionally adds more field-state handling around backgrounds.

Conclusion:

- No old save/cancel behavior appears superior enough to port directly.

### 9. Preview refresh behavior

Assessment:

- Both branches include `Refresh Frame`.
- Old branch already had “Saved. Preview refreshed.”
- Current branch keeps refresh behavior and expands preview-side live updates for background controls.

Important current-only gain:

- live background preview without waiting for a full save cycle.

Conclusion:

- Current branch must keep this newer preview behavior.

### 10. JS / PHP differences that explain UX differences

Main explanation:

- The helper JS files checked are identical.
- The UX differences mostly come from inline script and PHP UI decisions inside `class-jcw-ai-assistant-visual-editor-page.php`.

Current branch adds:

- `get_editor_add_links()`
- Help dropdown
- Add dropdown
- duplicate `Full width` and `Desktop` preview controls
- section background permissions and support checks
- background reset-to-default flow
- background preview defaults
- `applySectionBackgroundPreview()`
- `resetBackgroundPreviewToDefaults()`
- service card icon editing support

Old branch kept more always-visible explanatory UI:

- dedicated intro card
- dedicated “How to navigate” card
- more obvious first-run guidance before the user interacts

## Features present in `jcw_wp` but missing or weaker in `jcw_construction_test`

These are the only meaningful old UX advantages I found:

- The old editor had stronger always-visible onboarding text around how to use the preview.
- The old editor separated the intro/explanation area from the preview more clearly, which likely made first use easier.
- The old preview mode control was simpler and less confusing.

Specific current weakness versus old:

- The current branch adds both `Full width` and `Desktop`, but both point to the same desktop preview mode URL. That is clutter at best and confusing at worst.

I did **not** find a clearly better old implementation of:

- direct text click routing
- image click routing
- button/link editing
- AI field editing
- save/cancel flow

## Features present in `jcw_construction_test` but missing in `jcw_wp`

These are significant and should be preserved:

- Section background controls
- Background live preview in the frame
- Background reset-to-default flow
- Background preset/default merging
- Section settings handle and grouping improvements
- Add menu / content creation shortcuts in the editor toolbar
- Service card icon editing support
- Broader field UI metadata for modern controls
- Construction preset related support

These are not “extra noise”; they are real editor capability gains.

## Which specific old behavior should be ported

Only small UX behavior should be ported, not systems.

Recommended old behavior to port into the current branch:

- Restore a short always-visible helper line near the preview header.
  - Example intent:
  - use the site menu
  - click text to edit exact content
  - click section background to edit the section
- Simplify the first-run editor framing so a new user does not need to open Help to understand direct editing.
- Clean up the preview mode switch so it is obvious what each mode does.

The biggest concrete port-worthy item is not code from old branch. It is the old branch’s clearer onboarding/discoverability.

## Which current behavior must be preserved

- Section background controls
- Background live preview
- Background default/preset restore behavior
- Section settings handle behavior
- Construction preset compatibility
- Current direct drawer save pipeline
- Current contextual field routing
- Current service card icon support

Do not remove these to chase old simplicity.

## Recommended safest next Codex task

Safest next task:

- Do a **small Visual Editor UX cleanup pass in the current branch only**.

Recommended scope:

1. Add one always-visible instruction strip above or beside the preview.
2. Remove or properly differentiate the duplicate `Full width` / `Desktop` control.
3. Keep Help and Add menus, but make the core direct-edit behavior visible without opening menus.
4. Do not touch the background save pipeline unless a specific bug is found.

That would recover the main usability benefit of the old branch without risking the newer current features.

## Risks

- Risk: trying to “port old behavior” too broadly could accidentally remove current background and section-settings capabilities.
- Risk: the old branch is simpler partly because it has fewer capabilities, not because its interaction model is fundamentally better.
- Risk: if the next pass edits the huge inline script aggressively, it could break contextual target mapping or preview refresh behavior.
- Risk: changing preview mode controls without testing all device states could affect layout assumptions inside the iframe wrapper.

## Bottom line

`jcw_wp` does not contain a better old Visual Editor engine that should be copied back.

The current `jcw_construction_test` editor is the better base. The only meaningful things worth bringing forward from the old branch are:

- clearer always-visible usage guidance
- a less confusing preview mode toolbar

## Code changes

None in either WordPress branch.

Only this report was created:

- `tools/reports/visual-editor-old-vs-current-audit.md`
