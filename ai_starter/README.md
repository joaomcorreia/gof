# AI Starter Future Structure

This app is a placeholder boundary for the future AI Starter product flow.

Keep the first implementation minimal:

1. Checkout success flow
   - Resolve the paid order.
   - Create the AI Starter order record if needed.
   - Send the customer into onboarding.

2. Onboarding form
   - Ask only for the small set of business details required to generate the first site.
   - Avoid building a large dashboard or settings area.

3. Generated site instance
   - Store one generated site record tied to the paid order.
   - Track only status, location, and generation metadata at first.

4. Token-based control panel
   - Use a simple signed or hashed token flow for the first version.
   - Avoid user accounts unless the product really needs them later.

Recommended first implementation shape:

- `ai_starter/models.py`
  Add `StarterOrder`, `StarterOnboarding`, `GeneratedSite`, and `ControlPanelToken`.
- `ai_starter/views.py`
  Add `checkout_success`, `onboarding`, and `panel`.
- `ai_starter/urls.py`
  Keep routes local to this app and mount them later under a focused path such as `/starter/`.
- `ai_starter/services.py`
  Add small service helpers only when external checkout verification or site generation actually exists.

Keep public marketing pages in `core`.
Keep product workflow code in `ai_starter`.
