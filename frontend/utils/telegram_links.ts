const TELEGRAM_USERNAME_REGEX = /^[A-Za-z0-9_]+$/;
const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type ClientBotAction = "contact_specialist" | "book";

function normalizeBotUsername(username?: string): string | null {
  if (!username) {
    return null;
  }

  const normalized = username.trim();
  if (!normalized || normalized.startsWith("@")) {
    return null;
  }

  if (!TELEGRAM_USERNAME_REGEX.test(normalized)) {
    return null;
  }

  return normalized;
}

function normalizeSpecialistUuid(specialistUuid?: string): string | null {
  if (!specialistUuid) {
    return null;
  }

  const normalized = specialistUuid.trim();
  if (!normalized || !UUID_REGEX.test(normalized)) {
    return null;
  }

  return normalized;
}

export function buildClientBotLink(username?: string, action?: ClientBotAction, specialistUuid?: string): string | null {
  const normalizedUsername = normalizeBotUsername(username);
  if (!normalizedUsername) {
    return null;
  }

  if (!action) {
    return `https://t.me/${normalizedUsername}`;
  }

  const normalizedSpecialistUuid = normalizeSpecialistUuid(specialistUuid);
  const actionPayload = normalizedSpecialistUuid ? `${action}_${normalizedSpecialistUuid}` : action;
  const payload = encodeURIComponent(actionPayload);
  return `https://t.me/${normalizedUsername}?start=${payload}`;
}

// TODO: add unit tests for buildClientBotLink when frontend test runner is available.
