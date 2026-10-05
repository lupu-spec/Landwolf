/** Display decisions follow the server's entitlement response, never local dates. */
export type FeedbackState =
  "none" | "invited" | "active" | "feedback_required" | "expired" | "revoked";
export type FeedbackStatus = {
  state: FeedbackState;
  enrolled: boolean;
  pilot_reserved?: boolean;
  accepted_at: number | null;
  expires_at: number | null;
  terms_version: string;
  survey_version: number;
  due_survey: {
    key: string;
    due_at: number;
    grace_until: number;
  } | null;
  next_due_at: number | null;
  completed_surveys: string[];
  access_allowed: boolean;
  access_override?: "owner" | "complimentary" | null;
};
export function feedbackViewAllowed(
  status: FeedbackStatus | null,
  view: string,
): boolean {
  return (
    view === "feedback" ||
    view === "billing" ||
    view === "hunt" ||
    (status !== null && status.access_allowed)
  );
}
export function feedbackHeadline(status: FeedbackStatus): string {
  switch (status.state) {
    case "none":
      return "Investor feedback program";
    case "invited":
      return "You're invited to help shape LandWolf";
    case "feedback_required":
      return "Your feedback is overdue";
    case "expired":
      return "Your three-month feedback pilot has ended";
    case "revoked":
      return "Your feedback pilot access has been removed";
    case "active":
      return status.due_survey
        ? "Your next feedback check-in is ready"
        : "Thank you for helping improve LandWolf";
  }
}
