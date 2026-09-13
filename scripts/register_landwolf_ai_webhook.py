#!/usr/bin/env python3
import os
import stripe

EVENTS = [
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
    "invoice.paid",
]

def main():
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key.startswith("sk_test_"):
        raise SystemExit("Set the LandWolf sandbox STRIPE_SECRET_KEY (sk_test_...).")
    stripe.api_key = key

    endpoint = stripe.WebhookEndpoint.create(
        url="https://landwolf.ai/api/billing/webhook",
        enabled_events=EVENTS,
        description="LandWolf sandbox subscription access",
        metadata={"app": "landwolf", "environment": "sandbox", "domain": "landwolf.ai"},
    )

    print(f"STRIPE_WEBHOOK_ENDPOINT_ID={endpoint.id}")
    print(f"STRIPE_WEBHOOK_SECRET={endpoint.secret}")

if __name__ == "__main__":
    main()
