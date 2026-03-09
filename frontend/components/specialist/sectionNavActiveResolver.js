/**
 * @typedef {{ id: string; top: number; bottom?: number; height?: number }} SectionGeometry
 */

/**
 * Resolve active section by real section geometry and current scroll position.
 * The section list must be in visual order.
 *
 * @param {SectionGeometry[]} sections
 * @param {{ scrollY: number; viewportHeight: number; documentHeight: number; stickyOffset: number; bottomThreshold?: number; switchThreshold?: number; viewportBottomInset?: number }} options
 * @returns {string | null}
 */
export function resolveActiveSectionId(sections, options) {
  if (!sections.length) {
    return null;
  }

  const bottomThreshold = options.bottomThreshold ?? 24;
  const switchThreshold = Math.max(options.switchThreshold ?? 8, 0);
  const reachedBottom = options.scrollY + options.viewportHeight >= options.documentHeight - bottomThreshold;
  if (reachedBottom) {
    return sections[sections.length - 1].id;
  }

  const normalizedSections = sections.map((section, index) => {
    const nextTop = sections[index + 1]?.top;
    const fallbackBottom = Number.isFinite(nextTop) ? nextTop : section.top + Math.max(section.height ?? 1, 1);
    const rawBottom = section.bottom;
    const bottom = Number.isFinite(rawBottom) && rawBottom > section.top ? rawBottom : Math.max(fallbackBottom, section.top + 1);

    return {
      id: section.id,
      top: section.top,
      bottom,
    };
  });

  const viewportBottomInset = Math.max(options.viewportBottomInset ?? 24, 0);
  const stickyOffset = Math.max(options.stickyOffset, 0);
  const viewportTop = options.scrollY + stickyOffset + 12 - switchThreshold;
  const viewportBottom = options.scrollY + Math.max(options.viewportHeight - viewportBottomInset, 0);

  if (viewportTop <= normalizedSections[0].top) {
    return normalizedSections[0].id;
  }

  const lastSection = normalizedSections[normalizedSections.length - 1];
  const lastSectionHeight = lastSection.bottom - lastSection.top;
  const lastVisibleOverlap = Math.max(0, Math.min(lastSection.bottom, viewportBottom) - Math.max(lastSection.top, viewportTop));
  const distance = lastSection.top - viewportTop;
  if (distance >= 0 && distance <= 48) {
    return lastSection.id;
  }
  if (lastSectionHeight >= 24 && lastVisibleOverlap >= lastSectionHeight) {
    return lastSection.id;
  }

  let activeId = normalizedSections[0].id;
  let bestOverlap = -1;

  for (const section of normalizedSections) {
    if (viewportTop >= section.top) {
      activeId = section.id;
    }

    const overlapStart = Math.max(section.top, viewportTop);
    const overlapEnd = Math.min(section.bottom, viewportBottom);
    const overlap = Math.max(0, overlapEnd - overlapStart);

    if (overlap > 0 && overlap >= bestOverlap) {
      bestOverlap = overlap;
      activeId = section.id;
    }
  }

  return activeId;
}
