import { renderTrial } from "./trial";
import {
  feedbackHeadline,
  feedbackViewAllowed,
  type FeedbackStatus,
} from "./feedback-policy";

type Api = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
type Answers = {
  usage: "used" | "not_used";
  last_attempted_task: string;
  blocker: string;
  feature_request: string;
  feature_reason: string;
  priority: "low" | "medium" | "high";
  value_rating: number | null;
  no_changes: boolean;
};
function node<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  text = "",
  className = "",
): HTMLElementTagNameMap[K] {
  const result = document.createElement(tag);
  result.textContent = text;
  result.className = className;
  return result;
}
function get(id: string): HTMLElement {
  const result = document.getElementById(id);
  if (!result) throw new Error(`Missing feedback element: ${id}`);
  return result;
}
const date = (value: number | null): string =>
  value === null
    ? "Not scheduled"
    : new Date(value * 1000).toLocaleDateString();
const message = (error: unknown): string =>
  error instanceof Error ? error.message : "Please try again.";
function button(label: string, action: () => void): HTMLButtonElement {
  const result = node("button", label, "button secondary small");
  result.type = "button";
  result.addEventListener("click", action);
  return result;
}

export function setupFeedback(
  api: Api,
  changed: (status: FeedbackStatus) => void,
) {
  let status: FeedbackStatus | null = null;
  let generation = 0;
  let running = false;
  let owner = false;
  let adminVerified = false;
  let download: AbortController | undefined;
  let refreshing = false;
  let rendered = "";
  let timer: ReturnType<typeof setInterval> | undefined;
  let adminSequence = 0;
  const content = get("feedback-content");
  const notice = get("feedback-notice");
  const noticeText = get("feedback-notice-text");
  const admin = get("feedback-admin");

  function clearAdmin(): void {
    adminVerified = false;
    adminSequence++;
    download?.abort();
    download = undefined;
    admin.replaceChildren();
    admin.hidden = true;
  }

  function renderNotice(current: FeedbackStatus): void {
    notice.hidden =
      current.state === "none" ||
      (current.state === "active" && !current.due_survey);
    noticeText.textContent = feedbackHeadline(current);
    if (current.due_survey)
      noticeText.textContent += ` · Due ${date(current.due_survey.due_at)}. Complete by ${date(current.due_survey.grace_until)} to avoid interrupted access.`;
  }

  function survey(current: FeedbackStatus, baseline: boolean): HTMLFormElement {
    const form = node("form", "", "feedback-form");
    const title = node(
      "h3",
      baseline
        ? "A short starting-point survey"
        : "Tell us about your experience",
    );
    form.append(
      title,
      node(
        "p",
        baseline
          ? "You do not need to have used LandWolf. Tell us what you hope to do and what would make it useful."
          : "Honest feedback is useful, including if you haven't used LandWolf. Please leave out sensitive financial or personal information.",
      ),
    );
    const label = (text: string, field: HTMLElement) => {
      const wrapper = node("label", text);
      wrapper.append(field);
      form.append(wrapper);
    };
    const select = (name: string, options: [string, string][]) => {
      const field = node("select");
      field.name = name;
      for (const [value, text] of options) {
        const option = node("option", text);
        option.value = value;
        field.append(option);
      }
      return field;
    };
    const usage = select("usage", [
      ["not_used", "I haven't used it yet"],
      ["used", "I have used LandWolf"],
    ]);
    label("Have you used LandWolf?", usage);
    const textField = (name: string, title: string, required = true) => {
      const field = node("textarea");
      field.name = name;
      field.rows = 3;
      field.maxLength = 1500;
      field.required = required;
      label(title, field);
      return field;
    };
    textField(
      "last_attempted_task",
      baseline
        ? "What do you want to accomplish with LandWolf?"
        : "What did you last try to do, or hope to do?",
    );
    textField("blocker", "What got in the way? If nothing, say so.");
    const noChanges = node("input");
    noChanges.type = "checkbox";
    noChanges.name = "no_changes";
    label("I have no change to suggest right now", noChanges);
    const feature = textField(
      "feature_request",
      "What one feature or improvement would help most?",
    );
    const reason = textField(
      "feature_reason",
      "Why would that improvement matter to you?",
    );
    const priority = select("priority", [
      ["medium", "Medium"],
      ["high", "High"],
      ["low", "Low"],
    ]);
    label("How important is that improvement?", priority);
    noChanges.addEventListener("change", () => {
      feature.required = reason.required = !noChanges.checked;
      feature.disabled =
        reason.disabled =
        priority.disabled =
          noChanges.checked;
    });
    const value = select("value_rating", [
      ["", "Not rated — I haven't used it"],
      ["1", "1 — Not useful"],
      ["2", "2"],
      ["3", "3"],
      ["4", "4"],
      ["5", "5 — Very useful"],
    ]);
    value.disabled = true;
    label("How useful has LandWolf been?", value);
    usage.addEventListener("change", () => {
      value.required = usage.value === "used";
      value.disabled = usage.value !== "used";
      if (usage.value !== "used") value.value = "";
    });
    const consent = node("input");
    consent.type = "checkbox";
    consent.name = "accepted_terms";
    consent.required = baseline;
    if (baseline)
      label(
        "I agree to three calendar months of pilot access from acceptance, with required feedback on days 14, 30, 60 and 85 and up to seven days to complete each check-in, ending sooner if the pilot expires. Access is paused if feedback is overdue and ends at expiry or owner revocation. No automatic charge or subscription starts. I understand reminders appear in LandWolf, not by email.",
        consent,
      );
    const result = node("p", "", "form-message");
    result.setAttribute("role", "status");
    result.setAttribute("aria-live", "polite");
    const submit = node(
      "button",
      baseline ? "Accept pilot & submit starting survey" : "Submit feedback",
      "button primary",
    );
    submit.type = "submit";
    form.append(result, submit);
    let saving = false;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (saving || !form.reportValidity()) return;
      const session = generation;
      const data = new FormData(form);
      const read = (key: string) => String(data.get(key) ?? "").trim();
      const answers: Answers = {
        usage: usage.value === "used" ? "used" : "not_used",
        last_attempted_task: read("last_attempted_task"),
        blocker: read("blocker"),
        feature_request: noChanges.checked ? "" : read("feature_request"),
        feature_reason: noChanges.checked ? "" : read("feature_reason"),
        priority:
          priority.value === "high"
            ? "high"
            : priority.value === "low"
              ? "low"
              : "medium",
        value_rating:
          usage.value === "used" && value.value ? Number(value.value) : null,
        no_changes: noChanges.checked,
      };
      if (
        !answers.last_attempted_task ||
        !answers.blocker ||
        (!answers.no_changes &&
          (!answers.feature_request || !answers.feature_reason))
      ) {
        result.textContent =
          "Please complete the questions with text, not just spaces.";
        return;
      }
      saving = true;
      submit.disabled = true;
      form.setAttribute("aria-busy", "true");
      result.textContent = "Saving your feedback…";
      try {
        await api(
          baseline ? "/api/feedback/accept" : "/api/feedback/responses",
          "POST",
          baseline
            ? {
                terms_version: current.terms_version,
                accepted_terms: consent.checked,
                baseline: answers,
              }
            : {
                survey_key: current.due_survey?.key,
                survey_version: current.survey_version,
                answers,
              },
        );
        if (session !== generation) return;
        rendered = "";
        await refresh();
        get("feedback-save-status").textContent =
          "Your feedback has been saved. Thank you. Access reflects your current pilot status.";
      } catch (error) {
        if (session === generation) result.textContent = message(error);
      } finally {
        saving = false;
        submit.disabled = false;
        form.setAttribute("aria-busy", "false");
      }
    });
    return form;
  }

  function render(current: FeedbackStatus): void {
    renderNotice(current);
    const signature = JSON.stringify(current);
    if (signature === rendered) return;
    rendered = signature;
    content.replaceChildren(node("h2", feedbackHeadline(current)));
    if (
      current.self_service_trial &&
      current.self_service_trial.state !== "none"
    ) {
      const trialGeneration = generation;
      renderTrial(
        content,
        current.self_service_trial,
        api,
        async () => {
          if (generation === trialGeneration) await refresh();
        },
        () => generation === trialGeneration,
      );
      return;
    }

    const saved = node("p");
    saved.id = "feedback-save-status";
    saved.setAttribute("role", "status");
    content.append(saved);
    if (current.state === "none")
      content.append(
        node(
          "p",
          current.pilot_reserved
            ? "Your marketing pilot is reserved for this email. Verify your email through the account controls or reply to your invitation so support can enroll your account. No payment is required."
            : "This invitation-only program helps us learn what property investors need. Contact support if you would like to participate.",
        ),
      );
    if (current.state === "invited") content.append(survey(current, true));
    if (current.accepted_at !== null)
      content.append(
        node(
          "p",
          `Accepted ${date(current.accepted_at)} · Pilot ends ${date(current.expires_at)}. No automatic charge.`,
        ),
      );
    if (current.state === "active" || current.state === "feedback_required") {
      content.append(
        node(
          "p",
          "Check-ins are due on days 14, 30, 60 and 85. Reminders appear here while you are signed in; no email reminders are sent.",
        ),
      );
      if (current.due_survey) {
        content.append(
          node(
            "p",
            `Check-in ${current.due_survey.key.replace("day", "day ")} · due ${date(current.due_survey.due_at)} · grace period ends ${date(current.due_survey.grace_until)}.`,
          ),
        );
        if (current.state === "feedback_required")
          content.append(
            node(
              "p",
              "Submit the required check-in to restore eligible pilot features. Your saved Hunts and account support remain available.",
            ),
          );
        content.append(survey(current, false));
      } else
        content.append(
          node(
            "p",
            current.next_due_at
              ? `Your next check-in is due ${date(current.next_due_at)}.`
              : "Your scheduled check-ins are complete.",
          ),
        );
      content.append(
        node(
          "p",
          `${current.completed_surveys.length} recorded survey submissions.`,
        ),
      );
    }
    if (current.state === "expired" || current.state === "revoked")
      content.append(
        node(
          "p",
          current.access_allowed
            ? "This invitation is no longer active. Your existing account access is unchanged. Contact support if you have questions."
            : "New property research is unavailable under this pilot. Your saved Hunts remain accessible. Contact support to discuss next steps; no paid subscription has been started.",
        ),
      );
    const support = node("a", "Contact LandWolf support");
    support.href = "mailto:support.landwolf@gmail.com";
    content.append(
      support,
      button("Refresh status", () => void refresh()),
    );
  }

  async function refresh(): Promise<void> {
    if (!running || refreshing) return;
    refreshing = true;
    const session = generation;
    try {
      const next = await api<FeedbackStatus>("/api/feedback");
      if (!running || session !== generation) return;
      status = next;
      adminVerified = owner && next.access_override === "owner";
      if (!adminVerified) clearAdmin();
      render(next);
      changed(next);
    } catch (error) {
      if (!running || session !== generation) return;
      clearAdmin();
      notice.hidden = false;
      noticeText.textContent = `Unable to refresh pilot status. ${message(error)}`;
      if (status === null)
        content.replaceChildren(
          node("p", message(error), "form-message"),
          button("Retry feedback status", () => void refresh()),
        );
    } finally {
      if (session === generation) refreshing = false;
    }
  }

  // Owner-only controls are rendered after the authenticated session identifies the owner.
  // The API remains responsible for authorization on every read and write.
  async function loadAdmin(): Promise<void> {
    if (!adminVerified) return;
    download?.abort();
    const session = generation;
    const sequence = ++adminSequence;
    const current = () =>
      adminVerified &&
      running &&
      generation === session &&
      sequence === adminSequence;
    admin.hidden = false;
    admin.replaceChildren(
      node("h2", "Manage investor feedback pilots"),
      node("p", "Loading accounts…"),
    );
    try {
      const [accounts, enrollments] = await Promise.all([
        api<{ accounts: { id: string; email: string; owner: boolean }[] }>(
          "/api/admin/accounts",
        ),
        api<{
          enrollments: (FeedbackStatus & {
            account_id: string;
            email: string;
          })[];
        }>("/api/admin/feedback"),
      ]);
      if (!current()) return;
      admin.replaceChildren(node("h2", "Manage investor feedback pilots"));
      admin.append(
        node(
          "p",
          "Invite an existing account to three calendar months of access in exchange for scheduled feedback. The user must accept the terms and starting survey. Invitations appear in their account; no email is sent.",
        ),
      );
      const result = node("p", "", "form-message");
      result.setAttribute("role", "status");
      const exportUsers = button("Export users CSV", () => {
        if (!current() || exportUsers.disabled) return;
        exportUsers.disabled = true;
        const controller = new AbortController();
        download = controller;
        const timeout = setTimeout(() => controller.abort(), 30000);
        result.textContent = "Preparing user export…";
        void (async () => {
          try {
            const response = await fetch("/api/admin/feedback/users.csv", {
              credentials: "same-origin",
              cache: "no-store",
              redirect: "error",
              headers: { Accept: "text/csv" },
              signal: controller.signal,
            });
            if (!current() || controller.signal.aborted) return;
            if (response.status === 401 || response.status === 403) {
              clearAdmin();
              notice.hidden = false;
              noticeText.textContent =
                "Owner authorization is required to view or export users.";
              return;
            }
            if (
              !response.ok ||
              !response.headers.get("Content-Type")?.startsWith("text/csv")
            )
              throw new Error(
                response.status === 409
                  ? "The export exceeds 10,000 accounts. No partial file was created."
                  : "Unable to export users. Please try again.",
              );
            const blob = await response.blob();
            if (!current() || controller.signal.aborted) return;
            const url = URL.createObjectURL(blob);
            const link = node("a");
            link.href = url;
            link.download = `landwolf-users-${new Date().toISOString().slice(0, 10)}.csv`;
            document.body.append(link);
            link.click();
            link.remove();
            // Allow browsers time to consume the blob before releasing it.
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            result.textContent =
              "CSV download started. Check your browser’s downloads.";
          } catch (error) {
            if (current())
              result.textContent = controller.signal.aborted
                ? "The export timed out. Please try again."
                : message(error);
          } finally {
            clearTimeout(timeout);
            if (download === controller) download = undefined;
            exportUsers.disabled = false;
          }
        })();
      });
      const wrap = node("div", "", "feedback-table-wrap");
      const table = node("table", "", "feedback-table");
      const caption = node(
        "caption",
        "Existing accounts and investor pilot invitations",
      );
      const head = node("thead");
      const header = node("tr");
      for (const label of ["Account", "Pilot status", "Ends", "Actions"]) {
        const cell = node("th", label);
        cell.scope = "col";
        header.append(cell);
      }
      head.append(header);
      const body = node("tbody");
      for (const account of accounts.accounts) {
        const enrollment = enrollments.enrollments.find(
          (row) => row.account_id === account.id,
        );
        const row = node("tr");
        const actions = node("td");
        const state = enrollment?.state ?? "none";
        row.append(
          node("td", account.email),
          node(
            "td",
            account.owner ? "Owner account" : state.replaceAll("_", " "),
          ),
          node("td", date(enrollment?.expires_at ?? null)),
          actions,
        );
        const mutate = async (control: HTMLButtonElement, revoke: boolean) => {
          if (
            revoke &&
            !window.confirm(
              `Revoke the feedback pilot for ${account.email}? Accepted pilot access will end immediately.`,
            )
          )
            return;
          control.disabled = true;
          result.textContent = revoke
            ? "Removing pilot access…"
            : "Creating invitation…";
          try {
            await api(
              `/api/admin/accounts/${encodeURIComponent(account.id)}/feedback-pilot`,
              revoke ? "DELETE" : "POST",
              {},
            );
            if (!current()) return;
            await loadAdmin();
          } catch (error) {
            if (current()) result.textContent = message(error);
          } finally {
            control.disabled = false;
          }
        };
        if (!account.owner && state === "none") {
          const invite = button(
            "Invite to feedback pilot",
            () => void mutate(invite, false),
          );
          actions.append(invite);
        }
        if (
          !account.owner &&
          ["invited", "active", "feedback_required"].includes(state)
        ) {
          const revoke = button(
            "Revoke pilot",
            () => void mutate(revoke, true),
          );
          actions.append(revoke);
        }
        if (account.owner)
          actions.append(node("span", "Owner access is managed separately."));
        if (state === "revoked" || state === "expired")
          actions.append(node("span", "Pilot ended."));
        body.append(row);
      }
      table.append(caption, head, body);
      wrap.append(table);
      const responses = node("div");
      const view = button("View submitted feedback", () => {
        view.disabled = true;
        responses.replaceChildren(node("p", "Loading submitted feedback…"));
        void (async () => {
          try {
            const report = await api<{
              responses: {
                account_id: string;
                email: string;
                survey_key: string;
                submitted_at: number;
                answers: Answers;
              }[];
            }>("/api/admin/feedback/responses");
            if (!current()) return;
            responses.replaceChildren(
              node("h3", "Submitted feedback"),
              node(
                "p",
                "Most recent submissions, up to 500. Feedback is shown as entered by participants.",
              ),
            );
            if (!report.responses.length)
              responses.append(
                node("p", "No feedback has been submitted yet."),
              );
            const fields: [keyof Answers, string][] = [
              ["usage", "Usage"],
              ["last_attempted_task", "Task"],
              ["blocker", "Blocker"],
              ["feature_request", "Requested improvement"],
              ["feature_reason", "Why it matters"],
              ["priority", "Priority"],
              ["value_rating", "Usefulness"],
              ["no_changes", "No changes requested"],
            ];
            for (const response of report.responses) {
              const card = node("details", "", "feedback-response");
              card.append(
                node(
                  "summary",
                  `${response.email} · ${response.survey_key} · ${date(response.submitted_at)}`,
                ),
              );
              const list = node("dl");
              for (const [key, label] of fields)
                list.append(
                  node("dt", label),
                  node(
                    "dd",
                    response.answers[key] === null
                      ? "Not rated"
                      : String(response.answers[key] ?? ""),
                  ),
                );
              card.append(list);
              responses.append(card);
            }
          } catch (error) {
            if (current())
              responses.replaceChildren(
                node("p", message(error), "form-message"),
              );
          } finally {
            view.disabled = false;
          }
        })();
      });
      admin.append(
        result,
        exportUsers,
        node(
          "p",
          "The CSV includes all registered users (up to 10,000), roles and pilot dates. The table shows up to 500 accounts. Downloads use your browser’s chosen folder.",
        ),
        wrap,
        view,
        button("Refresh accounts", () => void loadAdmin()),
        responses,
      );
    } catch (error) {
      if (current())
        admin.replaceChildren(
          node("h2", "Manage investor feedback pilots"),
          node("p", message(error), "form-message"),
          button("Retry account list", () => void loadAdmin()),
        );
    }
  }
  return {
    async start(isOwner: boolean): Promise<void> {
      this.clear();
      running = true;
      owner = isOwner;
      const session = generation;
      await refresh();
      if (!running || session !== generation) return;
      timer = setInterval(() => {
        if (document.visibilityState === "visible") void refresh();
      }, 60000);
    },
    clear(): void {
      generation++;
      running = false;
      owner = false;
      refreshing = false;
      status = null;
      rendered = "";
      clearInterval(timer);
      content.replaceChildren();

      clearAdmin();
      notice.hidden = true;
    },
    refresh,
    allowed(view: string): boolean {
      return feedbackViewAllowed(status, view);
    },
    async open(): Promise<void> {
      await refresh();
      if (owner) await loadAdmin();
    },
    get state(): FeedbackStatus | null {
      return status;
    },
  };
}
