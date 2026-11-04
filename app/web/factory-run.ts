/** Owner-only approval and result display. All transport credentials stay on the server. */
import type { Api } from "./crm";
import { element } from "./dom";
type Work = { id: string; status: string; revision: number };
type Dispatch = {
  id: string;
  state: string;
  title: string;
  goal: string;
  runtime: string;
  project_key: string;
  acceptance: string;
  message?: string;
  task_id?: string;
  result?: { report: unknown; patch: string } | null;
};
type Runner = {
  name: string;
  connected: boolean;
  ready: boolean;
  projects: { id: string; name: string; runtimes: string[]; checks: string }[];
};
export function factoryRun(
  api: Api,
  work: Work,
  isActive: () => boolean,
): HTMLElement {
  const panel = element("details");
  panel.dataset.workStatus = work.status;
  panel.append(element("summary", "", "FACTORY RUN"));
  const content = element("div", "customer-management");
  panel.append(content);
  let generation = 0;
  let poll: ReturnType<typeof setTimeout> | undefined;
  const endpoint = "/api/admin/portal/work/" + work.id + "/factory";
  function button(
    label: string,
    action: () => Promise<void>,
  ): HTMLButtonElement {
    const b = element("button", "button", label);
    b.type = "button";
    b.addEventListener("click", async () => {
      b.disabled = true;
      try {
        await action();
      } catch (e) {
        if (isActive())
          message.textContent =
            e instanceof Error ? e.message : "Factory unavailable.";
      } finally {
        b.disabled = false;
      }
    });
    return b;
  }
  const message = element("p");
  message.setAttribute("role", "status");
  async function load() {
    clearTimeout(poll);
    const stamp = ++generation;
    const current = () => isActive() && stamp === generation && panel.open;
    content.replaceChildren(element("p", "", "LOADING…"));
    const { dispatch } = await api<{ dispatch: Dispatch | null }>(endpoint);
    if (!current()) return;
    content.replaceChildren(message, button("REFRESH RUN", load));
    message.textContent = dispatch
      ? dispatch.state.toUpperCase() + " · " + (dispatch.message || "")
      : "NO RUN YET";
    if (dispatch) {
      content.append(element("p", "muted", "REQUEST · " + dispatch.id));
      if (dispatch.task_id)
        content.append(
          element("p", "muted", "FACTORY TASK · " + dispatch.task_id),
        );
      if (["queued", "running"].includes(dispatch.state)) {
        content.append(
          button("CANCEL RUN", async () => {
            await api(endpoint + "/cancel", "POST", {});
            if (current()) await load();
          }),
        );
      }
      if (dispatch.result) {
        content.append(element("h4", "", "RESULT FOR OWNER REVIEW"));
        const report = element("pre", "preserve-lines");
        report.textContent = JSON.stringify(dispatch.result.report, null, 2);
        const label = element("label", "", "PROPOSED CODE");
        const patch = element("textarea");
        patch.readOnly = true;
        patch.rows = 12;
        patch.value = dispatch.result.patch;
        label.append(patch);
        content.append(report, label);
      }
      const open = element("a", "button", "OPEN FACTORY");
      open.href = "https://l91.landwolf.ai/";
      open.target = "_blank";
      open.rel = "noopener noreferrer";
      content.append(
        open,
        element(
          "p",
          "muted",
          "RESULTS STAY PRIVATE UNTIL YOU PUBLISH AN UPDATE. CODE IS NOT APPLIED OR DEPLOYED.",
        ),
      );
      if (["queued", "running"].includes(dispatch.state)) {
        content.append(
          element(
            "p",
            "muted",
            "UPDATES EVERY 5 SECONDS WHILE THIS PANEL IS OPEN.",
          ),
        );
        poll = setTimeout(() => {
          if (current() && document.visibilityState === "visible")
            void load().catch(() => {
              if (isActive() && panel.open)
                message.textContent = "STATUS UNAVAILABLE. REFRESH TO RETRY.";
            });
        }, 5000);
      }
      if (dispatch.state !== "pending") return;
    }
    if (work.status !== "approved") {
      content.append(
        element("p", "muted", "SET SOFTWARE WORK TO APPROVED BEFORE RUNNING."),
      );
      return;
    }
    const brief =
      dispatch ||
      (await api<{ title: string; goal: string }>(
        "/api/admin/portal/work/" + work.id + "/handoff",
        "POST",
        {},
      ));
    const { runners } = await api<{ runners: Runner[] }>(
      "/api/admin/portal/factory/targets",
    );
    if (!current()) return;
    const runner = runners[0];
    if (!runner) {
      message.textContent = "NO CONNECTED RUNNER";
      return;
    }
    content.append(
      element("h4", "", brief.title),
      element("p", "preserve-lines", brief.goal),
      element(
        "p",
        "muted",
        runner.name +
          (runner.connected && runner.ready
            ? " · READY"
            : " · OFFLINE — REQUESTS WAIT IN QUEUE"),
      ),
    );
    const form = element("form");
    const targetLabel = element("label", "", "PROJECT / RUNTIME");
    const target = element("select");
    target.required = true;
    for (const project of runner.projects)
      for (const runtime of project.runtimes) {
        const option = element(
          "option",
          "",
          project.name +
            " / " +
            runtime.toUpperCase() +
            " / " +
            project.checks.toUpperCase(),
        );
        option.value = project.id + ":" + runtime;
        target.append(option);
      }
    if (dispatch) {
      target.value = dispatch.project_key + ":" + dispatch.runtime;
      target.disabled = true;
    }
    targetLabel.append(target);
    const acceptanceLabel = element("label", "", "ACCEPTANCE REQUIREMENTS");
    const acceptance = element("textarea");
    acceptance.maxLength = 4000;
    acceptance.rows = 4;
    acceptance.value = dispatch?.acceptance || "";
    acceptance.readOnly = !!dispatch;
    acceptanceLabel.append(acceptance);
    const confirmLabel = element("label");
    const confirm = element("input");
    confirm.type = "checkbox";
    confirm.required = true;
    confirmLabel.append(
      confirm,
      document.createTextNode(
        " I REVIEWED THIS REQUEST AND APPROVE RUNNING IT ON MY MACHINE.",
      ),
    );
    const run = element(
      "button",
      "button",
      dispatch ? "RETRY SAME REQUEST" : "RUN REQUEST",
    );
    run.type = "submit";
    form.append(
      targetLabel,
      acceptanceLabel,
      confirmLabel,
      element(
        "p",
        "muted",
        "CODE RUNS IN A TEMPORARY SANDBOX. NEW PROJECTS RECEIVE SYNTAX CHECKS, NOT FUNCTIONAL ACCEPTANCE.",
      ),
      run,
    );
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!form.reportValidity()) return;
      run.disabled = true;
      try {
        const [project_key, runtime] = target.value.split(":");
        await api(endpoint, "POST", {
          revision: work.revision,
          project_key,
          runtime,
          acceptance: acceptance.value,
          confirmed: confirm.checked,
        });
        if (current()) await load();
      } catch (e) {
        if (current()) {
          message.textContent =
            e instanceof Error
              ? e.message
              : "Request not confirmed. Refresh before retrying.";
        }
      } finally {
        run.disabled = false;
      }
    });
    content.append(form);
  }
  panel.addEventListener("toggle", () => {
    if (!panel.open) {
      clearTimeout(poll);
      generation++;
      return;
    }
    void load().catch((e) => {
      if (isActive()) {
        content.replaceChildren(message, button("REFRESH RUN", load));
        message.textContent =
          e instanceof Error ? e.message : "Factory unavailable.";
      }
    });
  });
  return panel;
}
