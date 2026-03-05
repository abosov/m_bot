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
    <section id="booking" className="specialist-page__section" aria-label="Запись на консультацию">
      <a href={bookingLink} target="_blank" rel="noopener noreferrer">
        Записаться на консультацию
      </a>
    </section>
  );
}

export default SectionCTA;
