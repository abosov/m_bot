import { type MouseEvent, useEffect, useMemo, useRef, useState } from "react";

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
    if (Number.isFinite(cssOffset) && cssOffset > 0) {
      return cssOffset;
    }

    const stickyHeader = document.getElementById("specialist-sticky-header");
    const sectionNav = document.getElementById("specialist-section-nav");
    const headerHeight = stickyHeader?.getBoundingClientRect().height ?? 72;
    const sectionNavHeight = sectionNav?.getBoundingClientRect().height ?? 0;
    return headerHeight + sectionNavHeight + 16;
  };

  const resolveActiveSection = (sections: HTMLElement[]) => {
    if (!sections.length) {
      return null;
    }

    const stickyOffset = getStickyOffset();
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    const docHeight = document.documentElement.scrollHeight;
    const isNearPageBottom = window.scrollY + viewportHeight >= docHeight - 2;

    if (isNearPageBottom) {
      return sections[sections.length - 1]?.id ?? null;
    }

    const anchorY = Math.min(Math.max(stickyOffset + 8, 0), viewportHeight * 0.75);
    let containingId: string | null = null;
    let nearestAboveId: string | null = null;
    let nearestAboveTop = Number.NEGATIVE_INFINITY;
    let nearestBelowId: string | null = null;
    let nearestBelowTop = Number.POSITIVE_INFINITY;

    sections.forEach((section) => {
      const rect = section.getBoundingClientRect();

      if (rect.top <= anchorY && rect.bottom > anchorY) {
        containingId = section.id;
      }

      if (rect.top <= anchorY && rect.top > nearestAboveTop) {
        nearestAboveTop = rect.top;
        nearestAboveId = section.id;
      }

      if (rect.top > anchorY && rect.top < nearestBelowTop) {
        nearestBelowTop = rect.top;
        nearestBelowId = section.id;
      }
    });

    return containingId ?? nearestAboveId ?? nearestBelowId ?? sections[0]?.id ?? null;
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
      const nextId = resolveActiveSection(sections);
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
      rootMargin: "-20% 0px -70% 0px",
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
