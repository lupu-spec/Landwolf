import { releaseCards, type Delivery } from "./releases";
/** Owner tools for publishing a customer-safe update and preparing a reviewed handoff. */
import type { Api } from "./crm";
import { element } from "./dom";
import { factoryRun } from "./factory-run";

type Project = {
  releases?: Delivery[];
  customer_id: string;
  access_pending?: boolean;
  services: { id: string; service: string; status: string; revision: number }[];
  messages: { author: string; text: string }[];
};
export function customerManagement(
  api: Api,
  requestId: string,
  revision: number,
  isActive: () => boolean,
): HTMLElement {
  const section = element("details");
  section.append(element("summary", "", "CUSTOMER WORKSPACE"));
  const content = element("div", "customer-management");
  section.append(content);
  let ticket = 0;
  const live = (stamp: number) => isActive() && stamp === ticket;
  function prepareForm(stamp: number): HTMLElement {
    const form = element("form");
    const label = element("label", "", "WORK SERVICE");
    const service = element("select");
    service.setAttribute("aria-label", "WORK SERVICE");
    for (const value of ["software", "studio", "fabrication", "supply"]) {
      const option = element("option", "", value.toUpperCase());
      option.value = value;
      service.append(option);
    }
    label.append(service);
    const submit = element("button", "button", "PREPARE WORK");
    submit.type = "submit";
    const result = element("p");
    result.setAttribute("role", "status");
    form.append(
      label,
      element(
        "p",
        "muted",
        "PREPARE A SERVICE FOR REVIEW. THIS DOES NOT RUN CODE OR GRANT CUSTOMER ACCESS.",
      ),
      submit,
      result,
    );
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      submit.disabled = true;
      try {
        await api(
          "/api/admin/portal/projects/" + requestId + "/prepare",
          "POST",
          { revision, service: service.value, confirmed: true },
        );
        if (live(stamp)) await load();
      } catch (e) {
        if (live(stamp))
          result.textContent =
            e instanceof Error ? e.message : "Unable to prepare work.";
      } finally {
        submit.disabled = false;
      }
    });
    return form;
  }
  async function linkForm(stamp: number) {
    try {
      const catalog = await api<{
        customers: { id: string; name: string; email: string }[];
      }>("/api/admin/portal/catalog");
      if (!live(stamp)) return;
      const form = element("form");
      const label = element("label", "", "CUSTOMER ACCOUNT");
      const select = element("select");
      select.required = true;
      const empty = element("option", "", "SELECT A VERIFIED CUSTOMER");
      empty.value = "";
      select.append(empty);
      for (const c of catalog.customers) {
        const o = element(
          "option",
          "",
          c.name + " · " + c.email + " · " + c.id.slice(0, 8),
        );
        o.value = c.id;
        select.append(o);
      }
      label.append(select);
      const consent = element("label", "");
      const check = element("input");
      check.type = "checkbox";
      check.required = true;
      consent.append(
        check,
        document.createTextNode(
          " I verified this account belongs to the customer who submitted this project.",
        ),
      );
      const link = element("button", "button", "LINK CUSTOMER");
      link.type = "submit";
      const status = element("p");
      status.setAttribute("role", "status");
      form.append(label, consent, link, status);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        link.disabled = true;
        try {
          await api(
            "/api/admin/portal/projects/" + requestId + "/link",
            "POST",
            { customer_id: select.value, identity_confirmed: check.checked },
          );
          if (live(stamp)) await load();
        } catch (e) {
          if (live(stamp))
            status.textContent =
              e instanceof Error ? e.message : "Unable to link.";
        } finally {
          link.disabled = false;
        }
      });
      content.append(form);
    } catch (e) {
      if (live(stamp))
        content.append(
          element(
            "p",
            "",
            e instanceof Error ? e.message : "Unable to load customers.",
          ),
        );
    }
  }
  async function load() {
    const stamp = ++ticket;
    content.replaceChildren(element("p", "", "LOADING…"));
    try {
      const project = await api<Project>(
        "/api/admin/portal/projects/" + requestId,
      );
      if (!live(stamp)) return;
      content.replaceChildren(
        element("p", "muted", "CUSTOMER · " + project.customer_id),
      );
      content.append(releaseCards(project.releases || [], true));
      const status = element("p");
      status.setAttribute("role", "status");
      for (const work of project.services) {
        const wrap = element("div", "crm-actions");
        const label = element("label", "", work.service.toUpperCase());
        const input = element("select");
        input.setAttribute("aria-label", work.service.toUpperCase());
        for (const state of [
          "received",
          "reviewing",
          "quoted",
          "approved",
          "in_progress",
          "delivered",
          "closed",
        ]) {
          const option = element(
            "option",
            "",
            state.replaceAll("_", " ").toUpperCase(),
          );
          option.value = state;
          input.append(option);
        }
        input.value = work.status;
        label.append(input);
        const save = element("button", "button", "SAVE WORK STATUS");
        save.type = "button";
        save.addEventListener("click", async () => {
          save.disabled = true;
          try {
            await api("/api/admin/portal/work/" + work.id, "PATCH", {
              revision: work.revision,
              status: input.value,
            });
            if (live(stamp)) await load();
          } catch (e) {
            if (live(stamp))
              status.textContent =
                e instanceof Error ? e.message : "Unable to save.";
          } finally {
            save.disabled = false;
          }
        });
        wrap.append(label, save);
        if (work.service === "software") {
          wrap.append(factoryRun(api, work, () => live(stamp)));
        }
        content.append(wrap);
      }
      content.append(prepareForm(stamp));
      if (project.access_pending) await linkForm(stamp);
      content.append(element("h3", "", "CUSTOMER UPDATES"));
      for (const message of project.messages)
        content.append(
          element("p", "", message.author.toUpperCase() + ": " + message.text),
        );
      const form = element("form");
      const label = element("label", "", "PUBLISH TO CUSTOMER");
      const text = element("textarea");
      text.required = true;
      text.maxLength = 2000;
      label.append(text);
      const publish = element("button", "button", "PUBLISH UPDATE");
      publish.type = "submit";

      const messageId = crypto.randomUUID();
      form.append(label, publish, status);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        publish.disabled = true;
        try {
          await api(
            "/api/admin/portal/projects/" + requestId + "/messages",
            "POST",
            { submission_id: messageId, text: text.value.trim() },
          );
          if (live(stamp)) await load();
        } catch (e) {
          if (live(stamp))
            status.textContent =
              e instanceof Error ? e.message : "Unable to publish.";
        } finally {
          publish.disabled = false;
        }
      });
      content.append(form);
    } catch (e) {
      if (!live(stamp)) return;
      content.replaceChildren(
        element(
          "p",
          "",
          e instanceof Error ? e.message : "Unable to load workspace.",
        ),
      );
      if (
        !(e instanceof Error) ||
        e.message !== "Project has no customer workspace"
      )
        return;
      content.append(prepareForm(stamp));
      await linkForm(stamp);
    }
  }
  section.addEventListener("toggle", () => {
    if (section.open) void load();
    else ticket++;
  });
  return section;
}
