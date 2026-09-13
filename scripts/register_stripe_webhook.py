#!/usr/bin/env python3
import os
import sys
from urllib.parse import urlparse
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
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/register_stripe_webhook.py https://your-host.example.com")
    base_url = sys.argv[1].rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("A public HTTPS base URL is required.")

    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key.startswith("sk_test_"):
        raise SystemExit("Use the LandWolf sandbox test secret key (sk_test_...).")

    stripe.api_key = key
    endpoint = stripe.WebhookEndpoint.create(
        url=f"{base_url}/api/billing/webhook",
        enabled_events=EVENTS,
        description="LandWolf sandbox subscription access",
        metadata={"app": "landwolf", "environment": "sandbox"},
    )
    print(f"STRIPE_WEBHOOK_ENDPOINT_ID={endpoint.id}")
    print(f"STRIPE_WEBHOOK_SECRET={endpoint.secret}")

if __name__ == "__main__":
    main()
