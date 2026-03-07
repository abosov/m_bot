import { type MouseEvent, useEffect, useMemo, useRef, useState } from "react";
import { resolveActiveSectionId } from "./sectionNavActiveResolver";

type SectionNavItem = {
  id: string;
  label: string;
};

type SectionNavProps = {
  items: SectionNavItem[];
};

export function SectionNav({ items }: SectionNavProps) {
  const [activeId, setActiveId] = useState<string | null>(items[0]?.id ?? null);
  const navListRef = useRef<HTMLDivElement | null>(null);

  const getStickyOffset = () => {
    const rootStyles = window.getComputedStyle(document.documentElement);
    const cssOffset = Number.parseFloat(rootStyles.getPropertyValue("--specialist-sticky-offset"));
    const stickyHeader = document.getElementById("specialist-sticky-header");
    const sectionNav = document.getElementById("specialist-section-nav");
    const headerHeight = stickyHeader?.getBoundingClientRect().height ?? 72;
    const sectionNavHeight = sectionNav?.getBoundingClientRect().height ?? 0;
    const measuredOffset = headerHeight + sectionNavHeight + 16;

    if (Number.isFinite(cssOffset) && cssOffset > 0) {
      return Math.max(cssOffset, measuredOffset);
    }

    return measuredOffset;
  };



  const navItems = useMemo(() => items.filter((item) => Boolean(item.id && item.label)), [items]);

  useEffect(() => {
    setActiveId(navItems[0]?.id ?? null);
  }, [navItems]);

  useEffect(() => {
    if (!navItems.length) {
      return;
    }

    const sections = navItems
      .map((item) => document.getElementById(item.id))
      .filter((section): section is HTMLElement => Boolean(section));

    if (!sections.length) {
      return;
    }

    let animationFrameId: number | null = null;

    const updateActiveSection = () => {
      const sectionGeometries = sections.map((section) => ({
        id: section.id,
        top: section.getBoundingClientRect().top + window.scrollY,
        bottom: section.getBoundingClientRect().bottom + window.scrollY,
        height: section.getBoundingClientRect().height,
      }));

      const nextId = resolveActiveSectionId(sectionGeometries, {
        scrollY: window.scrollY,
        viewportHeight: window.innerHeight || document.documentElement.clientHeight,
        documentHeight: document.documentElement.scrollHeight,
        stickyOffset: getStickyOffset(),
      });
      if (nextId) {
        setActiveId((prevId) => (prevId === nextId ? prevId : nextId));
      }
    };

    const scheduleUpdate = () => {
      if (animationFrameId !== null) {
        return;
      }

      animationFrameId = window.requestAnimationFrame(() => {
        animationFrameId = null;
        updateActiveSection();
      });
    };

    const observer = new IntersectionObserver(scheduleUpdate, {
      root: null,
      rootMargin: "-10% 0px -40% 0px",
      threshold: [0, 0.1, 0.25, 0.5, 0.75, 1],
    });

    sections.forEach((section) => observer.observe(section));
    updateActiveSection();
    window.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", scheduleUpdate);

    return () => {
      if (animationFrameId !== null) {
        window.cancelAnimationFrame(animationFrameId);
      }

      observer.disconnect();
      window.removeEventListener("scroll", scheduleUpdate);
      window.removeEventListener("resize", scheduleUpdate);
    };
  }, [navItems]);

  useEffect(() => {
    if (!activeId || !navListRef.current) {
      return;
    }

    const activeElement = navListRef.current.querySelector<HTMLElement>(`a[data-section-id="${activeId}"]`);
    activeElement?.scrollIntoView({ inline: "center", block: "nearest", behavior: "auto" });
  }, [activeId]);

  const handleNavigate = (event: MouseEvent<HTMLAnchorElement>, targetId: string) => {
    const target = document.getElementById(targetId);
    if (!target) {
      return;
    }

    event.preventDefault();
    setActiveId(targetId);
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    window.history.replaceState(null, "", `#${targetId}`);
  };

  if (!navItems.length) {
    return null;
  }

  return (
    <nav id="specialist-section-nav" className="specialist-subnav" aria-label="Навигация по разделам специалиста">
      <div className="container specialist-subnav__inner">
        <div className="specialist-subnav__list" ref={navListRef} role="tablist" aria-label="Разделы страницы">
          {navItems.map((item) => {
            const isActive = activeId === item.id;

            return (
              <a
                key={item.id}
                href={`#${item.id}`}
                data-section-id={item.id}
                className={`specialist-subnav__link${isActive ? " specialist-subnav__link--active" : ""}`}
                onClick={(event) => handleNavigate(event, item.id)}
                aria-current={isActive ? "true" : undefined}
                role="tab"
              >
                {item.label}
              </a>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

export default SectionNav;
