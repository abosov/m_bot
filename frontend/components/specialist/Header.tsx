type SpecialistHeaderProps = {
  displayName: string;
  specialization: string;
  clientBotUsername?: string;
};

export function Header({ displayName, specialization, clientBotUsername }: SpecialistHeaderProps) {
  const headerBookLink = clientBotUsername ? `https://t.me/${clientBotUsername}?start=book` : null;

  return (
    <header id="specialist-sticky-header" className="specialist-header" aria-label="Specialist profile header">
      <div className="specialist-header__inner container">
        <div className="specialist-header__identity">
          <p className="specialist-header__display-name">{displayName}</p>
          <p className="specialist-header__specialization">{specialization}</p>
        </div>
        {headerBookLink ? (
          <a
            id="header-book-button"
            className="header-cta-book"
            href={headerBookLink}
            target="_blank"
            rel="noopener"
          >
            Записаться
          </a>
        ) : null}
      </div>
    </header>
  );
}

export default Header;
