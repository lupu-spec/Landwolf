/** Keep focused content clear of the app's floating mobile controls. */
export function setupFocusVisibility(): void {
  document.addEventListener("focusin", (event) => {
    const target = event.target;
    if (
      !(target instanceof HTMLElement) ||
      !target.closest("main, footer, dialog")
    )
      return;
    const bounds = target.getBoundingClientRect();
    const x = Math.max(
      0,
      Math.min(innerWidth - 1, bounds.left + bounds.width / 2),
    );
    const y = Math.max(
      0,
      Math.min(innerHeight - 1, bounds.top + bounds.height / 2),
    );
    const covering = document.elementFromPoint(x, y);
    if (
      covering &&
      !target.contains(covering) &&
      covering.closest(".navigation-dock, .wolf-launcher, .site-header")
    ) {
      target.scrollIntoView({
        block: "center",
        inline: "nearest",
        behavior: "instant",
      });
    }
  });
}
