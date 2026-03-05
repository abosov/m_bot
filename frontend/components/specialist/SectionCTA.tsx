const TELEGRAM_BOT_USERNAME_REGEX = /^[A-Za-z][A-Za-z0-9_]{3,30}bot$/i;

type SectionCTAProps = {
  clientBotUsername?: string;
  specialistId?: number;
};

function isValidClientBotUsername(clientBotUsername?: string): clientBotUsername is string {
  if (!clientBotUsername) {
    return false;
  }

  return TELEGRAM_BOT_USERNAME_REGEX.test(clientBotUsername);
}

function isValidSpecialistId(specialistId?: number): specialistId is number {
  return Number.isInteger(specialistId) && specialistId > 0;
}

export function buildClientBotBookingLink(clientBotUsername?: string, specialistId?: number): string | null {
  if (!isValidClientBotUsername(clientBotUsername) || !isValidSpecialistId(specialistId)) {
    return null;
  }

  return `https://t.me/${clientBotUsername}?start=book_${specialistId}`;
}

export function SectionCTA({ clientBotUsername, specialistId }: SectionCTAProps) {
  const bookingLink = buildClientBotBookingLink(clientBotUsername, specialistId);

  if (!bookingLink) {
    return null;
  }

  return (
    <section id="booking" className="specialist-page__section" aria-label="Запись на консультацию">
      <a href={bookingLink}>Записаться на консультацию</a>
    </section>
  );
}

export default SectionCTA;
