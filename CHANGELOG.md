# Changelog

All significant changes to the OWINP project.

The format is based on [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Planned
- Buttons of different types (download / open link)
- Interface color palette
- "Settings" section in the application
- GitHub token in settings
- English localization of the interface and code

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