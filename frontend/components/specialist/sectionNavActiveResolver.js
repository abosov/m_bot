/**
 * @typedef {{ id: string; top: number }} SectionGeometry
 */

/**
 * Resolve active section by real section geometry and current scroll position.
 * The section list must be in visual order.
 *
 * @param {SectionGeometry[]} sections
 * @param {{ scrollY: number; viewportHeight: number; documentHeight: number; stickyOffset: number; bottomThreshold?: number }} options
 * @returns {string | null}
 */
export function resolveActiveSectionId(sections, options) {
  if (!sections.length) {
    return null;
  }

  const bottomThreshold = options.bottomThreshold ?? 24;
  const switchThreshold = options.switchThreshold ?? 8;
  const reachedBottom = options.scrollY + options.viewportHeight >= options.documentHeight - bottomThreshold;
  if (reachedBottom) {
    return sections[sections.length - 1].id;
  }

  const probeY = options.scrollY + Math.max(options.stickyOffset, 0) + 12;
  const activationY = probeY - Math.max(switchThreshold, 0);

  if (activationY <= sections[0].top) {
    return sections[0].id;
  }

  let activeId = sections[0].id;
  for (let index = 1; index < sections.length; index += 1) {
    const current = sections[index];
    if (current.top <= activationY) {
      activeId = current.id;
      continue;
    }

    break;
  }

  return activeId;
}
