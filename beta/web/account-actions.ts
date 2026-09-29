/** Expiring account links stay in memory; never persist them or send them as query strings. */
type Api = <T>(path: string, method?: string, body?: unknown) => Promise<T>;
function get<T extends HTMLElement = HTMLElement>(id: string): T {
  const value = document.getElementById(id);
  if (!value) throw new Error(`Missing account element: ${id}`);
  return value as T;
}

export function setupAccountActions(api: Api, signedOut: () => void): boolean {
  const fragment = new URLSearchParams(window.location.hash.slice(1));
  let token = fragment.get("token") ?? "";
  const action = fragment.get("action");
  const hasAction =
    (action === "reset" || action === "verify") &&
    /^[A-Za-z0-9_-]{43}$/.test(token);
  if (window.location.hash) history.replaceState(null, "", location.pathname);
  const dialog = get<HTMLDialogElement>("account-dialog");
  const title = get("account-action-title");
  const message = get("account-action-message");
  const input = get<HTMLInputElement>("account-action-input");
  const label = get("account-action-label");
  const button = get<HTMLButtonElement>("account-action-submit");
  let mode: "request" | "reset" | "verify" = "request";

  function open(next: typeof mode): void {
    mode = next;
    message.textContent = "";
    input.value = "";
    input.hidden = next === "verify";
    label.hidden = next === "verify";
    input.required = next !== "verify";
    input.type = next === "reset" ? "password" : "email";
    input.minLength = next === "reset" ? 12 : 3;
    input.maxLength = next === "reset" ? 128 : 254;
    input.autocomplete = next === "reset" ? "new-password" : "email";
    title.textContent =
      next === "verify" ? "Verify your email" : "Reset your password";
    label.textContent =
      next === "reset"
        ? "New password (12–128 characters)"
        : "Account email address";
    button.textContent =
      next === "verify"
        ? "Verify email"
        : next === "reset"
          ? "Update password"
          : "Request reset email";
    button.disabled = false;
    dialog.showModal();
  }
  get("forgot-password").addEventListener("click", () => open("request"));
  get("close-account-action").addEventListener("click", () => {
    token = "";
    dialog.close();
  });
  dialog.addEventListener("cancel", () => {
    token = "";
  });
  get<HTMLFormElement>("account-action-form").addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();
      button.disabled = true;
      try {
        const path =
          mode === "request"
            ? "recovery"
            : mode === "reset"
              ? "reset-password"
              : "verify-email";
        const body =
          mode === "request"
            ? { email: input.value }
            : { token, ...(mode === "reset" ? { password: input.value } : {}) };
        const result = await api<{ message: string }>(
          `/api/auth/${path}`,
          "POST",
          body,
        );
        input.value = "";
        message.textContent = result.message;
        if (mode === "reset") signedOut();
        if (mode !== "request") token = "";
      } catch (error) {
        message.textContent =
          error instanceof Error
            ? error.message
            : "Request failed. Please try again.";
        button.disabled = false;
      }
    },
  );
  get("verify-email").addEventListener("click", async () => {
    const button = get<HTMLButtonElement>("verify-email");
    button.disabled = true;
    try {
      const response = await api<{ message: string }>(
        "/api/auth/verification",
        "POST",
        {},
      );
      get("email-status").textContent = response.message;
    } catch (error) {
      get("email-status").textContent =
        error instanceof Error ? error.message : "Request failed.";
    } finally {
      button.disabled = false;
    }
  });
  if (hasAction) open(action === "reset" ? "reset" : "verify");
  return hasAction;
}
