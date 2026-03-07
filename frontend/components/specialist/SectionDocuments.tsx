type SpecialistPublicMedia = Record<string, unknown>;

type SectionDocumentsProps = {
  media?: SpecialistPublicMedia[];
};

type DocumentItem = {
  title: string;
  url: string | null;
};

function sanitizeText(input: string): string {
  return input
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+=("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "")
    .trim();
}

function normalizeUrl(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const sanitized = sanitizeText(value);
  if (!sanitized) {
    return null;
  }

  if (!/^https?:\/\//i.test(sanitized)) {
    return null;
  }

  return sanitized;
}

function normalizeDocumentItem(raw: SpecialistPublicMedia): DocumentItem | null {
  const mediaType = typeof raw.media_type === "string" ? raw.media_type.trim().toLowerCase() : "";
  if (mediaType !== "document") {
    return null;
  }

  const titleCandidate = raw.title ?? raw.name;
  if (typeof titleCandidate !== "string") {
    return null;
  }

  const title = sanitizeText(titleCandidate);
  if (!title) {
    return null;
  }

  return {
    title,
    url: normalizeUrl(raw.url),
  };
}

function getDocumentItems(media?: SpecialistPublicMedia[]): DocumentItem[] {
  if (!Array.isArray(media)) {
    return [];
  }

  return media.map(normalizeDocumentItem).filter((item): item is DocumentItem => Boolean(item));
}

export function SectionDocuments({ media }: SectionDocumentsProps) {
  const documentItems = getDocumentItems(media);

  if (!documentItems.length) {
    return null;
  }

  return (
    <section className="specialist-page__section section" aria-label="Документы">
      <div id="documents" className="specialist-section-anchor" aria-hidden="true" />
      <div className="container">
        <div className="section-card specialist-card specialist-content-card">
          <h2 className="section-title specialist-section-title">Документы</h2>
          <ul className="specialist-grid specialist-grid--documents">
          {documentItems.map((item, index) => (
            <li key={`${item.title}-${index}`} className="specialist-grid-card">
              {item.url ? (
                <a href={item.url} target="_blank" rel="noopener noreferrer" className="specialist-grid-card__title">
                  {item.title}
                </a>
              ) : (
                <span className="specialist-grid-card__title">{item.title}</span>
              )}
              <p className="specialist-grid-card__meta">Документ специалиста</p>
            </li>
          ))}
        </ul>
        {documentItems.some((item) => !item.url) ? <p className="specialist-section-note">Скоро будет доступно скачивание</p> : null}
        </div>
      </div>
    </section>
  );
}

export default SectionDocuments;
