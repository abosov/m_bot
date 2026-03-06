import Contacts from "./Contacts";
import { buildClientBotLink } from "../../utils/telegram_links";

const ALLOWED_IMAGE_HOSTNAMES = new Set(["images.mbot.app", "cdn.mbot.app"]);

type SpecialistHeroProps = {
  displayName: string;
  specialization: string;
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
  displayName,
  specialization,
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
    <section id="hero" className="specialist-page__section specialist-page__section--hero section" aria-label="Hero специалиста">
      <div className="container">
        <div className="section-card specialist-card specialist-hero hero-grid">
          <div className="specialist-hero__photo-wrap profile-photo">
            {canRenderImage ? (
              <img src={photoUrl} alt={`Фото специалиста ${displayName}`} className="specialist-hero__photo" loading="eager" />
            ) : (
              <div className="specialist-hero__photo-placeholder" aria-label="Фото специалиста недоступно">
                <span className="specialist-hero__photo-placeholder-icon" aria-hidden="true">
                  ⊚
                </span>
                <p className="specialist-hero__photo-placeholder-title">Фото скоро появится</p>
                <p className="specialist-hero__photo-placeholder-text">Пока можно познакомиться с профилем специалиста.</p>
              </div>
            )}
          </div>

          <div className="specialist-hero__content">
            <p className="specialist-hero__kicker">Публичный профиль специалиста</p>
            <h1 className="specialist-hero__title hero-name">{displayName}</h1>
            <p className="specialist-hero__subtitle hero-specialization">{specialization}</p>

            {hasQuote ? <blockquote className="specialist-hero__quote hero-quote">{quoteText}</blockquote> : null}

            <Contacts telegram={telegram} whatsapp={whatsapp} phone={phone} email={email} />

            <div className="specialist-hero__actions hero-cta">
              {clientBotContactLink ? (
                <a href={clientBotContactLink} target="_blank" rel="noopener noreferrer" className="specialist-button specialist-button--primary hero-button">
                  Связаться со специалистом
                </a>
              ) : (
                <span className="specialist-button specialist-button--disabled hero-button">Связаться со специалистом</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default Hero;
