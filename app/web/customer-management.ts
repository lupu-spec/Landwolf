/** Owner tools for publishing a customer-safe update and preparing a reviewed handoff. */
import type { Api } from "./crm";
import { element } from "./dom";

type Project = {
  customer_id: string;
  services: { id: string; service: string; status: string; revision: number }[];
  messages: { author: string; text: string }[];
};
export function customerManagement(
  api: Api,
  requestId: string,
  isActive: () => boolean,
): HTMLElement {
  const section = element("details");
  section.append(element("summary", "", "CUSTOMER WORKSPACE"));
  const content = element("div", "customer-management");
  section.append(content);
  let ticket = 0;
  const live = (stamp: number) => isActive() && stamp === ticket;
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
        if (work.service === "software" && work.status === "approved") {
          const handoff = element("button", "button", "PREPARE FACTORY BRIEF");
          handoff.type = "button";
          handoff.addEventListener("click", async () => {
            handoff.disabled = true;
            try {
              const brief = await api<{
                title: string;
                goal: string;
                work_item_id: string;
              }>("/api/admin/portal/work/" + work.id + "/handoff", "POST", {});
              if (!live(stamp)) return;
              const review = element("label", "", "REVIEW BEFORE RUNNING");
              const text = element("textarea");
              text.readOnly = true;
              text.rows = 7;
              text.value =
                brief.title +
                "\n\n" +
                brief.goal +
                "\n\nWork reference: " +
                brief.work_item_id;
              review.append(text);
              const open = element("a", "button", "OPEN L91 FACTORY");
              open.href = "https://l91.landwolf.ai/";
              open.target = "_blank";
              open.rel = "noopener noreferrer";
              wrap.append(
                review,
                open,
                element(
                  "p",
                  "muted",
                  "Copy the reviewed brief into a new L91 task. Preparing it does not run code.",
                ),
              );
            } catch (e) {
              if (live(stamp))
                status.textContent =
                  e instanceof Error ? e.message : "Unable to prepare brief.";
            } finally {
              handoff.disabled = false;
            }
          });
          wrap.append(handoff);
        }
        content.append(wrap);
      }
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
      const status = element("p");
      status.setAttribute("role", "status");
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
  }
  section.addEventListener("toggle", () => {
    if (section.open) void load();
    else ticket++;
  });
  return section;
}
