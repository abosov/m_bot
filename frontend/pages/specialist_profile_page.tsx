import { useEffect, useMemo, useState } from "react";
import Header from "../components/specialist/Header";
import Hero from "../components/specialist/Hero";
import SectionAbout from "../components/specialist/SectionAbout";
import SectionEducation from "../components/specialist/SectionEducation";
import SectionReviews from "../components/specialist/SectionReviews";
import SectionServices from "../components/specialist/SectionServices";
import SectionCTA from "../components/specialist/SectionCTA";
import "../styles/specialist.css";

const SPECIALIST_SLUG_REGEX = /^[A-Za-z]+[A-Za-z]_[1-9][0-9]$/;
const RESERVED_PATHS = new Set(["pricing", "privacy", "terms", "revoke-access", "api", "static", "assets"]);
const MIN_SPECIALIST_ID = 10;
const MAX_SPECIALIST_ID = 30;

export type PublicSpecialistPagePayload = {
  profile: Record<string, unknown>;
  blocks: Array<Record<string, unknown>>;
  media: Array<Record<string, unknown>>;
  reviews: Array<Record<string, unknown>>;
};

export function validateSpecialistSlug(slug: string): boolean {
  if (!SPECIALIST_SLUG_REGEX.test(slug) || RESERVED_PATHS.has(slug)) {
    return false;
  }

  const idPart = slug.split("_")[1];
  const specialistId = Number(idPart);

  return specialistId >= MIN_SPECIALIST_ID && specialistId <= MAX_SPECIALIST_ID;
}

export async function loadSpecialistProfilePage(slug: string): Promise<PublicSpecialistPagePayload> {
  if (!validateSpecialistSlug(slug)) {
    throw new Error("Invalid specialist slug");
  }

  const response = await fetch(`/api/public/specialists/${encodeURIComponent(slug)}`);

  if (!response.ok) {
    throw new Error(`Failed to load specialist profile page: ${response.status}`);
  }

  return (await response.json()) as PublicSpecialistPagePayload;
}

type SpecialistProfilePageProps = {
  slug: string;
  loader?: (slug: string) => Promise<PublicSpecialistPagePayload>;
};

function SectionDocuments() {
  return <section id="documents" className="specialist-page__section">Документы</section>;
}

export function SpecialistProfilePage({ slug, loader = loadSpecialistProfilePage }: SpecialistProfilePageProps) {
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<PublicSpecialistPagePayload | null>(null);

  const isValidSlug = useMemo(() => validateSpecialistSlug(slug), [slug]);

  useEffect(() => {
    if (!isValidSlug) {
      setError("Invalid specialist slug");
      setPayload(null);
      return;
    }

    let cancelled = false;

    loader(slug)
      .then((loadedPayload) => {
        if (!cancelled) {
          setPayload(loadedPayload);
          setError(null);
        }
      })
      .catch((loadError: Error) => {
        if (!cancelled) {
          setPayload(null);
          setError(loadError.message);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isValidSlug, loader, slug]);

  const displayName = (payload?.profile.display_name as string | undefined) ?? "Специалист";
  const specialization = (payload?.profile.specialization as string | undefined) ?? "Специализация";

  if (error) {
    return <main>{error}</main>;
  }

  return (
    <main className="specialist-page">
      <Header displayName={displayName} specialization={specialization} />
      <Hero
        photoUrl={payload?.profile.photo_url as string | undefined}
        heroQuote={payload?.profile.hero_quote as string | undefined}
        clientBotUsername={payload?.profile.client_bot_username as string | undefined}
        specialistId={payload?.profile.specialist_id as number | undefined}
        telegram={payload?.profile.telegram as string | undefined}
        whatsapp={payload?.profile.whatsapp as string | undefined}
        phone={payload?.profile.phone as string | undefined}
        email={payload?.profile.email as string | undefined}
      />
      <SectionAbout blocks={payload?.blocks} />
      <SectionEducation blocks={payload?.blocks} />
      <SectionDocuments />
      <SectionServices blocks={payload?.blocks} />
      <SectionReviews reviews={payload?.reviews} />
      <SectionCTA
        clientBotUsername={payload?.profile.client_bot_username as string | undefined}
        specialistId={payload?.profile.specialist_id as number | undefined}
      />
    </main>
  );
}

export default SpecialistProfilePage;
