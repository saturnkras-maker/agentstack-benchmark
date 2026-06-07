# Billing and payment v0.1

Vladimir authorized the billing/payment stage, but live checkout cannot be safely enabled from this environment because no payment provider configuration is present.

## Current status

- Free beta: active, no payment required.
- Paid hosted-verified track: reserved, not live.
- Live checkout: not connected.
- Provider secrets embedded in repository or site: no.

## Provider preflight checked

Environment presence was checked without printing values:

- `STRIPE_SECRET_KEY`: not present.
- `STRIPE_PUBLISHABLE_KEY`: not present.
- `STRIPE_PRICE_ID`: not present.
- `STRIPE_PAYMENT_LINK`: not present.
- `LEMONSQUEEZY_API_KEY`: not present.
- `PADDLE_API_KEY`: not present.
- `GITHUB_SPONSORS_URL`: not present.
- `AGENTSTACK_BILLING_URL`: not present.

## Required before live paid checkout

1. Choose merchant provider: Stripe, Paddle, Lemon Squeezy, GitHub Sponsors, or another provider.
2. Create product/price/payment link in the provider dashboard.
3. Configure provider public checkout URL or price ID outside the repository.
4. Configure webhook signature verification on a hosted backend before marking paid status as verified.
5. Add legal/refund/tax copy appropriate for the merchant account and jurisdiction.
6. Re-run secret scanning and payment-flow smoke tests.

## Safe public pricing state

The public launch page exposes only:

- `free-beta`: active, price `0`, no checkout.
- `hosted-verified`: reserved-not-live, provider required before activation.

This prevents fake billing success while still making the business model visible.
