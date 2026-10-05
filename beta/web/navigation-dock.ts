import { cycleOffset, dockScale } from "./dock-motion";

/** Enhance ordinary labeled buttons without owning routes or authorization. */
export function setupNavigationDock(): void {
  const foundShell = document.querySelector<HTMLElement>(".navigation-dock");
  const foundTrack = document.querySelector<HTMLElement>("#dock-track");
  if (!foundShell || !foundTrack) return;
  const shell = foundShell;
  const track = foundTrack;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const fine = matchMedia("(hover: hover) and (pointer: fine)");
  const items = [...track.querySelectorAll<HTMLButtonElement>("[data-dock]")];
  const arrows = [
    ...shell.querySelectorAll<HTMLButtonElement>("[data-dock-shift]"),
  ];
  const visible = () => items.filter((item) => !item.closest("[hidden]"));
  let frame = 0;
  let pointerX = 0;
  let wheelUntil = 0;
  let suppressClickUntil = 0;
  let drag:
    | { id: number; x: number; y: number; offset: number; moved: boolean }
    | undefined;
  const maximum = () => Math.max(0, track.scrollWidth - track.clientWidth);
  function resetScale(): void {
    cancelAnimationFrame(frame);
    frame = 0;
    for (const item of items) item.style.removeProperty("--dock-scale");
  }
  function shift(direction: number): void {
    resetScale();
    track.scrollTo({
      left: cycleOffset(track.scrollLeft, maximum(), direction),
      behavior: reduced.matches ? "instant" : "smooth",
    });
  }
  function sync(): void {
    const overflow = maximum() > 2;
    shell.dataset.overflow = String(overflow);
    for (const arrow of arrows) arrow.disabled = !overflow;
    resetScale();
  }
  for (const arrow of arrows)
    arrow.addEventListener("click", () =>
      shift(Number(arrow.dataset.dockShift)),
    );
  track.addEventListener("pointermove", (event) => {
    if (drag?.id === event.pointerId) {
      const dx = event.clientX - drag.x;
      const dy = event.clientY - drag.y;
      if (!drag.moved && Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 12) {
        drag = undefined;
        return;
      }
      if (Math.abs(dx) > 10 && !drag.moved) {
        drag.moved = true;
        track.setPointerCapture(event.pointerId);
        shell.dataset.dragging = "true";
        resetScale();
      }
      if (drag.moved) {
        track.scrollLeft = drag.offset - dx;
        return;
      }
    }
    if (!fine.matches || reduced.matches || event.pointerType !== "mouse")
      return;
    pointerX = event.clientX;
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      for (const item of visible()) {
        const box = item.getBoundingClientRect();
        item.style.setProperty(
          "--dock-scale",
          dockScale(pointerX - box.x - box.width / 2).toFixed(3),
        );
      }
    });
  });
  track.addEventListener("pointerleave", resetScale);
  track.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || maximum() <= 2) return;
    drag = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      offset: track.scrollLeft,
      moved: false,
    };
  });
  function finish(event: PointerEvent): void {
    if (!drag || drag.id !== event.pointerId) return;
    const active = drag;
    drag = undefined;
    delete shell.dataset.dragging;
    if (track.hasPointerCapture(event.pointerId))
      track.releasePointerCapture(event.pointerId);
    if (!active.moved) return;
    suppressClickUntil = performance.now() + 400;
    if (event.type === "pointercancel" || event.type === "lostpointercapture")
      return;
    const dx = event.clientX - active.x;
    if (
      Math.abs(dx) > 48 &&
      ((active.offset <= 2 && dx > 0) ||
        (active.offset >= maximum() - 2 && dx < 0))
    )
      shift(dx < 0 ? 1 : -1);
  }
  track.addEventListener("pointerup", finish);
  track.addEventListener("pointercancel", finish);
  track.addEventListener("lostpointercapture", finish);
  track.addEventListener(
    "click",
    (event) => {
      if (event.detail > 0 && performance.now() < suppressClickUntil) {
        suppressClickUntil = 0;
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    },
    true,
  );
  track.addEventListener(
    "wheel",
    (event) => {
      if (event.ctrlKey || maximum() <= 2) return;
      const delta =
        Math.abs(event.deltaX) > Math.abs(event.deltaY)
          ? event.deltaX
          : event.deltaY;
      if (!Number.isFinite(delta) || Math.abs(delta) < 2) return;
      event.preventDefault();
      if (performance.now() < wheelUntil) return;
      wheelUntil = performance.now() + 220;
      shift(Math.sign(delta));
    },
    { passive: false },
  );
  track.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const choices = visible();
    const index = choices.indexOf(document.activeElement as HTMLButtonElement);
    if (index < 0) return;
    let next: number;
    if (event.key === "ArrowRight") next = (index + 1) % choices.length;
    else if (event.key === "ArrowLeft")
      next = (index + choices.length - 1) % choices.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = choices.length - 1;
    else return;
    event.preventDefault();
    choices[next]?.focus({ preventScroll: true });
    reveal(choices[next]);
  });
  function reveal(item?: HTMLElement): void {
    if (!item) return;
    const box = item.getBoundingClientRect();
    const bounds = track.getBoundingClientRect();
    if (box.left < bounds.left + 8 || box.right > bounds.right - 8)
      track.scrollTo({
        left:
          track.scrollLeft +
          box.left -
          bounds.left -
          (bounds.width - box.width) / 2,
        behavior: "instant",
      });
  }
  track.addEventListener("focusin", (event) => {
    if (event.target instanceof HTMLElement)
      reveal(event.target.closest<HTMLElement>("[data-dock]") ?? undefined);
  });
  const observer = new MutationObserver(sync);
  observer.observe(track, {
    subtree: true,
    attributes: true,
    attributeFilter: ["hidden"],
  });
  new ResizeObserver(sync).observe(track);
  reduced.addEventListener("change", resetScale);
  sync();
}
