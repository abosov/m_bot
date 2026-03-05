import Contacts from "./Contacts";

const ALLOWED_IMAGE_HOSTNAMES = new Set(["images.mbot.app", "cdn.mbot.app"]);
const TELEGRAM_BOT_USERNAME_REGEX = /^[A-Za-z][A-Za-z0-9_]{3,30}bot$/i;
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type SpecialistHeroProps = {
  photoUrl?: string;
  heroQuote?: string;
  clientBotUsername?: string;
  specialistId?: string;
  telegram?: string;
  whatsapp?: string;
  phone?: string;
  email?: string;
};

function isAllowedImageUrl(photoUrl?: string): boolean {
  if (!photoUrl) {
    return false;
  }

  try {
    const url = new URL(photoUrl);
    return ALLOWED_IMAGE_HOSTNAMES.has(url.hostname);
  } catch {
    return false;
  }
}

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

export function buildClientBotWriteLink(clientBotUsername?: string, specialistId?: string): string | null {
  if (!isValidClientBotUsername(clientBotUsername) || !isValidSpecialistId(specialistId)) {
    return null;
  }

  return `https://t.me/${clientBotUsername}?start=write_${specialistId}`;
}

export function Hero({
  photoUrl,
  heroQuote,
  clientBotUsername,
  specialistId,
  telegram,
  whatsapp,
  phone,
  email,
}: SpecialistHeroProps) {
  const canRenderImage = isAllowedImageUrl(photoUrl);
  const clientBotWriteLink = buildClientBotWriteLink(clientBotUsername, specialistId);

  return (
    <section id="hero" className="specialist-page__section" aria-label="Hero специалиста">
      <div
        className="specialist-hero"
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(220px, 1fr) minmax(320px, 2fr)",
          gridTemplateAreas: '"photo quote" "photo button"',
          gap: "16px",
          alignItems: "start",
        }}
      >
        <div style={{ gridArea: "photo" }}>
          {canRenderImage ? (
            <img src={photoUrl} alt="Фото специалиста" />
          ) : (
            <div aria-label="Фото специалиста недоступно">Фото специалиста</div>
          )}
        </div>

        <blockquote style={{ gridArea: "quote", margin: 0 }}>{heroQuote ?? ""}</blockquote>

        <div style={{ gridArea: "button" }}>
          {clientBotWriteLink ? (
            <a href={clientBotWriteLink}>Связаться со специалистом</a>
          ) : (
            <span>Связаться со специалистом</span>
          )}

          <Contacts telegram={telegram} whatsapp={whatsapp} phone={phone} email={email} />
        </div>
      </div>
    </section>
  );
}

export default Hero;
