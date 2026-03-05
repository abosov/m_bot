type SpecialistPublicBlock = Record<string, unknown>;

type ServiceItem = {
  name: string;
  price: string;
};

type SectionServicesProps = {
  blocks?: SpecialistPublicBlock[];
};

function sanitizeText(input: string): string {
  return input
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+=("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
    .replace(/javascript:/gi, "")
    .trim();
}

function normalizeServiceItem(raw: unknown): ServiceItem | null {
  if (typeof raw === "string") {
    const sanitized = sanitizeText(raw);
    return sanitized ? { name: sanitized, price: "" } : null;
  }

  if (!raw || typeof raw !== "object") {
    return null;
  }

  const maybeItem = raw as Record<string, unknown>;
  const name = typeof maybeItem.name === "string" ? sanitizeText(maybeItem.name) : "";
  const price = typeof maybeItem.price === "string" ? sanitizeText(maybeItem.price) : "";

  if (!name && !price) {
    return null;
  }

  return { name, price };
}

function getServiceItems(blocks?: SpecialistPublicBlock[]): ServiceItem[] {
  const servicesBlock = blocks?.find((block) => block.block_type === "services");

  if (!servicesBlock) {
    return [];
  }

  const candidate = servicesBlock.items ?? servicesBlock.content ?? servicesBlock.body ?? servicesBlock.text;

  if (Array.isArray(candidate)) {
    return candidate.map(normalizeServiceItem).filter((item): item is ServiceItem => Boolean(item));
  }

  if (typeof candidate === "string") {
    return candidate
      .split("\n")
      .map((line) => normalizeServiceItem(line))
      .filter((item): item is ServiceItem => Boolean(item));
  }

  return [];
}

export function SectionServices({ blocks }: SectionServicesProps) {
  const serviceItems = getServiceItems(blocks);

  if (!serviceItems.length) {
    return null;
  }

  return (
    <section id="services" className="specialist-page__section" aria-label="Услуги и цены">
      <h2>Услуги и цены</h2>
      <ul>
        {serviceItems.map((item, index) => (
          <li key={`${item.name}-${item.price}-${index}`}>
            <span>{item.name}</span>
            {item.price ? <span>{item.price}</span> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default SectionServices;
