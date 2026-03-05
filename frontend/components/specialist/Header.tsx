import { buildClientBotLink } from "../../utils/telegram_links";

type SpecialistHeaderProps = {
  displayName: string;
  specialization: string;
  clientBotUsername?: string;
};

const NAV_ITEMS = [
  { href: "#about", label: "О себе" },
  { href: "#education", label: "Образование" },
  { href: "#documents", label: "Документы" },
  { href: "#services", label: "Услуги и цены" },
  { href: "#reviews", label: "Отзывы" },
];

export function Header({ displayName, specialization, clientBotUsername }: SpecialistHeaderProps) {
  const bookingLink = buildClientBotLink(clientBotUsername, "book");

  return (
    <header id="specialist-sticky-header" className="specialist-header" aria-label="Specialist profile header">
      <div className="specialist-header__identity">
        <p className="specialist-header__display-name">{displayName}</p>
        <p className="specialist-header__specialization">{specialization}</p>
      </div>

      <nav className="specialist-header__menu" aria-label="Меню специалиста">
        {NAV_ITEMS.map((item) => (
          <a key={item.href} href={item.href} className="specialist-header__menu-link">
            {item.label}
          </a>
        ))}
        <a
          href={bookingLink ?? "#booking"}
          className="specialist-header__cta"
          target={bookingLink ? "_blank" : undefined}
          rel={bookingLink ? "noopener noreferrer" : undefined}
        >
          Записаться
        </a>
      </nav>
    </header>
  );
}

export default Header;
