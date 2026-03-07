type SpecialistPublicBlock = Record<string, unknown>;

type ReviewItem = {
  text: string;
  author: string;
};

type SectionReviewsProps = {
  blocks?: SpecialistPublicBlock[];
};

function sanitizeText(input: string): string {
  return input
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+=("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "")
    .trim();
}

function normalizeReviewItem(raw: unknown): ReviewItem | null {
  if (typeof raw === "string") {
    const text = sanitizeText(raw);
    return text ? { text, author: "" } : null;
  }

  if (!raw || typeof raw !== "object") {
    return null;
  }

  const maybeItem = raw as Record<string, unknown>;
  const textCandidate = maybeItem.text ?? maybeItem.content ?? maybeItem.body;
  const authorCandidate = maybeItem.author ?? maybeItem.name;
  const text = typeof textCandidate === "string" ? sanitizeText(textCandidate) : "";
  const author = typeof authorCandidate === "string" ? sanitizeText(authorCandidate) : "";

  if (!text) {
    return null;
  }

  return { text, author };
}

function getReviewItems(blocks?: SpecialistPublicBlock[]): ReviewItem[] {
  const reviewsBlock = blocks?.find((block) => block.block_type === "reviews");

  if (!reviewsBlock) {
    return [];
  }

  const candidate = reviewsBlock.items ?? reviewsBlock.content ?? reviewsBlock.body ?? reviewsBlock.text;

  if (Array.isArray(candidate)) {
    return candidate.map(normalizeReviewItem).filter((item): item is ReviewItem => Boolean(item));
  }

  if (typeof candidate === "string") {
    return candidate
      .split("\n")
      .map((line) => normalizeReviewItem(line))
      .filter((item): item is ReviewItem => Boolean(item));
  }

  return [];
}

export function SectionReviews({ blocks }: SectionReviewsProps) {
  const reviewItems = getReviewItems(blocks);

  if (!reviewItems.length) {
    return null;
  }

  return (
    <section className="specialist-page__section section" aria-label="Отзывы">
      <div id="reviews" className="specialist-section-anchor" aria-hidden="true" />
      <div className="container">
        <div className="section-card specialist-card specialist-content-card">
          <h2 className="section-title specialist-section-title">Отзывы</h2>
          <ul className="reviews-grid" aria-label="Отзывы клиентов">
            {reviewItems.map((item, index) => (
              <li key={`${item.text}-${item.author}-${index}`} className="review-card">
                <p className="review-text">{item.text}</p>
                {item.author ? <p className="review-author">{item.author}</p> : null}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export default SectionReviews;
