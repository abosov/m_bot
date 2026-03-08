type SpecialistHeaderProps = {
  displayName: string;
  specialization: string;
  bookingHref?: string;
};

export function Header({ displayName, specialization, bookingHref }: SpecialistHeaderProps) {

  return (
    <header id="specialist-sticky-header" className="specialist-header" aria-label="Specialist profile header">
      <div className="specialist-header__inner container">
        <div className="specialist-header__identity">
          <p className="specialist-header__display-name">{displayName}</p>
          <p className="specialist-header__specialization">{specialization}</p>
        </div>
        <div className="specialist-header__actions">
          <a
            id="specialist-header-book-link"
            className={`specialist-button specialist-button--primary specialist-header__book-button${bookingHref ? '' : ' specialist-hidden'}`}
            href={bookingHref || '#'}
            target="_blank"
            rel="noopener noreferrer"
          >
            Записаться
          </a>
        </div>
      </div>
    </header>
  );
}

export default Header;
