const TELEGRAM_BOT_USERNAME_REGEX = /^[A-Za-z][A-Za-z0-9_]{3,30}bot$/i;
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type SectionCTAProps = {
  clientBotUsername?: string;
  specialistId?: string;
};

function isValidClientBotUsername(clientBotUsername?: string): clientBotUsername is string {
  if (!clientBotUsername) {
    return false;
  }

  return TELEGRAM_BOT_USERNAME_REGEX.test(clientBotUsername);
}

function isValidSpecialistId(specialistId?: string): specialistId is string {
  if (!specialistId) {
    return false;
  }

  return UUID_REGEX.test(specialistId);
}

export function buildClientBotBookingLink(clientBotUsername?: string, specialistId?: string): string | null {
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
