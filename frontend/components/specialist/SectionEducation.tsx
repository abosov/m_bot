type SpecialistPublicBlock = Record<string, unknown>;

type SectionEducationProps = {
  blocks?: SpecialistPublicBlock[];
};

function sanitizeHtml(input: string): string {
  return input
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+=("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "");
}

function asEducationList(rawContent: unknown): string[] {
  if (Array.isArray(rawContent)) {
    return rawContent.filter((item): item is string => typeof item === "string").map((item) => sanitizeHtml(item).trim()).filter(Boolean);
  }

  if (typeof rawContent === "string") {
    return rawContent
      .split("\n")
      .map((line) => sanitizeHtml(line).trim())
      .filter(Boolean);
  }

  return [];
}

function getEducationItems(blocks?: SpecialistPublicBlock[]): string[] {
  const educationBlock = blocks?.find((block) => block.block_type === "education");

  if (!educationBlock) {
    return [];
  }

  return asEducationList(educationBlock.items ?? educationBlock.content ?? educationBlock.body ?? educationBlock.text);
}

export function SectionEducation({ blocks }: SectionEducationProps) {
  const educationItems = getEducationItems(blocks);

  if (!educationItems.length) {
    return null;
  }

  return (
    <section id="education" className="specialist-page__section" aria-label="Образование">
      <h2>Образование</h2>
      <ul>
        {educationItems.map((item, index) => (
          <li key={`${item}-${index}`}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

export default SectionEducation;
