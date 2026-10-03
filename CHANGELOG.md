# Changelog

All notable changes to Learn Signal are documented here.

## [1.1.0] - 2026-10-03

### Changed

- **No built-in data limits on your own computer.** The caps on file size (was 50 MB), rows (10,000 per sheet), columns (80), sheets (30), cells (250,000), unpacked workbook size, pasted text (1,000,000 characters), scenarios (30), options (12), studies (12), results per study (10), study-result rows (3,600), questions, answers and sources are gone. None was mathematically necessary: every calculation grows with options × scenarios × study results.
- Validation, EVSI, question values and the sensitivity check now group and vectorise instead of rescanning lists, so a 1,000-scenario model calculates in seconds.
- The upload cap is 10,000 MB in `.streamlit/config.toml`, both launchers (`LEARNSIGNAL_MAX_UPLOAD_MB`) and the Dockerfile.

### Added

- **Public demo caps** under `SIGNAL_PUBLIC=1`, all in `src/learnsignal/limits.py`, using the 1.0.0 values. Capped messages say it is a demo limit and that the downloaded app has none; the data page lists the caps.
- Running out of memory gives a plain message instead of a crash.
- Result tables longer than 50,000 rows show their first rows on screen with a note; exports keep every row.
- Long CSV cells beyond the csv module's 128 KB default are read.

## [1.0.0] - 2026-10-03

First public release.

### Added

- **Decision model:** 2–30 mutually exclusive scenarios with priors that must total 1, 2–12 options and a net payoff for every option in every scenario, in one stated unit and horizon. Unknown numbers stay blank; nothing is renormalised or filled in.
- **Value of information:** exact expected payoff and expected opportunity loss per option, EVPI, and for up to 12 studies (up to 10 results each, entered as P(result | scenario)) the EVSI, net value after study cost, preferred option after each result and Bayesian posteriors. Impossible results are reported, not divided by zero.
- **Questions:** the value of perfectly answering up to 20 questions that group scenarios, labelled as overlapping and non-additive.
- **Sensitivity:** one scenario's prior on a 0.025 grid, with best expected payoff, EVPI and where the preferred option switches.
- **Three ways in:** Excel or CSV upload with suggested, user-confirmed column matching (a simple decision table or the complete linked project workbook), manual entry, or a copy-and-paste AI prompt with the exact JSON schema. The app makes no AI or network calls.
- **Review gate:** results stay hidden until a named review is recorded; the review is tied to a SHA-256 fingerprint of the inputs and cleared by any edit.
- **Exports:** Excel workbook (re-importable), project JSON with the review record, printable HTML brief and evidence ZIP, with spreadsheet-formula neutralisation. Unreviewed projects export inputs without calculated values.
- Fictional lunch-service demo, already reviewed; Research & limits page with sources checked against Crossref.
- Upload cap of 50 MB (launchers, Dockerfile and `.streamlit/config.toml`), with row, column, sheet and cell limits explained as method limits.
- Signal Hub entry point `learnsignal.ui.render()` with `APP_INFO`, `learn:`-namespaced keys and Hub mode (no file writes, no network calls, opens on the fictional demo, project kept in session memory).
- Windows and macOS launchers (port 8601, `LEARNSIGNAL_PORT`, `LEARNSIGNAL_MAX_UPLOAD_MB`), Dockerfile, `AI_ANALYST.md`, data guide, methods and sources documentation.
