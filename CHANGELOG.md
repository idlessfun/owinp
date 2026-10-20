# Changelog

All significant changes to the OWINP project.

The format is based on [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Planned
- GitHub token in settings
- Admin tool adaptation for per-language cards

## [0.3.1] — 2026-10-20

### Added
- True portable mode: a `portable.flag` next to `OWINP.exe` keeps settings and cache in `OWINP-data`, with an `%APPDATA%\OWINP` fallback if that folder is read-only
- Reproducible release build script for Nuitka, the portable ZIP and the Inno Setup installer

### Security
- Catalog JSON and images are fetched only from `api.github.com` / `raw.githubusercontent.com`; every redirect is re-checked against that allowlist
- Application update requests are restricted to `api.github.com` and reject redirects outside that host
- GitHub API and catalog responses are size-limited
- Asset names are validated against Windows-specific unsafe names (drive-relative names, reserved device names, trailing dots/spaces) and must stay inside the cache
- Downloads re-check HTTPS on every redirect, enforce a size limit, detect truncated transfers, and verify an optional SHA-256 checksum from the catalog
- Links in release notes are opened only through the http(s)-only sanitizer
- The download dialog cancels on `Esc` instead of hiding a still-running download; auto-run is skipped while the dialog is closing

### Fixed
- Update dialog no longer crashes on `null` release fields returned by GitHub
- Closing the main window cancels update/catalog workers immediately instead of waiting for their timeouts
- Download progress uses 64-bit integers and no longer overflows on files larger than 2 GB
- The English cache is used as a fallback even when the current-language cache folder is absent
- Screenshots fit the program page at the minimum window size
- Catalog data: 7-Zip 26.03 links and duplicate primary button, Vesktop EN/RU metadata, VLC Yandex mirror, ISO release date
- Installer documentation now matches the per-machine installation into `Program Files`

## [0.3.0] — 2026-10-19

### Added
- Animated startup splash (ring, icon, progress) with a setting: always / first launch / never
- Smooth UI animations: window fade-in, page transitions, card cascade, expandable update banner, smooth download progress
- "Low-end PC mode" — one switch that disables every animation, including the splash
- Instant language switch (RU/EN) without restarting the application
- Window size and position are remembered between launches
- Hotkeys: `Ctrl+F` — search, `Esc` — back from a program page, `F5` — refresh catalog
- Dark-themed scrollbars and checkboxes

### Changed
- Search input is debounced (150 ms) instead of rebuilding the list on every key
- Catalog JSON and images are written atomically (temporary file + rename)
- Icons/screenshots are revalidated with conditional HTTP requests instead of being downloaded every hour
- Compact mode now actually changes card size
- Settings file is written atomically

### Fixed
- Crash on exit and overlapping update/catalog checks (a running `QThread` was destroyed)
- The program list is rebuilt automatically after a background catalog update
- Cache cleanup no longer deletes icons/screenshots that are still referenced by cards
- "Clear cache" now resets the catalog update throttle instead of waiting an hour
- A broken remote JSON can no longer overwrite a valid cached card
- Path traversal through `icon` / `screenshots` names from catalog JSON
- Invalid cards (non-object JSON, missing `id`/`name`) are skipped instead of crashing the list
- Details page now starts at the top; an empty "Screenshots" section is not shown
- Closing the download dialog no longer freezes the UI or crashes the process
- Version comparison handles `v` prefixes and pre-release tags (`1.0.0-beta`)
- Update check no longer fails on Windows consoles with cp1251/cp866 code pages
- First run now really detects the system language (the auto-detect branch was unreachable)
- Language switch is applied immediately by rebuilding the UI, without a process restart
- Installer requests administrator rights for the per-machine installation into `Program Files` and registers an uninstall entry
- Settings and catalog JSON saved with a UTF-8 BOM are read correctly
- External links are restricted to `http`/`https`

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