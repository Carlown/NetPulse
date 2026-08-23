# Changelog

## [1.1.7] - 2026-08-23

### Fixed

- Fixed marketplace index requests falling back to the offline cache when an expired GitHub token was present.
- Kept the cached GitHub login available for author-only marketplace actions after token cleanup.
- Synced the Settings page immediately after disabling automatic update checks from the update prompt.

### Verified

- English-mode UI smoke check passed with no visible Chinese text in the loaded application widgets.
- Dark-mode theme switching passed in the Qt offscreen regression check.
- Marketplace index fetch returned live entries instead of the local cache.

## [1.1.6] - 2026-08-22

### Fixed

- Fixed marketplace refreshes returning stale indexes immediately after a plugin publish.
- Fixed rapid marketplace refresh clicks duplicating plugin cards in the UI.
- Preserved registered plugin protocols when importing stress-test configurations.
- Clamped imported ports, thread counts, rate limits, and durations to supported ranges.
- Rejected malformed bracketed IPv6 host/port values in collaborative direct-connect mode.
- Reset relay mode state cleanly when a collaborative host session is shut down.
- Completed English labels in the built-in Test Environment plugin, including localized time-zone display.
- Updated the marketplace checksum for the corrected Test Environment plugin.

### Improved

- Refined tray-menu positioning so the complete menu remains visible near screen edges.
- Made plugin lists independently scrollable while keeping page controls visible.
- Improved plugin-market and report-menu animation compatibility with current QFluentWidgets versions.
- Updated installer metadata, documentation, and the displayed application version to `1.1.6`.

### Verification

- Python bytecode compilation passed for the application and marketplace plugins.
- Qt offscreen smoke startup passed for the main window and all primary views.
- English-mode UI smoke check found no visible Chinese text in the loaded application widgets.
