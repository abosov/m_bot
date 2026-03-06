const BASIC_EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type SpecialistContactsProps = {
  telegram?: string;
  whatsapp?: string;
  phone?: string;
  email?: string;
};

type ContactItem = {
  id: string;
  label: string;
  value: string;
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

  const contactItems: ContactItem[] = [
    normalizedTelegram ? { id: "telegram", label: "Telegram", value: normalizedTelegram } : null,
    normalizedWhatsapp ? { id: "whatsapp", label: "WhatsApp", value: normalizedWhatsapp } : null,
    normalizedPhone ? { id: "phone", label: "Телефон", value: normalizedPhone } : null,
    normalizedEmail ? { id: "email", label: "Email", value: normalizedEmail } : null,
  ].filter((item): item is ContactItem => Boolean(item));

  if (contactItems.length === 0) {
    return null;
  }

  return (
    <ul className="specialist-contacts" aria-label="Контакты специалиста">
      {contactItems.map((item) => (
        <li key={item.id} className="specialist-contacts__item">
          <span className="specialist-contacts__label">{item.label}</span>
          <span className="specialist-contacts__value">{item.value}</span>
        </li>
      ))}
    </ul>
  );
}

export default Contacts;
