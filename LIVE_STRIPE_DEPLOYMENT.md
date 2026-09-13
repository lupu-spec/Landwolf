# LandWolf live Stripe deployment

1. Connect/access the live LandWolf Stripe account.
2. Live recurring prices are connected:
   - $29 USD / month — `price_1UF0wdPhxY7l1SSNacgAt3xi`
   - $299 USD / year — `price_1UF0wcPhxY7l1SSNtwo6diAI`
   - Product — `prod_VFVepZMgPE2lMH`
3. Copy `.env.live.example` values into the production host's environment variables.
4. Deploy LandWolf to `https://landwolf.ai`.
5. Run:
   `STRIPE_SECRET_KEY=sk_live_... python scripts/register_landwolf_ai_live_webhook.py`
6. Save the returned `whsec_...` as `STRIPE_WEBHOOK_SECRET`.
7. Restart the app.
8. Complete a real low-risk purchase and verify:
   - Checkout succeeds
   - subscription becomes `active`
   - detailed property access unlocks
   - cancellation/revocation removes access

Never commit `sk_live_...` or `whsec_...` values to Git.
