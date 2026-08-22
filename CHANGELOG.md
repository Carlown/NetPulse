# Changelog

## [1.1.6] - 2026-08-22

### Fixed

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
