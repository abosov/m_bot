type SpecialistPublicBlock = Record<string, unknown>;

type SectionAboutProps = {
  blocks?: SpecialistPublicBlock[];
};

function sanitizeHtml(input: string): string {
  return input
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+=("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "");
}

function getAboutBlockContent(blocks?: SpecialistPublicBlock[]): string | null {
  const aboutBlock = blocks?.find((block) => block.block_type === "about");

  if (!aboutBlock) {
    return null;
  }

  const rawContent = aboutBlock.content ?? aboutBlock.body ?? aboutBlock.text;

  if (typeof rawContent !== "string") {
    return null;
  }

  const sanitizedContent = sanitizeHtml(rawContent).trim();
  return sanitizedContent || null;
}

export function SectionAbout({ blocks }: SectionAboutProps) {
  const aboutContent = getAboutBlockContent(blocks);

  if (!aboutContent) {
    return null;
  }

  return (
    <section id="about" className="specialist-page__section" aria-label="О себе">
      <h2>О себе</h2>
      <div dangerouslySetInnerHTML={{ __html: aboutContent }} />
    </section>
  );
}

export default SectionAbout;
