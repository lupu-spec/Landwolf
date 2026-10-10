/** Keep app controls in the visible viewport without disabling pinch zoom. */
export function viewportInsets(
  layoutHeight: number,
  height: number,
  offsetTop: number,
  scale: number,
): { height: number; top: number; bottom: number } | null {
  if (
    ![layoutHeight, height, offsetTop, scale].every(Number.isFinite) ||
    layoutHeight <= 0 ||
    height <= 0 ||
    offsetTop < 0 ||
    Math.abs(scale - 1) > 0.05
  )
    return null;
  return {
    height,
    top: offsetTop,
    bottom: Math.max(0, layoutHeight - height - offsetTop),
  };
}

function editor(): HTMLElement | null {
  const active = document.activeElement;
  if (!(active instanceof HTMLElement)) return null;
  if (active instanceof HTMLTextAreaElement)
    return active.readOnly || active.disabled ? null : active;
  if (active instanceof HTMLInputElement)
    return !active.readOnly &&
      !active.disabled &&
      ["text", "search", "email", "password", "tel", "url", "number"].includes(
        active.type,
      )
      ? active
      : null;
  return active.isContentEditable ? active : null;
}

/** Blur only editable controls, preserving normal keyboard/button navigation. */
export function dismissMobileKeyboard(): void {
  editor()?.blur();
}

export function setupMobileKeyboard(): void {
  const root = document.documentElement;
  const mobile = matchMedia("(max-width: 1100px)");
  const touch = matchMedia("(any-pointer: coarse)");
  const dock = document.querySelector(".navigation-dock");
  const done = document.createElement("button");
  done.type = "button";
  done.className = "keyboard-done";
  done.textContent = "Done";
  done.setAttribute("aria-label", "Done editing — hide keyboard");
  done.addEventListener("click", dismissMobileKeyboard);
  dock?.append(done);
  const dialogDone = done.cloneNode(true) as HTMLButtonElement;
  dialogDone.addEventListener("click", dismissMobileKeyboard);
  document.querySelector(".detail-topbar")?.append(dialogDone);
  const floatingDone = done.cloneNode(true) as HTMLButtonElement;
  floatingDone.classList.add("keyboard-done-floating");
  floatingDone.addEventListener("click", dismissMobileKeyboard);
  document.body.append(floatingDone);

  let frame = 0;
  let revealEditor = false;
  function fit(): void {
    frame = 0;
    const reveal = revealEditor;
    revealEditor = false;
    const viewport = window.visualViewport;
    const bounds = viewportInsets(
      window.innerHeight,
      viewport?.height ?? window.innerHeight,
      viewport?.offsetTop ?? 0,
      viewport?.scale ?? 1,
    );
    root.dataset.mobileEditing = String(
      (mobile.matches || touch.matches) && Boolean(editor()),
    );
    root.dataset.viewportFit = String(Boolean(bounds));
    for (const [name, value] of [
      ["height", bounds?.height],
      ["top", bounds?.top],
      ["bottom", bounds?.bottom],
    ] as const) {
      const property = `--app-viewport-${name}`;
      if (value === undefined) root.style.removeProperty(property);
      else root.style.setProperty(property, `${value}px`);
    }
    const field = editor();
    root.dataset.researchEditing = String(
      Boolean(
        field?.closest(
          "#research-form, .decision-form, #hunt-form, #analysis-form",
        ),
      ),
    );
    const dialog = field?.closest<HTMLDialogElement>(".property-dialog[open]");
    if (
      reveal &&
      bounds &&
      dialog &&
      field &&
      (mobile.matches || touch.matches)
    ) {
      const box = field.getBoundingClientRect();
      const top = dialog
        .querySelector(".detail-topbar")
        ?.getBoundingClientRect().bottom;
      const bottom = dialog.getBoundingClientRect().bottom - 24;
      if (top !== undefined && box.top < top + 8)
        dialog.scrollTop += box.top - top - 8;
      else if (box.bottom > bottom) dialog.scrollTop += box.bottom - bottom;
    } else if (
      reveal &&
      bounds &&
      field?.closest("#research-form, .decision-form, #hunt-form") &&
      (mobile.matches || touch.matches)
    ) {
      const box = field.getBoundingClientRect();
      const top = bounds.top + 8;
      const bottom = bounds.top + bounds.height - 90;
      if (box.top < top)
        window.scrollBy({ top: box.top - top, behavior: "instant" });
      else if (box.bottom > bottom)
        window.scrollBy({ top: box.bottom - bottom, behavior: "instant" });
    }
  }
  function schedule(event: Event): void {
    // Follow an editor on focus/resize, never fight a user's deliberate scrolling.
    revealEditor ||= event.type === "focusin" || event.type === "resize";
    if (!frame) frame = requestAnimationFrame(fit);
  }
  document.addEventListener("focusin", schedule);
  document.addEventListener("focusout", schedule);
  window.addEventListener("resize", schedule, { passive: true });
  window.visualViewport?.addEventListener("resize", schedule, {
    passive: true,
  });
  window.visualViewport?.addEventListener("scroll", schedule, {
    passive: true,
  });
  mobile.addEventListener("change", schedule);
  touch.addEventListener("change", schedule);
  document.addEventListener("pointerdown", (event) => {
    // Do not shrink or move the tapped control between pointer down and click.
    if (
      root.dataset.mobileEditing === "true" &&
      editor() &&
      event.target instanceof Element &&
      event.target.closest("button, summary")
    )
      event.preventDefault();
  });
  // Navigation must release the editor before hiding or replacing its screen.
  document.addEventListener(
    "click",
    (event) => {
      if (
        event.target instanceof Element &&
        event.target.closest(
          "[data-nav], .property-actions button, #close-detail, #research-new",
        )
      )
        dismissMobileKeyboard();
    },
    true,
  );
  fit();
}
