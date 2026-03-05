type SpecialistHeaderProps = {
  displayName: string;
  specialization: string;
};

const NAV_ITEMS = [
  { href: "#about", label: "О себе" },
  { href: "#education", label: "Образование" },
  { href: "#documents", label: "Документы" },
  { href: "#services", label: "Услуги и цены" },
  { href: "#reviews", label: "Отзывы" },
  { href: "#booking", label: "Записаться", isCta: true },
];

export function Header({ displayName, specialization }: SpecialistHeaderProps) {
  return (
    <header className="specialist-header" aria-label="Specialist profile header">
      <div className="specialist-header__identity">
        <p className="specialist-header__display-name">{displayName}</p>
        <p className="specialist-header__specialization">{specialization}</p>
      </div>

      <nav className="specialist-header__menu" aria-label="Меню специалиста">
        {NAV_ITEMS.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className={item.isCta ? "specialist-header__cta" : "specialist-header__menu-link"}
          >
            {item.label}
          </a>
        ))}
      </nav>
    </header>
  );
}

export default Header;
