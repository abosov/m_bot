import { type MouseEvent, useEffect, useMemo, useRef, useState } from "react";
import { buildClientBotLink } from "../../utils/telegram_links";

type SectionNavItem = {
  id: string;
  label: string;
};

type SectionNavProps = {
  items: SectionNavItem[];
  clientBotUsername?: string;
  specialistUuid?: string;
};

export function SectionNav({ items, clientBotUsername, specialistUuid }: SectionNavProps) {
  const [activeId, setActiveId] = useState<string | null>(items[0]?.id ?? null);
  const navListRef = useRef<HTMLDivElement | null>(null);

  const bookingLink = buildClientBotLink(clientBotUsername, "book", specialistUuid);

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

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntries = entries.filter((entry) => entry.isIntersecting);
        if (!visibleEntries.length) {
          return;
        }

        const next = visibleEntries
          .sort((a, b) => {
            if (b.intersectionRatio !== a.intersectionRatio) {
              return b.intersectionRatio - a.intersectionRatio;
            }
            return a.boundingClientRect.top - b.boundingClientRect.top;
          })
          .map((entry) => entry.target.id)[0];

        if (next) {
          setActiveId(next);
        }
      },
      {
        root: null,
        rootMargin: "-28% 0px -58% 0px",
        threshold: [0.1, 0.3, 0.6],
      },
    );

    sections.forEach((section) => observer.observe(section));

    return () => {
      observer.disconnect();
    };
  }, [navItems]);

  useEffect(() => {
    if (!activeId || !navListRef.current) {
      return;
    }

    const activeElement = navListRef.current.querySelector<HTMLElement>(`a[data-section-id="${activeId}"]`);
    activeElement?.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
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

        {bookingLink ? (
          <a href={bookingLink} target="_blank" rel="noopener noreferrer" className="specialist-button specialist-button--primary specialist-subnav__cta">
            Записаться
          </a>
        ) : null}
      </div>
    </nav>
  );
}

export default SectionNav;
