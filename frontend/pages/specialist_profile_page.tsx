export type PublicSpecialistPagePayload = {
  profile: Record<string, unknown>;
  blocks: Array<Record<string, unknown>>;
  media: Array<Record<string, unknown>>;
  reviews: Array<Record<string, unknown>>;
};

export async function loadSpecialistProfilePage(slug: string): Promise<PublicSpecialistPagePayload> {
  const response = await fetch(`/api/public/specialists/${slug}`);

  if (!response.ok) {
    throw new Error(`Failed to load specialist profile page: ${response.status}`);
  }

  return (await response.json()) as PublicSpecialistPagePayload;
}
