const TELEGRAM_USERNAME_REGEX = /^[A-Za-z0-9_]+$/;

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

export function buildClientBotLink(username?: string, action?: ClientBotAction): string | null {
  const normalizedUsername = normalizeBotUsername(username);
  if (!normalizedUsername) {
    return null;
  }

  if (!action) {
    return `https://t.me/${normalizedUsername}`;
  }

  const payload = encodeURIComponent(action);
  return `https://t.me/${normalizedUsername}?start=${payload}`;
}

// TODO: add unit tests for buildClientBotLink when frontend test runner is available.
