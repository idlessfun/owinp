# Changelog

All significant changes to the OWINP project.

The format is based on [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Planned
- GitHub token in settings
- Admin tool adaptation for per-language cards

## [0.2.0] — 2026-09-20

### Added
- **Multilingual support**: the app is now fully localized (RU + EN)
- **Translator system** based on JSON files (`app/locales/*.json`)
- **Language switcher** in Settings with auto-restart
- **Language folders** for program cards (`app/apps/<lang>/`)
- **Per-language cache** (`cache/apps/<lang>/`)
- **Catalog downloader** now fetches only the current language
- **Buttons of different types**: `download` / `link`
- **Interface color themes** (5 presets: dark-blue, dark-red, dark-green, dark-purple, light)
- **Extended settings page**: theme, font size, compact mode, auto-update, auto-run, screenshots
- **Theme support in dialogs** (download dialog, update dialog)
- **Cache migration** from the old flat structure to per-language folders
- **"Clear cache" button** on the main page
- **Throttling respects language changes** — updates immediately when the language is switched

### Fixed
- Crash when closing the download dialog
- Program icon not showing in the download dialog
- Double `emit` when updating the catalog
- Old flat cache files were not removed automatically

### Changed
- Code fully translated to English (docstrings, comments, logs)
- README updated for the new structure

## [0.1.1] — 2026-09-19

### Fixed
- Crash when closing the download dialog (`QThread` now terminates correctly)
- The program icon is now displayed in the download dialog (taken from the cache)
- Automatic cleanup of outdated files from the cache (deleted programs disappear from the catalog)
- Double `emit` when updating the catalog (the list was rebuilt twice)

### Added
- "🧹 Clear cache" button on the main page

## [0.1.0] — 2026-09-16

### Added
- Basic interface with dark theme
- Program catalog from JSON
- Program page (like in F-Droid)
- Search and filter by categories
- Built-in downloading with progress bar, speed, and cancellation
- "Open folder" and "Run" buttons after downloading
- Code auto-update via GitHub Releases
- Program catalog auto-update from GitHub
- Automatic downloading and caching of icons and screenshots
- Throttling of checks (no more than once an hour)
- "Check for updates" button on the main page
- Cache for offline work
- `downloads` array in JSON — support for multiple buttons (mirrors, portable)
- Extended settings
### Built
- **`.exe`** via **Nuitka** — no longer requires installing Python
- **Installer** via **Inno Setup** with Russian and English languages
- **Portable** version (`.zip` archive) — works without installation
- **Application icon** in all places (`.exe`, shortcuts, taskbar)
- **File metadata**: publisher OWINP, version 0.1.0
- **Launch without console** — the application looks like a regular Windows program

### Security
- Only HTTPS for all network requests
- Domain whitelist for downloading the catalog
- Sanitization of file names (protection against path traversal)
- JSON validation before use
- Checked on VirusTotal: 1/68 (false positive of the ML scanner)

### Documentation
- LICENSE (MIT)
- README.md with description and instructions
- CHANGELOG.md
- SECURITY.md