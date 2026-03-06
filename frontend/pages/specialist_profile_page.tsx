import { useEffect, useMemo, useState } from "react";
import Header from "../components/specialist/Header";
import Hero from "../components/specialist/Hero";
import SectionAbout from "../components/specialist/SectionAbout";
import SectionEducation from "../components/specialist/SectionEducation";
import SectionReviews from "../components/specialist/SectionReviews";
import SectionDocuments from "../components/specialist/SectionDocuments";
import SectionServices from "../components/specialist/SectionServices";
import SectionCTA from "../components/specialist/SectionCTA";
import "../styles/specialist.css";

const SPECIALIST_SLUG_REGEX = /^[A-Za-z]+[A-Za-z]_[1-9][0-9]$/;
const RESERVED_PATHS = new Set(["pricing", "privacy", "terms", "revoke-access", "api", "static", "assets"]);
const MIN_SPECIALIST_ID = 10;
const MAX_SPECIALIST_ID = 30;

export type PublicSpecialistPagePayload = {
  profile: PublicSpecialistProfile;
  blocks: Array<Record<string, unknown>>;
  media: Array<Record<string, unknown>>;
  reviews: Array<Record<string, unknown>>;
};

type PublicSpecialistContacts = {
  telegram?: string | null;
  whatsapp?: string | null;
  phone?: string | null;
  email?: string | null;
};

type PublicSpecialistProfile = {
  id: string;
  public_slug: string;
  display_name: string;
  specialization: string;
  hero_quote?: string | null;
  contacts: PublicSpecialistContacts;
  client_bot_username: string;
  photo_url?: string | null;
};

type HeroContactProps = {
  telegram?: string;
  whatsapp?: string;
  phone?: string;
  email?: string;
};

export function mapProfileToHeroContacts(profile?: PublicSpecialistProfile | null): HeroContactProps {
  return {
    telegram: profile?.contacts?.telegram ?? undefined,
    whatsapp: profile?.contacts?.whatsapp ?? undefined,
    phone: profile?.contacts?.phone ?? undefined,
    email: profile?.contacts?.email ?? undefined,
  };
}

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

  useEffect(() => {
    let animationFrameId: number | null = null;

    const updateStickyOffset = () => {
      const stickyHeader = document.getElementById("specialist-sticky-header");
      const measuredHeight = stickyHeader?.getBoundingClientRect().height ?? 120;
      const offset = `${Math.ceil(measuredHeight)}px`;

      document.documentElement.style.setProperty("--specialist-sticky-offset", offset);
    };

    const handleResize = () => {
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId);
      }

      animationFrameId = requestAnimationFrame(() => {
        updateStickyOffset();
        animationFrameId = null;
      });
    };

    updateStickyOffset();
    window.addEventListener("resize", handleResize);

    // TODO(US-PUB-UX-1): add UI test asserting anchor navigation keeps headings visible under sticky header.
    return () => {
      if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId);
      }

      window.removeEventListener("resize", handleResize);
      document.documentElement.style.removeProperty("--specialist-sticky-offset");
    };
  }, []);

  const displayName = (payload?.profile.display_name as string | undefined) ?? "Специалист";
  const specialization = (payload?.profile.specialization as string | undefined) ?? "Специализация";
  const heroContacts = mapProfileToHeroContacts(payload?.profile);
  const clientBotUsername = payload?.profile.client_bot_username;
  const specialistUuid = payload?.profile.id;

  if (error) {
    return <main>{error}</main>;
  }

  return (
    <main className="specialist-page">
      <Header
        displayName={displayName}
        specialization={specialization}
        clientBotUsername={clientBotUsername}
        specialistUuid={specialistUuid}
      />
      <Hero
        photoUrl={payload?.profile.photo_url as string | undefined}
        heroQuote={payload?.profile.hero_quote as string | undefined}
        clientBotUsername={clientBotUsername}
        specialistUuid={specialistUuid}
        telegram={heroContacts.telegram}
        whatsapp={heroContacts.whatsapp}
        phone={heroContacts.phone}
        email={heroContacts.email}
      />
      <SectionAbout blocks={payload?.blocks} />
      <SectionEducation blocks={payload?.blocks} />
      <SectionDocuments media={payload?.media} />
      <SectionServices blocks={payload?.blocks} />
      <SectionReviews blocks={payload?.blocks} />
      <SectionCTA clientBotUsername={clientBotUsername} specialistUuid={specialistUuid} />
    </main>
  );
}

export default SpecialistProfilePage;
