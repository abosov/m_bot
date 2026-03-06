import Contacts from "./Contacts";
import { buildClientBotLink } from "../../utils/telegram_links";

const ALLOWED_IMAGE_HOSTNAMES = new Set(["images.mbot.app", "cdn.mbot.app"]);

type SpecialistHeroProps = {
  photoUrl?: string;
  heroQuote?: string;
  clientBotUsername?: string;
  specialistUuid?: string;
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

export function Hero({
  photoUrl,
  heroQuote,
  clientBotUsername,
  specialistUuid,
  telegram,
  whatsapp,
  phone,
  email,
}: SpecialistHeroProps) {
  const canRenderImage = isAllowedImageUrl(photoUrl);
  const quoteText = (heroQuote ?? "").trim();
  const hasQuote = quoteText.length > 0;
  const clientBotContactLink = buildClientBotLink(clientBotUsername, "contact_specialist", specialistUuid);

  return (
    <section id="hero" className="specialist-page__section" aria-label="Hero специалиста">
      <div
        className="specialist-hero"
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(220px, 1fr) minmax(320px, 2fr)",
          gridTemplateAreas: hasQuote ? '"photo quote" "photo button"' : '"photo button"',
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

        {hasQuote ? <blockquote style={{ gridArea: "quote", margin: 0 }}>{quoteText}</blockquote> : null}

        <div style={{ gridArea: "button" }}>
          {clientBotContactLink ? (
            <a href={clientBotContactLink} target="_blank" rel="noopener noreferrer">
              Связаться со специалистом
            </a>
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
