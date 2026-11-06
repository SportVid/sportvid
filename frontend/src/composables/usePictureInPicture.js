import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from "vue";

const PIP_MIN_WIDTH = 240;
const PIP_MIN_HEIGHT = 135;
const PIP_MARGIN = 24;
const PIP_DRAG_THRESHOLD = 4; // px of pointer movement before a press counts as a drag, not a click

/**
 * Floating, draggable & resizable "picture-in-picture" panel for a card's
 * main visual (video, top-view pitch, ...). This only owns the panel's own
 * state (position/size, open/closed, drag & resize handling) -- the
 * component using it is responsible for:
 *  - actually teleporting its DOM into the panel via
 *    `<Teleport to="body" :disabled="!isPip">`, styled with `panelStyle`.
 *  - calling `open(rootEl, contentEl)` right before switching to PiP, and
 *    binding `lastCardContentHeight` as a fixed height on whatever
 *    placeholder replaces its content in the card -- so the card doesn't
 *    grow/shrink just because the content left it.
 *  - re-measuring its own content through `measure(el)` (on
 *    loadedmetadata/resize/fullscreenchange/etc, same as it already would
 *    without PiP) and writing the result to its own shared store *only*
 *    when not in PiP -- `measure()` keeps the PiP-local `contentSize` (read
 *    while floating instead) up to date on its own, so resizing the panel
 *    never leaks into layout state other cards read.
 *  - marking every one of its own clickable elements (list items, canvas,
 *    controls, ...) with a `pip-no-drag` class, so a press there always
 *    just clicks instead of also dragging the panel.
 *  - passing an `onResize` callback that re-measures its content -- called
 *    both after a resize-drag and once PiP is entered/exited.
 */
export function usePictureInPicture({ onResize } = {}) {
  const isPip = ref(false);
  const pipRect = reactive({ top: null, left: null, width: 400, height: 225 });
  const lastCardContentHeight = ref(0);
  const contentSize = ref({ width: 0, height: 0, top: 0, left: 0 });

  const panelStyle = computed(() => ({
    top: pipRect.top + "px",
    left: pipRect.left + "px",
    width: pipRect.width + "px",
    height: pipRect.height + "px",
  }));

  const clampToViewport = () => {
    if (pipRect.top === null) return;
    pipRect.width = Math.min(pipRect.width, window.innerWidth - PIP_MARGIN);
    pipRect.height = Math.min(pipRect.height, window.innerHeight - PIP_MARGIN);
    pipRect.left = Math.min(Math.max(0, pipRect.left), window.innerWidth - pipRect.width);
    pipRect.top = Math.min(Math.max(0, pipRect.top), window.innerHeight - pipRect.height);
  };

  // rootEl: the node that's actually teleported -- measured for the
  // placeholder's pinned height, since that's the exact box leaving the
  // card. contentEl: the element whose own aspect ratio should drive the
  // panel's *initial* size (defaults to rootEl; pass something more precise
  // -- e.g. a <video>, not its wrapper -- when the two can differ).
  const open = (rootEl, contentEl = rootEl) => {
    const rootRect = rootEl?.getBoundingClientRect();
    if (rootRect && rootRect.height > 0) {
      lastCardContentHeight.value = rootRect.height;
    }
    // Only pick an initial size/position the first time this panel is ever
    // opened -- a later open keeps wherever the user last dragged/resized
    // it to.
    if (pipRect.top === null) {
      const rect = contentEl?.getBoundingClientRect();
      const aspect = rect && rect.width > 0 && rect.height > 0 ? rect.width / rect.height : 16 / 9;
      pipRect.width = Math.min(400, rect?.width || 400) || 400;
      pipRect.height = pipRect.width / aspect;
      pipRect.top = window.innerHeight - pipRect.height - PIP_MARGIN;
      pipRect.left = window.innerWidth - pipRect.width - PIP_MARGIN;
    }
    clampToViewport();
    isPip.value = true;
  };
  const close = () => {
    isPip.value = false;
  };

  // Measures `el`'s current box. While in PiP this also updates the
  // PiP-local `contentSize` (so this component's own overlay/canvas keeps
  // following the floating panel's size); the caller still decides what to
  // do with the return value while docked (normally: write it to its own
  // store).
  const measure = (el) => {
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    const size = { width: rect.width, height: rect.height, top: rect.top, left: rect.left };
    if (isPip.value) {
      contentSize.value = size;
    }
    return size;
  };

  let drag = null;
  const onDragMove = (event) => {
    if (!drag) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moving) {
      // Stay a no-op until the pointer has actually moved -- lets a plain
      // click on a control/list-item/canvas-marker inside the panel fire
      // normally instead of being swallowed as a drag.
      if (Math.abs(dx) < PIP_DRAG_THRESHOLD && Math.abs(dy) < PIP_DRAG_THRESHOLD) return;
      drag.moving = true;
    }
    const maxLeft = Math.max(0, window.innerWidth - pipRect.width);
    const maxTop = Math.max(0, window.innerHeight - pipRect.height);
    pipRect.left = Math.min(Math.max(0, drag.startLeft + dx), maxLeft);
    pipRect.top = Math.min(Math.max(0, drag.startTop + dy), maxTop);
  };
  const onDragEnd = () => {
    drag = null;
    window.removeEventListener("pointermove", onDragMove);
    window.removeEventListener("pointerup", onDragEnd);
  };
  const onDragStart = (event) => {
    if (!isPip.value || event.button) return;
    // Anything clickable in its own right opts out of panel-dragging
    // entirely via the pip-no-drag class -- wherever the cursor turns into
    // a hand, a press there should only ever click, never also drag.
    if (event.target.closest?.(".pip-no-drag")) return;
    drag = {
      startX: event.clientX,
      startY: event.clientY,
      startLeft: pipRect.left,
      startTop: pipRect.top,
      moving: false,
    };
    window.addEventListener("pointermove", onDragMove);
    window.addEventListener("pointerup", onDragEnd);
  };

  // Corner-handle resize, locked to the panel's own aspect ratio -- dragging
  // diagonally scales width+height together, it never distorts the content.
  let resizeState = null;
  const onResizeMove = (event) => {
    if (!resizeState) return;
    const dx = event.clientX - resizeState.startX;
    const dy = event.clientY - resizeState.startY;
    const delta = (dx + dy) / 2;

    let newWidth = Math.max(PIP_MIN_WIDTH, resizeState.startWidth + delta);
    let newHeight = newWidth / resizeState.aspect;
    if (newHeight < PIP_MIN_HEIGHT) {
      newHeight = PIP_MIN_HEIGHT;
      newWidth = newHeight * resizeState.aspect;
    }

    const maxWidth = Math.max(PIP_MIN_WIDTH, window.innerWidth - pipRect.left);
    const maxHeight = Math.max(PIP_MIN_HEIGHT, window.innerHeight - pipRect.top);
    if (newWidth > maxWidth) {
      newWidth = maxWidth;
      newHeight = newWidth / resizeState.aspect;
    }
    if (newHeight > maxHeight) {
      newHeight = maxHeight;
      newWidth = newHeight * resizeState.aspect;
    }

    pipRect.width = newWidth;
    pipRect.height = newHeight;
    onResize?.();
  };
  const onResizeEnd = () => {
    resizeState = null;
    window.removeEventListener("pointermove", onResizeMove);
    window.removeEventListener("pointerup", onResizeEnd);
  };
  const onResizeStart = (event) => {
    event.stopPropagation();
    resizeState = {
      startX: event.clientX,
      startY: event.clientY,
      startWidth: pipRect.width,
      startHeight: pipRect.height,
      aspect: pipRect.width / pipRect.height,
    };
    window.addEventListener("pointermove", onResizeMove);
    window.addEventListener("pointerup", onResizeEnd);
  };

  watch(isPip, async () => {
    await nextTick();
    onResize?.();
  });

  onMounted(() => {
    window.addEventListener("resize", clampToViewport);
  });
  onBeforeUnmount(() => {
    window.removeEventListener("resize", clampToViewport);
    window.removeEventListener("pointermove", onDragMove);
    window.removeEventListener("pointerup", onDragEnd);
    window.removeEventListener("pointermove", onResizeMove);
    window.removeEventListener("pointerup", onResizeEnd);
  });

  return {
    isPip,
    lastCardContentHeight,
    contentSize,
    panelStyle,
    open,
    close,
    measure,
    onDragStart,
    onResizeStart,
  };
}
