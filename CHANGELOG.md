# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [2.0.0] - 2026-03-28

### Changed
- Migrate to Checkmk 2.4 new plugin API (`cmk.rulesets.v1`) — compatible with Checkmk 2.3+
- Rewrite notification script as `notifications/telegram` (no extension) using `subprocess`/`curl` instead of Python HTTP libraries

### Added
- SOCKS5 proxy support via curl `--proxy socks5h://` with separate `--proxy-user` argument
- Password store integration using `utils.get_password_from_env_or_context()` for bot token and proxy credentials

## [1.4.2] - 2022-03-16

### Fixed
- Crash when notification body exceeds 4096 characters (Telegram API message length limit)
- `AttributeError: _parsed` for `TelegramMessage` class

## [1.4.1] - 2022-01-27

### Fixed
- Bot token only available on first invocation; subsequent notifications failed
- Wrong import of `Union` type
- Remove unused imports from parameter spec

## [1.4.0] - 2021-07-22

### Added
- Configurable notification message template
- Store bot token in Checkmk password store

### Changed
- Use Checkmk built-in `utils` module instead of custom helpers

## [1.3.0] - 2021-05-31

### Added
- Packaging script (`package.sh`) to build `.mkp` archive
- HTML special character sanitation in notification context

### Changed
- Move graph rendering into the plugin (removes dependency on Checkmk internals)

## [1.0.0] - 2020-11-29

### Added
- Optional performance graph sending
- Configurable graph send conditions
- Notification status calculation (OK/WARN/CRIT/UNKNOWN)
- Class-based notifier architecture

## [0.1.0] - 2020-07-30

### Added
- Initial release with Checkmk 2.0 compatibility
- URL prefix support in notification message headers
