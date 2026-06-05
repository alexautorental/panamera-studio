# Porsche Panamera — конфигуратор (цвет + тюнинг)

Отдельный интерактивный конфигуратор Porsche Panamera (поколение **972 / G3, MY2024+**):
цвет кузова **и** тюнинг на одном сайте. Открывается на телефоне без установки и логина,
билд сохраняется в ссылку и шлётся в Telegram.

> Этот проект **не трогает** готовый сайт цветов `panamera` — это отдельная папка и отдельный
> GitHub Pages репозиторий. Рендеры цветов **скопированы** внутрь (самодостаточно), чтобы изменения
> старого проекта не могли его сломать.

## 🔗 Ссылки

- **Конфигуратор (live):** https://alexautorental.github.io/panamera-studio/
- Сайт цветов (отдельный, не изменялся): https://alexautorental.github.io/panamera/
- Deep-link билда (пример): `…/panamera-studio/#c=pts-viper-green&v=front-left&l=day&wheelSize=wheel-21&wheelFinish=wf-satin-black&calipers=cal-black&carbon=carbon-mirrors,carbon-lip`

## Что внутри (разделы 1–17 ТЗ)

1. Цвет кузова — 81 реальный Porsche-рендер (16 factory exact + 65 PTS/popular).
2. Ракурс — front-left, side, rear-left, top, front, rear.
3. OEM+ Porsche — Tequipment / Exclusive Manufaktur опции с бейджем Official.
4. Диски — размер 19/20/21 + отделка (серебро / чёрный / сатин / diamond cut / бронза / forged).
5. Обвес / аэродинамика — Stock, SportDesign (official), карбон-сплиттер 976 (confirmed aftermarket), TechArt (971 legacy), Widebody (concept).
6. Карбон — зеркала / губа / пороги / диффузор / спойлер (под кузов «976» — confirmed aftermarket).
7. Blackout / dechrome — сток / чёрный пакет / сатин-плёнка.
8. Посадка / подвеска — сток / air low / занижение (971 legacy) / show (concept).
9. Суппорты — чёрный / красный / белый PSCB / жёлтый PCCB / серебро / кастом-цвета.
10. Выхлоп — сток / Porsche Sport Exhaust (official) / Akrapovič (971 legacy).
11. Салон — чёрный / беж / Bordeaux / brown / карбон / дерево / Race-Tex.
12. Плёнка PPF — gloss / matte / satin / stealth + ceramic coating.
13. Тонировка — нет / лёгкая / средняя / тёмная.
14. Аксессуары — бокс/дуги на крышу, коврики, видеорегистратор, детское кресло (Tequipment).
15. Пресеты — 14 готовых билдов (Clean OEM+, Black Executive, SportDesign, Carbon Pack, Yachting/Miami/Viper, TechArt/Mansory Inspired, VIP Dark, Winter Daily, Rental Durable, Showcar Widebody, Track Look).
16. Смета — ориентир бюджета (диапазон €) + метр уровня.
17. Share — весь билд в URL hash, кнопки «Поделиться» (нативный share) и «Copy build».

### Навороты
Before/After сплит-слайдер (сток ↔ твой билд) · день/ночь/студия · Random build 🎲 ·
фильтр по бюджету (≤ €/€€/€€€/€€€€) · фильтр по стилю (luxury/sport/stealth/showcar/practical) ·
бейджи Official / Tequipment / Exclusive / Aftermarket / Concept / Needs-verification ·
предупреждения по спорным опциям · мини-галерея 6 ракурсов · сохранение нескольких билдов (localStorage) ·
экспорт билда текстом.

## Как «рисуется» (честно)

- **Большое фото** = реальный Porsche-рендер выбранного цвета. На него честно накладываются только
  те эффекты, что не врут: **финиш плёнки** (gloss/matte/satin/stealth — CSS-аппроксимация) и
  **свет** (день/ночь/студия). Before/After показывает реальную смену цвета/финиша.
- **Физический тюнинг** (диски, обвес, карбон, посадка, суппорты, тонировка, салон) показан как
  **конфигуратор-чипы со схемами и бейджами** + список в смете + чипы-моды на фото. Это сделано
  намеренно: лучше честная схема, чем плохая фейковая «замазка». Где визуал слабый — отмечено в `QA.md`.
- **DALL-E / нейрогенерация НЕ использованы** как источник истины. Реальные имена/совместимость/ссылки — из `SOURCES.md`.

## Структура

```
public/
  index.html                       — конфигуратор (загружает 2 JSON)
  tuning-assets/data/colors.json   — 81 цвет (локальные пути к рендерам)
  tuning-assets/data/tuning-options.json — все опции, пресеты, тиры, бейджи
  tuning-assets/base/car|masks/    — base-рендеры + маски (для before/after и будущих оверлеев)
  tuning-assets/swatches/          — 81 swatch
  tuning-assets/overlays/…         — пусто: место для будущих оверлеев (wheels/bodykits/carbon/tint/interior)
  tuning-assets/generated/         — пусто: место для будущих concept-визуалов
  panamera_official_assets/        — СКОПИРОВАННЫЕ заводские рендеры (16 цветов × 6)
  panamera_google_assistant_assets/generated-renders/ — СКОПИРОВАННЫЕ PTS-рендеры (65 × 6)
README.md · SOURCES.md · QA.md · .github/workflows/pages.yml
```

## Обновить / задеплоить

```bash
git add -A && git commit -m "update" && git push   # GitHub Actions выложит public/ за ~30 сек
```

## Что НЕ делалось (намеренно)
- Не редактировались файлы проекта `panamera` (только чтение/копирование ассетов).
- Не обещается физическая совместимость без источника — см. бейджи и `QA.md`.
- Поколения 971 и 972 не смешиваются: legacy-детали 971 помечены явно.
