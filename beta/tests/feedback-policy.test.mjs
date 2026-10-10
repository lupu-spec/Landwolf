import test from "node:test";
import assert from "node:assert/strict";
import {
  feedbackViewAllowed,
  feedbackHeadline,
} from "../web/feedback-policy.ts";

test("server denial blocks features but preserves feedback and personal Hunts", () => {
  for (const state of ["feedback_required", "expired", "revoked"]) {
    const status = { state, access_allowed: false, due_survey: null };
    assert.equal(feedbackViewAllowed(status, "explore"), false);
    assert.equal(feedbackViewAllowed(status, "research"), false);
    assert.equal(feedbackViewAllowed(status, "feedback"), true);
    assert.equal(feedbackViewAllowed(status, "hunt"), true);
    assert.equal(typeof feedbackHeadline(status), "string");
  }
  assert.equal(feedbackViewAllowed(null, "explore"), false);
  assert.equal(feedbackViewAllowed(null, "feedback"), true);
});

test("UI follows server entitlement including owner overrides", () => {
  assert.equal(
    feedbackViewAllowed({ state: "expired", access_allowed: true }, "explore"),
    true,
  );
  assert.equal(
    feedbackHeadline({ state: "active", due_survey: { key: "day14" } }),
    "Your next feedback check-in is ready",
  );
});
