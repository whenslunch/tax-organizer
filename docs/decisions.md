---
title: "Tax Organizer Decision Log"
description: "Record of design and implementation decisions for the tax-organizer project"
ms.date: 2026-02-28
ms.topic: reference
---

# Decision Log

## DEC-001: Local SPA Architecture

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Needed to decide between a hosted web app vs. local-only app for viewing tax documents.
- **Decision:** Local SPA served from localhost. No cloud hosting.
- **Rationale:** Tax documents are sensitive. Running locally eliminates data exfiltration risk, avoids hosting costs, and simplifies auth. A Mac Mini can serve it on the home network later if needed.

## DEC-002: Config File for Folder Paths

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Needed to decide how users specify which OneDrive folders to scan.
- **Decision:** JSON config file listing folder paths, categories, and expected documents.
- **Rationale:** Simplest approach to start. Interactive folder browsing deferred to a future iteration. Config file is version-controllable and easy to share across machines.

## DEC-003: User-Defined Completeness Checklist

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** The "readiness check" requires knowing what documents are expected.
- **Decision:** User defines the full checklist in the config file. No hardcoded assumptions about tax jurisdiction or document types.
- **Rationale:** Tax situations vary widely (US, Singapore, dual-filing). The user knows best what constitutes "complete." This keeps the tool jurisdiction-agnostic.

## DEC-004: Files Never Leave OneDrive

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Needed to decide whether to download files for processing or keep them in place.
- **Decision:** The organizer only reads metadata via Graph API and generates OneDrive web links. Files are never downloaded or copied to a non-OneDrive location. For future `tax-data-compiler` integration, the compiler will access files through the local OneDrive sync folder (which is already on the filesystem).
- **Rationale:** Privacy and security. OneDrive sync provides local file access without creating additional copies. The organizer's job is discovery then indexing, not data handling.

## DEC-005: Static Mockup Before Implementation

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Before building the real app, need to validate the UX.
- **Decision:** Build a static HTML/CSS mockup with realistic sample data. No API calls, no backend. Review and iterate on the design before writing application code.
- **Rationale:** Cheaper to change HTML than to refactor a full application. Ensures alignment on the dashboard layout, information hierarchy, and interaction patterns.

## DEC-006: Python Virtual Environments Required

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** User preference for environment isolation.
- **Decision:** All Python work uses `.venv` virtual environments. Dependencies managed via `requirements.txt` or `pyproject.toml`.
- **Rationale:** Prevents polluting the system Python. Standard practice for reproducible builds.

## DEC-007: Lightweight Frontend Tooling

- **Date:** 2026-02-28
- **Status:** Pending (recommendation below)
- **Context:** The frontend is a single-page dashboard. Need to choose between heavy frameworks (React, Vue) and lighter approaches.
- **Decision:** For the mockup, plain HTML/CSS/vanilla JS. For the real app, recommend one of:
  - **Vanilla JS + fetch**: Zero dependencies, full control. Best for a simple dashboard.
  - **Alpine.js** (~15 KB): Reactive behavior without a build step. Good if we want dynamic filtering/sorting without a bundler.
  - **Preact** (~3 KB): React API in a tiny package, if component architecture is needed later.
- **Recommendation:** Start with vanilla JS. Add Alpine.js only if interactivity demands grow.
- **Rationale:** The dashboard is primarily a read-only display of scanned results. Heavy frameworks add build complexity without proportional benefit.

## DEC-008: MSAL Device Code Flow for Authentication

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Need to authenticate with Microsoft Graph API to read OneDrive files. Options include authorization code flow (requires redirect URI), device code flow (no redirect needed), or client credentials (app-only, no user context).
- **Decision:** Use MSAL device code flow with a public client application registered for personal Microsoft accounts.
- **Rationale:** Device code flow requires no redirect URI, no client secret, and works from a localhost CLI/server. Tokens are cached locally in `.msal_cache` and auto-refresh silently.

## DEC-009: Flask as Backend Server

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Need a lightweight server to serve the dashboard and proxy Graph API calls. Options included Flask, FastAPI, or a bare `http.server`.
- **Decision:** Flask with four endpoints: `GET /` (dashboard), `GET /api/scan` (scan OneDrive), `GET /api/browse` (folder browser), `POST /api/logout` (clear tokens).
- **Rationale:** Flask is minimal, no async complexity needed for this use case, and pairs well with MSAL's synchronous token acquisition.

## DEC-010: Variable-Count Categories

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Some categories (Home Maintenance, Donations, Fortis, BCHydro) have a variable number of documents — no fixed expected count.
- **Decision:** Categories with `"variableCount": true` in config are excluded from readiness tracking. They display a count badge ("N found") instead of "N / M."
- **Rationale:** Readiness percentage should reflect only categories where completeness can be meaningfully measured.

## DEC-011: Year Placeholder System

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Config file had hardcoded `2025` in folder paths and filename patterns. Updating the tax year would require editing dozens of strings.
- **Decision:** Support `{year}` (4-digit) and `{yy}` (2-digit) placeholders in folder paths and expected-document patterns. The `_sub_year()` function substitutes them at scan time using the `taxYear` value from config.
- **Rationale:** Change one number in config (`"taxYear": 2026`) and all paths and patterns update automatically. Makes the config reusable across years.

## DEC-012: Multi-Folder Categories

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Some categories span multiple OneDrive folders. Home Insurance has files in both `{year} Home - Cooperators/` and `{year} Strata - Family/` under the same parent.
- **Decision:** The `folders` array in each category accepts multiple paths. The scanner aggregates files from all listed folders before matching against expected patterns.
- **Rationale:** Avoids duplicating categories just because files live in different subfolders. One category, one readiness check, multiple sources.

## DEC-013: OneDrive Login as Popup Window

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Users need to sign in to OneDrive to ensure files sync before scanning. A navigation link would leave the dashboard.
- **Decision:** OneDrive login opens in a popup window (500x700) rather than navigating the main page.
- **Rationale:** Keeps the dashboard visible while the user signs in. Better UX than losing context.

## DEC-014: Future Direction — Auto-Classification (Netflix Model)

- **Date:** 2026-02-28
- **Status:** Proposed
- **Context:** Current approach requires configuring per-category folder paths and filename patterns. User observed this is the opposite of how Netflix works — you don't choose where movies are stored, you just search.
- **Decision:** Explore a future "auto-classify" mode where the scanner recursively scans broad roots (e.g., `Documents/`) and classifies files by keyword patterns in filenames, without needing folder paths.
- **Trade-offs:**
  - Slower: recursive Graph API scanning vs. targeted folder reads
  - Mitigations: caching, Graph API delta queries for change tracking, background scanning
  - Config simplifies to classification rules + scan roots instead of per-category folder paths
- **Rationale:** Would dramatically simplify onboarding. Current folder-based approach works but requires manual configuration for each category. Auto-classification inverts the model: define what you're looking for, not where it lives.

## DEC-015: Subprocess Integration for Tax Data Compiler

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** The `tax-data-compiler` repo contains an `EquityExtractor` class that parses DBS Wealth Management PDF statements and produces CSV + HTML reports. We need to invoke this from tax-organizer to display extracted data in the dashboard. Two options were evaluated: (A) import the class directly as a Python module, or (B) call the script via subprocess and read its output files.
- **Decision:** Use subprocess invocation (Option B). The tax-organizer API endpoint runs `python ../tax-data-compiler/tax_compiler.py --folder <path> --output <path>`, waits for completion, then reads the resulting CSV to return structured JSON.
- **Rationale:** Subprocess keeps the two repos fully independent. Each maintains its own virtual environment, dependencies (PyMuPDF is only needed in tax-data-compiler), and release cycle. A change in the compiler's internals does not break tax-organizer as long as the CSV output schema stays stable. The code is immediately readable: "call external script, read its output." The alternative (direct import) would require `sys.path` manipulation, shared dependency installation, and tighter coupling between projects.

## DEC-016: Spreadsheet Display with Vanilla HTML Tables

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** Extracted DBS data (equity holdings, dividends, cash/interest) needs a spreadsheet-like display in the dashboard. Options considered: (A) vanilla HTML `<table>` with CSS for sticky headers, (B) Tabulator.js (~50 KB), (C) AG Grid.
- **Decision:** Use vanilla HTML tables styled with CSS sticky columns/headers. No external table library.
- **Rationale:** Consistent with the existing no-framework frontend (DEC-007). The data is read-only with a fixed structure (12 month columns), so sorting/filtering features from a library add no value. Vanilla tables are easier to maintain, require no build step, and keep the dashboard dependency-free.

## DEC-017: Per-Category Local Sync Path in Config

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** The tax-data-compiler reads PDFs from local disk (OneDrive sync folder), not via Graph API. To invoke it for different account holders, the API needs to know where each category's PDFs are on the local filesystem.
- **Decision:** Add an optional `localSyncPath` field to category objects in `config.json`. This points to the OneDrive sync folder on disk (e.g., `~/OneDrive/Documents/Banking & Finance/DBS/TzeLin/`). Only categories with this field can use the compile endpoint.
- **Rationale:** Minimal config change. Aligns with DEC-004 (files stay in OneDrive; compiler reads from the sync folder). The field is optional, so existing categories without local sync paths are unaffected.

## DEC-018: Separate Compilation Per Account Holder

- **Date:** 2026-02-28
- **Status:** Accepted
- **Context:** DBS statements exist for two account holders (Tze Lin and May Anne). Each has a separate folder of monthly PDFs. Data should be viewed independently.
- **Decision:** The compile API endpoint runs separately for each category ID (`dbs-tzelin`, `dbs-mayanne`). The dashboard provides a tab or selector to switch between them. Output goes to per-category subfolders (e.g., `output/dbs-tzelin/`, `output/dbs-mayanne/`) so results do not overwrite each other.
- **Rationale:** Account holders have different securities, dividend sources, and cash positions. Merging them would be misleading. Separate runs also allow independent re-compilation if one set of PDFs changes.
