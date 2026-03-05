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

  const contactItems = [
    normalizedTelegram ? `Telegram: ${normalizedTelegram}` : null,
    normalizedWhatsapp ? `WhatsApp: ${normalizedWhatsapp}` : null,
    normalizedPhone ? `Телефон: ${normalizedPhone}` : null,
    normalizedEmail ? `Email: ${normalizedEmail}` : null,
  ].filter((item): item is string => Boolean(item));

  if (contactItems.length === 0) {
    return null;
  }

  return (
    <ul className="specialist-contacts" aria-label="Контакты специалиста">
      {contactItems.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export default Contacts;
