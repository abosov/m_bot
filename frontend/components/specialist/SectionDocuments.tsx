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
    <section id="documents" className="specialist-page__section" aria-label="Документы">
      <h2>Документы</h2>
      <ul>
        {documentItems.map((item, index) => (
          <li key={`${item.title}-${index}`}>
            {item.url ? (
              <a href={item.url} target="_blank" rel="noopener noreferrer">
                {item.title}
              </a>
            ) : (
              <span>{item.title}</span>
            )}
          </li>
        ))}
      </ul>
      {documentItems.some((item) => !item.url) ? <p>Скоро будет доступно скачивание</p> : null}
    </section>
  );
}

export default SectionDocuments;
