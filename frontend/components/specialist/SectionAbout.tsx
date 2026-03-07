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
    <section className="specialist-page__section section" aria-label="О себе">
      <div id="about" className="specialist-section-anchor" aria-hidden="true" />
      <div className="container">
        <div className="section-card specialist-card specialist-content-card">
          <h2 className="section-title specialist-section-title">О себе</h2>
            <div className="section-text specialist-rich-text" dangerouslySetInnerHTML={{ __html: aboutContent }} />
        </div>
      </div>
    </section>
  );
}

export default SectionAbout;
