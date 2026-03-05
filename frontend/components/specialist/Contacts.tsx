const BASIC_EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type SpecialistContactsProps = {
  telegram?: string;
  whatsapp?: string;
  phone?: string;
  email?: string;
};

function normalizeValue(value?: string): string | null {
  if (!value) {
    return null;
  }

  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function isValidEmail(email?: string): email is string {
  const normalizedEmail = normalizeValue(email);
  return normalizedEmail ? BASIC_EMAIL_REGEX.test(normalizedEmail) : false;
}

export function Contacts({ telegram, whatsapp, phone, email }: SpecialistContactsProps) {
  const normalizedTelegram = normalizeValue(telegram);
  const normalizedWhatsapp = normalizeValue(whatsapp);
  const normalizedPhone = normalizeValue(phone);
  const normalizedEmail = isValidEmail(email) ? normalizeValue(email) : null;

  return (
    <div className="specialist-contacts" aria-label="Контакты специалиста">
      {normalizedTelegram ? <p>Telegram: {normalizedTelegram}</p> : null}
      {normalizedWhatsapp ? <p>WhatsApp: {normalizedWhatsapp}</p> : null}
      {normalizedPhone ? <p>Телефон: {normalizedPhone}</p> : null}
      {normalizedEmail ? <p>Email: {normalizedEmail}</p> : null}
    </div>
  );
}

export default Contacts;
