type SpecialistPublicBlock = Record<string, unknown>;

type ServiceItem = {
  name: string;
  price: string;
  description: string;
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

function buildServiceLabel(item: ServiceItem): string {
  const name = item.name.trim();
  const description = item.description.trim();

  if (name && description) {
    return `${name} — ${description}`;
  }

  return name || description;
}

function normalizeServiceItem(raw: unknown): ServiceItem | null {
  if (typeof raw === "string") {
    const sanitized = sanitizeText(raw);
    return sanitized ? { name: sanitized, price: "", description: "" } : null;
  }

  if (!raw || typeof raw !== "object") {
    return null;
  }

  const maybeItem = raw as Record<string, unknown>;
  const name = typeof maybeItem.name === "string" ? sanitizeText(maybeItem.name) : "";
  const price = typeof maybeItem.price === "string" ? sanitizeText(maybeItem.price) : "";
  const descriptionCandidate = maybeItem.description ?? maybeItem.body ?? maybeItem.text;
  const description = typeof descriptionCandidate === "string" ? sanitizeText(descriptionCandidate) : "";

  if (!name && !price && !description) {
    return null;
  }

  return { name, price, description };
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
  const serviceRows = getServiceItems(blocks)
    .map((item) => ({ label: buildServiceLabel(item), price: item.price }))
    .filter((item) => item.label.length > 0);

  if (!serviceRows.length) {
    return null;
  }

  return (
    <section className="specialist-page__section section" aria-label="Услуги и цены">
      <div id="services" className="specialist-section-anchor" aria-hidden="true" />
      <div className="container">
        <div className="section-card specialist-card specialist-content-card">
          <h2 className="section-title specialist-section-title">Услуги и цены</h2>
          <ul className="specialist-list" aria-label="Список услуг">
            {serviceRows.map((item, index) => (
              <li key={`${item.label}-${item.price}-${index}`} className="specialist-list__item specialist-list__item--service">
                <span>{item.label}</span>
                {item.price ? <span className="specialist-service__price">{item.price}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export default SectionServices;
