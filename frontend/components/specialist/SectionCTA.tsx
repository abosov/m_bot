import { buildClientBotLink } from "../../utils/telegram_links";

type SectionCTAProps = {
  clientBotUsername?: string;
  specialistUuid?: string;
};

export function SectionCTA({ clientBotUsername, specialistUuid }: SectionCTAProps) {
  const bookingLink = buildClientBotLink(clientBotUsername, "book", specialistUuid);

  if (!bookingLink) {
    return null;
  }

  return (
    <section id="booking" className="specialist-page__section section" aria-label="Запись на консультацию">
      <div className="container">
        <div className="section-card specialist-card specialist-cta-card cta-final">
          <h2 className="section-title specialist-section-title cta-final-title">Запишитесь на первую консультацию</h2>
          <p className="section-text specialist-cta-card__text">Выберите удобное время и начните работу со специалистом уже сегодня.</p>
          <a href={bookingLink} target="_blank" rel="noopener noreferrer" className="specialist-button specialist-button--primary specialist-button--large cta-final-button">
            Записаться на консультацию
          </a>
        </div>
      </div>
    </section>
  );
}

export default SectionCTA;
