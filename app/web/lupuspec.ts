/** Public, same-origin LupuSpec concept intake. No browser credential storage. */
type FormFields = HTMLInputElement | HTMLTextAreaElement;
const form = document.querySelector<HTMLFormElement>("#concept-form");
const status = document.querySelector<HTMLParagraphElement>("#submission-status");
const submit = document.querySelector<HTMLButtonElement>("#submit-request");

if (form && status && submit) {
  let submissionId = crypto.randomUUID();
  const field = (name: string): string => {
    const control = form.elements.namedItem(name) as FormFields | null;
    if (!control) throw new Error("Missing required form field");
    return control.value.trim();
  };
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submit.disabled = true;
    status.textContent = "Submitting project request…";
    try {
      const capability = form.querySelector<HTMLInputElement>(
        'input[name="capability"]:checked',
      )?.value;
      const permission = form.querySelector<HTMLInputElement>(
        'input[name="contact_permission"]',
      )?.checked;
      const quantity = Number(field("quantity"));
      if (!capability || !permission || !Number.isSafeInteger(quantity))
        throw new Error("Complete all required fields");
      const response = await fetch("/api/lupuspec/requests", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          submission_id: submissionId,
          capability,
          title: field("title"),
          text: field("text"),
          quantity,
          reference_url: field("reference_url"),
          full_name: field("full_name"),
          email: field("email"),
          company: field("company"),
          phone: field("phone"),
          contact_permission: permission,
        }),
      });
      if (!response.ok) {
        const payload: unknown = await response.json().catch(() => null);
        const detail =
          payload && typeof payload === "object" && "detail" in payload
            ? String(payload.detail)
            : "Request could not be submitted.";
        throw new Error(detail);
      }
      const payload = (await response.json()) as { request_id: string };
      status.textContent =
        "Request received. Reference: " +
        payload.request_id +
        ". LupuSpec will review the requirements before any quote or work order.";
      form.reset();
      submissionId = crypto.randomUUID();
    } catch (error) {
      status.textContent =
        error instanceof Error
          ? error.message
          : "Request could not be submitted.";
    } finally {
      submit.disabled = false;
    }
  });
}
