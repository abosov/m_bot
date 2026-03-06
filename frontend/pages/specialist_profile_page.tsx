import { useEffect, useMemo, useState } from "react";
import Header from "../components/specialist/Header";
import Hero from "../components/specialist/Hero";
import SectionNav from "../components/specialist/SectionNav";
import SectionAbout from "../components/specialist/SectionAbout";
import SectionEducation from "../components/specialist/SectionEducation";
import SectionReviews from "../components/specialist/SectionReviews";
import SectionDocuments from "../components/specialist/SectionDocuments";
import SectionServices from "../components/specialist/SectionServices";
import SectionCTA from "../components/specialist/SectionCTA";
import "../styles/layout.css";
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


function hasNonEmptyLines(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.some((item) => typeof item === "string" && item.trim().length > 0);
  }

  if (typeof value === "string") {
    return value
      .split("\n")
      .map((line) => line.trim())
      .some(Boolean);
  }

  return false;
}

function hasBlockContent(blocks: Array<Record<string, unknown>> | undefined, blockType: string): boolean {
  const target = blocks?.find((block) => block.block_type === blockType);
  if (!target) {
    return false;
  }

  return hasNonEmptyLines(target.items ?? target.content ?? target.body ?? target.text);
}

function hasDocumentMedia(media: Array<Record<string, unknown>> | undefined): boolean {
  return Boolean(
    media?.some((item) => {
      const mediaType = typeof item.media_type === "string" ? item.media_type.trim().toLowerCase() : "";
      const title = typeof item.title === "string" ? item.title.trim() : "";
      return mediaType === "document" && title.length > 0;
    }),
  );
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
      const sectionNav = document.getElementById("specialist-section-nav");
      const headerHeight = stickyHeader?.getBoundingClientRect().height ?? 72;
      const sectionNavHeight = sectionNav?.getBoundingClientRect().height ?? 0;
      const measuredHeight = headerHeight + sectionNavHeight + 16;
      const offset = `${Math.ceil(measuredHeight)}px`;

      document.documentElement.style.setProperty("--specialist-header-height", `${Math.ceil(headerHeight)}px`);
      document.documentElement.style.setProperty("--specialist-subnav-height", `${Math.ceil(sectionNavHeight)}px`);
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
      document.documentElement.style.removeProperty("--specialist-header-height");
      document.documentElement.style.removeProperty("--specialist-subnav-height");
      document.documentElement.style.removeProperty("--specialist-sticky-offset");
    };
  }, []);

  const displayName = (payload?.profile.display_name as string | undefined) ?? "Специалист";
  const specialization = (payload?.profile.specialization as string | undefined) ?? "Специализация";
  const heroContacts = mapProfileToHeroContacts(payload?.profile);
  const clientBotUsername = payload?.profile.client_bot_username;
  const specialistUuid = payload?.profile.id;

  const navItems = [
    hasBlockContent(payload?.blocks, "about") ? { id: "about", label: "О себе" } : null,
    hasBlockContent(payload?.blocks, "education") ? { id: "education", label: "Образование" } : null,
    hasDocumentMedia(payload?.media) ? { id: "documents", label: "Документы" } : null,
    hasBlockContent(payload?.blocks, "services") ? { id: "services", label: "Услуги и цены" } : null,
    hasBlockContent(payload?.blocks, "reviews") ? { id: "reviews", label: "Отзывы" } : null,
    clientBotUsername && specialistUuid ? { id: "booking", label: "Записаться" } : null,
  ].filter((item): item is { id: string; label: string } => Boolean(item));

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
        displayName={displayName}
        specialization={specialization}
        photoUrl={payload?.profile.photo_url as string | undefined}
        heroQuote={payload?.profile.hero_quote as string | undefined}
        clientBotUsername={clientBotUsername}
        specialistUuid={specialistUuid}
        telegram={heroContacts.telegram}
        whatsapp={heroContacts.whatsapp}
        phone={heroContacts.phone}
        email={heroContacts.email}
      />
      <SectionNav items={navItems} clientBotUsername={clientBotUsername} specialistUuid={specialistUuid} />
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
