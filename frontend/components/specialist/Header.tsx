import { buildClientBotLink } from "../../utils/telegram_links";

type SpecialistHeaderProps = {
  displayName: string;
  specialization: string;
  clientBotUsername?: string;
  specialistUuid?: string;
};

export function Header({ displayName, specialization, clientBotUsername, specialistUuid }: SpecialistHeaderProps) {
  const bookingLink = buildClientBotLink(clientBotUsername, "book", specialistUuid);

  return (
    <header id="specialist-sticky-header" className="specialist-header" aria-label="Specialist profile header">
      <div className="specialist-header__inner container">
        <div className="specialist-header__identity">
          <p className="specialist-header__display-name">{displayName}</p>
          <p className="specialist-header__specialization">{specialization}</p>
        </div>

        {bookingLink ? (
          <a href={bookingLink} className="specialist-button specialist-button--primary specialist-header__cta" target="_blank" rel="noopener noreferrer">
            Записаться
          </a>
        ) : null}
      </div>
    </header>
  );
}

export default Header;
