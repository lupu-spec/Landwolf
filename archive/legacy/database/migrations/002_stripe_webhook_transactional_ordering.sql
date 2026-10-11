BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS last_stripe_event_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS last_stripe_event_type VARCHAR(120),
    ADD COLUMN IF NOT EXISTS last_stripe_event_created BIGINT;

CREATE INDEX IF NOT EXISTS ix_users_stripe_subscription_id
    ON users (stripe_subscription_id);

ALTER TABLE subscription_events
    ADD COLUMN IF NOT EXISTS stripe_created BIGINT,
    ADD COLUMN IF NOT EXISTS customer_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS subscription_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS processing_result VARCHAR(50) NOT NULL DEFAULT 'applied',
    ADD COLUMN IF NOT EXISTS processed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Existing rows predate Stripe timestamp persistence; retain them but make
-- future writes require an explicit timestamp after backfill.
UPDATE subscription_events
SET stripe_created = COALESCE(
    stripe_created,
    EXTRACT(EPOCH FROM created_at)::BIGINT
)
WHERE stripe_created IS NULL;

ALTER TABLE subscription_events
    ALTER COLUMN stripe_created SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_subscription_events_stripe_created
    ON subscription_events (stripe_created);
CREATE INDEX IF NOT EXISTS ix_subscription_events_customer_id
    ON subscription_events (customer_id);
CREATE INDEX IF NOT EXISTS ix_subscription_events_subscription_id
    ON subscription_events (subscription_id);

COMMIT;
