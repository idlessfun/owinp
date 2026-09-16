# OWINP — Open Windows Programs

> Каталог бесплатных open-source программ для Windows с удобным интерфейсом, встроенным скачиванием и без телеметрии.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Latest Release](https://img.shields.io/github/v/release/idlessfun/owinp)](https://github.com/idlessfun/owinp/releases/latest)
[![Telegram](https://img.shields.io/badge/Telegram-%232CA5E0.svg?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/+l5zeMXjfbXI0YzJi)

## 📥 Скачать

**Готовая версия для Windows** — не требует установки Python:

- 🖥 **[Установщик](https://github.com/idlessfun/owinp/releases/download/v0.1.0/OWINP-Setup-0.1.0.exe)** — обычная установка в систему (21.7 МБ)
- 📦 **[Portable](https://github.com/idlessfun/owinp/releases/download/v0.1.0/OWINP-Portable-0.1.0.zip)** — распаковать и запустить (29 МБ)

Обе версии — в разделе [**Releases**](https://github.com/idlessfun/owinp/releases/latest).

## ✨ Возможности

- 🎨 **Современный интерфейс** — тёмная тема, оформление в стиле F-Droid
- 📦 **Каталог программ** — карточки с описанием, характеристиками и скриншотами
- 🔍 **Поиск и фильтры** — мгновенный поиск по названию, описанию и тегам, фильтр по категориям
- ⬇️ **Встроенное скачивание** — прогресс-бар, скорость, отмена
- 🚀 **Быстрый запуск** — после скачивания можно сразу открыть папку или запустить установщик
- 🌐 **Автообновление каталога** — свежие программы без переустановки приложения
- 🔄 **Автообновление приложения** — уведомление о новых версиях через GitHub Releases
- 🛡️ **Без телеметрии** — приложение не отправляет никаких данных
- 🔓 **Open Source** — код открыт под лицензией MIT
- 📝 **Data-driven** — программы добавляются простым JSON-файлом, без правки кода

## 🚀 Установка

### Вариант 1 — Готовая сборка (рекомендуется)

1. Перейди в [**Releases**](https://github.com/idlessfun/owinp/releases/latest)
2. Скачай `OWINP-Setup-X.X.X.exe` (установщик) или `OWINP-Portable-X.X.X.zip` (portable)
3. Установи / распакуй и запусти `OWINP.exe`

**Системные требования:**
- Windows 10 или 11 (64-bit)
- ~200 МБ свободного места

### Вариант 2 — Из исходников

**Требования:**
- Windows 10 или 11 (64-bit)
- Python 3.12+

```bash
# Клонировать репозиторий
git clone https://github.com/idlessfun/owinp.git
cd owinp

# Создать виртуальное окружение
python -m venv .venv

# Активировать (Windows)
.venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Запустить
python main.py
```

## 🔒 Безопасность

Приложение проверено на **VirusTotal**:

- **Установщик**: 1/68 (только DeepInstinct — ложное срабатывание ML-сканера)
- **Portable**: 1/64 (только Elastic — ложное срабатывание ML-сканера)

**Kaspersky**, **DrWeb**, **Microsoft**, **ESET**, **BitDefender**, **Sophos**, **Symantec**, **Avast** — подтвердили чистоту.

### Что делает приложение в сети

OWINP **не собирает** и **не отправляет** никаких данных о вас. Никакой телеметрии, аналитики, трекинга.

Приложение делает **только два** типа сетевых запросов, и **оба — только к репозиторию на GitHub**:

1. **Проверка обновлений приложения** — раз в час запрашивает последнюю версию через GitHub Releases API.
2. **Обновление каталога программ** — раз в час скачивает свежие JSON-карточки и картинки с `raw.githubusercontent.com`.

Обе проверки:
- Используют **только HTTPS**.
- Работают **только** с доменами `api.github.com` и `raw.githubusercontent.com`.
- **Тихо** пропускаются, если нет интернета — приложение продолжает работать из кэша.

**Никаких** других запросов приложение не делает.

## 🗂 Формат JSON-карточки программы

Каждая программа в каталоге — это JSON-файл в `app/apps/`. Пример:

```json
{
    "id": "unique-id",
    "name": "Название программы",
    "developer": "Разработчик",
    "description": "Короткое описание для карточки в списке",
    "long_description": "Подробное описание для страницы программы",
    "version": "1.0.0",
    "release_date": "2026-01-01",
    "category": "Утилиты",
    "size_mb": 5.0,
    "license": "MIT",
    "website": "https://example.com",
    "downloads": [
        {
            "label": "Скачать",
            "url": "https://example.com/setup.exe",
            "primary": true
        }
    ],
    "icon": "example.png",
    "requirements": [
        "Windows 10 и выше"
    ],
    "features": [
        "Возможность 1",
        "Возможность 2"
    ],
    "screenshots": [],
    "is_portable": false,
    "is_open_source": true,
    "tags": ["тег1", "тег2"]
}
```

**Обязательные поля:** `id`, `name`, `description`, `version`, `category`, `size_mb`, `website`, `icon` и одно из: `downloads` (новый формат) или `download_url` (старый формат).

**Опциональные:** `developer`, `long_description`, `release_date`, `license`, `requirements`, `features`, `screenshots`, `is_portable`, `is_open_source`, `tags`.

> ### Как добавить программу
> **К огромному счастью, данный процесс облегчился, и это можно сделать просто через [телеграм-группу поддержки OWINP](https://t.me/+l5zeMXjfbXI0YzJi)!**
>
> Сначала разберёмся, как свою программу предложить выпустить через телеграм-группу поддержки OWINP.
> От вас требуется следующее:
>
> 1. Название программы
> 2. Описание программы
> 3. Скриншоты и иконка в формате PNG
> 4. Ссылка на скачивание
> 5. Ссылка на сайт
>
> После проверки вы получите короткий ответ на ваше сообщение.
## 🛠 Технологии

- [Python 3.12](https://www.python.org/)
- [PySide6](https://doc.qt.io/qtforpython/) — Qt6 для Python
- [Nuitka](https://nuitka.net/) — компиляция в `.exe`
- [Inno Setup](https://jrsoftware.org/isinfo.php) — создание установщика

## 📋 Планы

### Уже готово

- [x] Базовый интерфейс с тёмной темой
- [x] Каталог программ из JSON
- [x] Страница программы (как в F-Droid)
- [x] Поиск и фильтр по категориям
- [x] Встроенное скачивание с прогресс-баром
- [x] Открытие папки / запуск установщика после скачивания
- [x] Автообновление кода через GitHub Releases
- [x] Автообновление каталога программ
- [x] Кэширование иконок и скриншотов
- [x] Троттлинг проверок (не чаще 1 раза в час)
- [x] Сборка `.exe` и установщик (Portable + Setup)
- [x] Отдельная админ-программа для управления каталогом (`OWINP Admin`)
- [x] Расширенная кастомизация JSON-карточек
### В разработке

- [ ] Английская локализация интерфейса и кода
- [ ] Подготовка к переводу приложения на разные языки
- [ ] Раздел «Настройки» в приложении
- [ ] Исправление багов в приложении
- [ ] Создание сообществ в разных соц-сетях
- [ ] Собирание команды для будущего процветания проекта
- [ ] Приготовить тортик:)

## 🤝 Вклад

Pull requests приветствуются! Для крупных изменений сначала открой [issue](https://github.com/idlessfun/owinp/issues), чтобы обсудить, что и как.

**Как помочь проекту:**
- 🐛 Сообщить об ошибке — открой [issue](https://github.com/idlessfun/owinp/issues)
- 📦 Добавить программу в каталог — следуй инструкции «Как добавить программу» выше
- 💡 Предложить идею — открой issue с описанием
- ⭐ Поставить звезду на GitHub — помогает проекту стать заметнее

**Хотите по легче? Вариант есть**
- 🐛 Напишите просто в [телеграмм группу поддержки проекта OWINP](https://t.me/+l5zeMXjfbXI0YzJi),
и я обьязательно отвечу.
**Но, вопросы не по теме будут автоматически через время удалятся! По этому имейте ввиду.**
## 📜 Лицензия

[MIT](LICENSE) — свободно используйте, изменяйте и распространяйте.

## 🔗 Ссылки

- Репозиторий: https://github.com/idlessfun/owinp
- Последний релиз: https://github.com/idlessfun/owinp/releases/latest
- Сообщить об ошибке: https://github.com/idlessfun/owinp/issues
- Telegram группа поддержки OWINP: https://t.me/+l5zeMXjfbXI0YzJi
