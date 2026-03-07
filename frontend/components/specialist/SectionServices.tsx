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
  const serviceItems = getServiceItems(blocks);

  if (!serviceItems.length) {
    return null;
  }

  return (
    <section className="specialist-page__section section specialist-page__section--services" aria-label="Услуги и цены">
      <div id="services" className="specialist-section-anchor" aria-hidden="true" />
      <div className="container">
        <div className="section-card specialist-card specialist-content-card">
          <h2 className="section-title specialist-section-title">Услуги и цены</h2>
          <ul className="services-grid" aria-label="Карточки услуг">
            {serviceItems.map((item, index) => (
              <li key={`${item.name}-${item.price}-${index}`} className="service-card">
                {item.name ? <p className="service-title">{item.name}</p> : null}
                {item.price ? <p className="service-price">{item.price}</p> : null}
                {item.description ? <p className="service-description">{item.description}</p> : null}
                <div className="service-cta">
                  <a href="#booking" className="specialist-button specialist-button--primary">
                    Записаться
                  </a>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export default SectionServices;
