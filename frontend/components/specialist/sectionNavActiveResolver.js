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
  const reachedBottom = options.scrollY + options.viewportHeight >= options.documentHeight - bottomThreshold;
  if (reachedBottom) {
    return sections[sections.length - 1].id;
  }

  const probeY = options.scrollY + Math.max(options.stickyOffset, 0) + 12;

  if (probeY <= sections[0].top) {
    return sections[0].id;
  }

  for (let index = 0; index < sections.length; index += 1) {
    const current = sections[index];
    const next = sections[index + 1];

    if (!next) {
      return current.id;
    }

    const switchBoundary = current.top + (next.top - current.top) / 2;
    if (probeY < switchBoundary) {
      return current.id;
    }
  }

  return sections[sections.length - 1].id;
}
