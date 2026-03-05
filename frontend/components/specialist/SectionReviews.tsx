type SpecialistPublicReview = Record<string, unknown>;

type ReviewCard = {
  authorName: string;
  content: string;
};

type SectionReviewsProps = {
  reviews?: SpecialistPublicReview[];
};

function sanitizeHtml(input: string): string {
  return input
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+=("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "");
}

function normalizeReview(value: SpecialistPublicReview): ReviewCard | null {
  const authorRaw = value.author_name;
  const contentRaw = value.content;

  if (typeof authorRaw !== "string" || typeof contentRaw !== "string") {
    return null;
  }

  const authorName = sanitizeHtml(authorRaw).trim();
  const content = sanitizeHtml(contentRaw).trim();

  if (!authorName || !content) {
    return null;
  }

  return { authorName, content };
}

export function SectionReviews({ reviews }: SectionReviewsProps) {
  const normalizedReviews = (reviews ?? []).map(normalizeReview).filter((review): review is ReviewCard => Boolean(review));

  if (!normalizedReviews.length) {
    return null;
  }

  return (
    <section id="reviews" className="specialist-page__section" aria-label="Отзывы">
      <h2>Отзывы</h2>
      <div>
        {normalizedReviews.map((review, index) => (
          <article key={`${review.authorName}-${index}`}>
            <p>{review.authorName}</p>
            <p>{review.content}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default SectionReviews;
