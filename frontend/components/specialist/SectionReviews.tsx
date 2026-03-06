type SpecialistPublicBlock = Record<string, unknown>;

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

function getReviewItems(blocks?: SpecialistPublicBlock[]): string[] {
  const reviewsBlock = blocks?.find((block) => block.block_type === "reviews");

  if (!reviewsBlock) {
    return [];
  }

  const candidate = reviewsBlock.items ?? reviewsBlock.content ?? reviewsBlock.body ?? reviewsBlock.text;

  if (Array.isArray(candidate)) {
    return candidate
      .filter((item): item is string => typeof item === "string")
      .map((item) => sanitizeText(item))
      .filter(Boolean);
  }

  if (typeof candidate === "string") {
    return candidate
      .split("\n")
      .map((line) => sanitizeText(line))
      .filter(Boolean);
  }

  return [];
}

export function SectionReviews({ blocks }: SectionReviewsProps) {
  const reviewItems = getReviewItems(blocks);

  if (!reviewItems.length) {
    return null;
  }

  return (
    <section id="reviews" className="specialist-page__section" aria-label="Отзывы">
      <h2>Отзывы</h2>
      <ul>
        {reviewItems.map((item, index) => (
          <li key={`${item}-${index}`}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

export default SectionReviews;
