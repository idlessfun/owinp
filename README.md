# OWINP — Open Windows Programs

> Catalog of free open-source programs for Windows with a convenient interface, built-in downloading, and no telemetry.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Latest Release](https://img.shields.io/github/v/release/idlessfun/owinp)](https://github.com/idlessfun/owinp/releases/latest)
[![Telegram](https://img.shields.io/badge/Telegram-%232CA5E0.svg?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/+l5zeMXjfbXI0YzJi)

## 📥 Download

**Ready-made version for Windows** — no need to install Python:

- 🖥 **[Installer](https://github.com/idlessfun/owinp/releases/download/v0.1.0/OWINP-Setup-0.1.0.exe)** — regular installation into the system (21.7 MB)
- 📦 **[Portable](https://github.com/idlessfun/owinp/releases/download/v0.1.0/OWINP-Portable-0.1.0.zip)** — unpack and run (29 MB)

Both versions are in the [**Releases**](https://github.com/idlessfun/owinp/releases/latest) section.

## ✨ Features

- 🎨 **Modern interface** — dark theme, F-Droid style design
- 📦 **Program catalog** — cards with description, characteristics, and screenshots
- 🔍 **Search and filters** — instant search by name, description, and tags, filter by categories
- ⬇️ **Built-in downloading** — progress bar, speed, cancellation
- 🚀 **Quick launch** — after downloading, you can immediately open the folder or run the installer
- 🌐 **Catalog auto-update** — fresh programs without reinstalling the application
- 🔄 **Application auto-update** — notification about new versions via GitHub Releases
- 🛡️ **No telemetry** — the application does not send any data
- 🔓 **Open Source** — code is open under the MIT license
- 📝 **Data-driven** — programs are added with a simple JSON file, without editing code

## 🚀 Installation

### Option 1 — Ready-made build (recommended)

1. Go to [**Releases**](https://github.com/idlessfun/owinp/releases/latest)
2. Download `OWINP-Setup-X.X.X.exe` (installer) or `OWINP-Portable-X.X.X.zip` (portable)
3. Install / unpack and run `OWINP.exe`

**System requirements:**
- Windows 10 or 11 (64-bit)
- ~200 MB of free space

### Option 2 — From source

**Requirements:**
- Windows 10 or 11 (64-bit)
- Python 3.12+

```bash
# Clone the repository
git clone https://github.com/idlessfun/owinp.git
cd owinp

# Create a virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## 🔒 Security

The application has been checked on **VirusTotal**:

- **Installer**: 1/68 (only DeepInstinct — false positive of the ML scanner)
- **Portable**: 1/64 (only Elastic — false positive of the ML scanner)

**Kaspersky**, **DrWeb**, **Microsoft**, **ESET**, **BitDefender**, **Sophos**, **Symantec**, **Avast** — confirmed cleanliness.

### What the application does on the network

OWINP **does not collect** and **does not send** any data about you. No telemetry, analytics, tracking.

The application makes **only two** types of network requests, and **both — only to the repository on GitHub**:

1. **Application update check** — once an hour requests the latest version via the GitHub Releases API.
2. **Program catalog update** — once an hour downloads fresh JSON cards and images from `raw.githubusercontent.com`.

Both checks:
- Use **only HTTPS**.
- Work **only** with the domains `api.github.com` and `raw.githubusercontent.com`.
- Are **silently** skipped if there is no internet — the application continues to work from the cache.

The application makes **no** other requests.

## 🗂 JSON program card format

Each program in the catalog is a JSON file in `app/apps/`. Example:

```json
{
    "id": "unique-id",
    "name": "Program name",
    "developer": "Developer",
    "description": "Short description for the card in the list",
    "long_description": "Detailed description for the program page",
    "version": "1.0.0",
    "release_date": "2026-01-01",
    "category": "Utilities",
    "size_mb": 5.0,
    "license": "MIT",
    "website": "https://example.com",
    "downloads": [
        {
            "label": "Download",
            "url": "https://example.com/setup.exe",
            "primary": true
        }
    ],
    "icon": "example.png",
    "requirements": [
        "Windows 10 and above"
    ],
    "features": [
        "Feature 1",
        "Feature 2"
    ],
    "screenshots": [],
    "is_portable": false,
    "is_open_source": true,
    "tags": ["tag1", "tag2"]
}
```

**Required fields:** `id`, `name`, `description`, `version`, `category`, `size_mb`, `website`, `icon` and one of: `downloads` (new format) or `download_url` (old format).

**Optional:** `developer`, `long_description`, `release_date`, `license`, `requirements`, `features`, `screenshots`, `is_portable`, `is_open_source`, `tags`.

> ### How to add a program
> **To great happiness, this process has become easier, and you can do it simply through the [OWINP support Telegram group](https://t.me/+l5zeMXjfbXI0YzJi)!**
>
> First, let's figure out how to propose your program for release through the OWINP support group.
> The following is required from you:
>
> 1. Program name
> 2. Program description
> 3. Screenshots and icon in PNG format
> 4. Download link
> 5. Website link
>
> After verification, you will receive a short reply to your message.
## 🛠 Technologies

- [Python 3.12](https://www.python.org/)
- [PySide6](https://doc.qt.io/qtforpython/) — Qt6 for Python
- [Nuitka](https://nuitka.net/) — compilation into `.exe`
- [Inno Setup](https://jrsoftware.org/isinfo.php) — creating the installer

## 📋 Plans

### Already done

- [x] Basic interface with dark theme
- [x] Program catalog from JSON
- [x] Program page (like in F-Droid)
- [x] Search and filter by categories
- [x] Built-in downloading with progress bar
- [x] Opening folder / running installer after downloading
- [x] Code auto-update via GitHub Releases
- [x] Program catalog auto-update
- [x] Caching of icons and screenshots
- [x] Throttling of checks (no more than once an hour)
- [x] Building `.exe` and installer (Portable + Setup)
- [x] Separate admin program for managing the catalog (`OWINP Admin`)
- [x] Extended customization of JSON cards
- [x] "Settings" section in the application
- [x] Fixing bugs in the application
### In development

- [ ] English localization of the interface and code
- [ ] Preparation for translating the application into different languages
- [ ] Creating communities in different social networks
- [ ] Gathering a team for the future prosperity of the project
- [ ] Prepare a cake:)

## 🤝 Contribution

Pull requests are welcome! For major changes, first open an [issue](https://github.com/idlessfun/owinp/issues) to discuss what and how.

**How to help the project:**
- 🐛 Report a bug — open an [issue](https://github.com/idlessfun/owinp/issues)
- 📦 Add a program to the catalog — follow the "How to add a program" instruction above
- 💡 Suggest an idea — open an issue with a description
- ⭐ Star the project on GitHub — helps the project become more visible

**Want an easier way? There is an option**
- 🐛 Just write to the [OWINP project support Telegram group](https://t.me/+l5zeMXjfbXI0YzJi),
and I will definitely reply.
**But, off-topic questions will be automatically deleted after a while! So keep that in mind.**
## 📜 License

[MIT](LICENSE) — freely use, modify, and distribute.

## 🔗 Links

- Repository: https://github.com/idlessfun/owinp
- Latest release: https://github.com/idlessfun/owinp/releases/latest
- Report a bug: https://github.com/idlessfun/owinp/issues
- OWINP support Telegram group: https://t.me/+l5zeMXjfbXI0YzJi