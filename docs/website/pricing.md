# Pricing page

## Pricing page structure

Каждая карточка тарифа содержит:

1. `tariff_name`
2. `price`
3. `price_unit`
4. `subtitle`
5. `description`
6. `features`
7. `action_button`

Это необходимо для консистентности UI.

## UX polish rules

- У каждой карточки есть фиксированный `pricing-badge-slot` (слот всегда занимает место, бейдж виден только у Pro).
- Карточка построена как `flex`-колонка, а блок `pricing-action` всегда прижат вниз (`margin-top: auto`).
- Адаптивная сетка тарифов:
  - desktop: 4 колонки;
  - `<= 1024px`: 2 колонки;
  - `<= 640px`: 1 колонка.
- Для `pricing-description` на десктопе включён clamp до 3 строк, на мобильном clamp отключается.
