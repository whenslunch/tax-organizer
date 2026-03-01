---
title: "Tax Organizer Requirements"
description: "Functional and non-functional requirements for the tax-organizer project"
ms.date: 2026-02-28
---

## Problem Statement

Tax-relevant documents are scattered across multiple OneDrive folders (Fidelity, DBS, Telus, Fortis, BCHydro, etc.). There is no consolidated view of what exists, what is missing, and whether the collection is complete for a given tax year. Manually tracking this across folders is tedious and error-prone.

## Goals

1. Provide a single-pane-of-glass web dashboard to view all tax-relevant documents for a given year
2. Scan configured OneDrive folders via Microsoft Graph API without moving files
3. Match discovered documents against expected patterns using glob-style matching
4. Check completeness against a user-defined checklist of expected documents
5. Generate clickable links that open documents directly in OneDrive
6. Serve as the discovery layer that feeds into `tax-data-compiler` for extraction (future)

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Static mockup | Done | Dark/light/random themes, 12 categories |
| MSAL device code auth | Done | Personal accounts, token caching |
| OneDrive scanner | Done | Graph API metadata scanning |
| Flask backend | Done | 4 API endpoints, serves dashboard |
| Config system | Done | JSON config with `{year}` placeholders |
| Live scan integration | Done | Dashboard calls `/api/scan` |
| Config population | 9/12 | See categories below |

### Category Configuration Status

| Category | Config Status | Scan Verified |
|----------|--------------|---------------|
| DBS-TzeLin | Done | 12/12 |
| DBS-MayAnne | Done | 12/12 |
| Fidelity | Done | 11/11 |
| UOB | Placeholder | Not tested |
| Fortis | Done | 7 found (variable) |
| BCHydro | Done | 5 found (variable) |
| Water & Sewer | Done | 1/1 |
| PropertyTax | Done | 1/1 |
| Telecommunications | Done | Blocked on OneDrive sync |
| Home Insurance | Done | 4/4 (2 folders) |
| Home Maintenance | Placeholder | Variable count |
| Donations | Placeholder | Variable count |

## Functional Requirements

### FR-1: OneDrive Folder Scanning

- Scan user-configured OneDrive folder paths via Microsoft Graph API
- Retrieve file metadata: name, path, creation date, modified date, size, web URL
- Support pagination for large folders (200 items per page)
- Filter files by tax year using filename patterns or lastModifiedDateTime

### FR-2: Tax Year Classification

- Classify files into tax years using (in priority order):
  1. Filename patterns (e.g., `Fidelity-202501.pdf`, `TELUS-*-2025-01-01.pdf`)
  2. File modified date (same year or Jan-Mar of next year)
- Year placeholders (`{year}`, `{yy}`) in config are substituted at scan time

### FR-3: Document Categorization

- Group documents by user-defined categories (12 categories configured)
- Categories and their matching rules (glob patterns) defined in config file
- Each expected document uses `fnmatch`-style patterns with `|` for alternatives
- Variable-count categories (`variableCount: true`) list all found files without expected tracking

### FR-4: Completeness Checking

- User defines expected documents per category with glob patterns
- After scanning, compare found files against expected patterns
- Report status per item: found, missing, or extra (unmatched)
- Variable-count categories excluded from readiness percentage

### FR-5: Web Dashboard

- Single-page web app served from localhost (port 8091)
- Dark/light/random theme switcher (15 random themes)
- Shows documents grouped by category with summary cards
- Readiness progress bar with percentage
- Each found document shows: filename, folder, date, size, and clickable OneDrive link
- Missing documents highlighted in sidebar
- OneDrive login popup button

### FR-6: Configuration

- JSON config file (`config/config.json`) specifies:
  - `taxYear`: target year (integer)
  - `categories`: array of category objects with `id`, `name`, `icon`, `folders`, `expected`
  - Each expected doc has `name` (display) and `pattern` (fnmatch glob, `|`-separated)
  - `variableCount: true` for categories without fixed expected counts
- `{year}` and `{yy}` placeholders in folder paths and patterns for year portability
- Sample config at `config/config.example.json` with generic examples
- Real config is gitignored

### FR-7: Authentication

- MSAL device code flow for Microsoft Graph API
- Public client app registered for personal Microsoft accounts
- Persistent token cache (`.msal_cache`) with silent token refresh
- Logout endpoint clears cached tokens

### FR-8: API Endpoints

- `GET /` — serves dashboard HTML
- `GET /api/scan` — triggers OneDrive scan, returns structured JSON result
- `GET /api/browse?path=` — browse OneDrive folder tree (for interactive folder discovery)
- `GET /api/config` — returns current config (without secrets)
- `POST /api/logout` — clears MSAL token cache

## Non-Functional Requirements

### NFR-1: Privacy and Security

- Application runs entirely on localhost; no cloud hosting
- Files never leave OneDrive; only metadata is read via Graph API
- No telemetry or external data transmission
- Credentials stored locally in `.env`, excluded from version control
- Authentication uses Microsoft-standard OAuth flows (device code)
- Graph API scope limited to `Files.Read` (read-only)

### NFR-2: Simplicity

- Minimal dependencies: Flask, MSAL, requests, python-dotenv
- Configuration via a single JSON file (not a database)
- Clear error messages when config is wrong or auth fails
- Vanilla JS frontend — no build step, no frameworks

### NFR-3: Portability

- Runs on macOS (primary), Linux, and Windows
- Python virtual environment (`.venv`) for isolation
- `requirements.txt` with pinned versions for reproducibility

## Future Requirements (Deferred)

### FR-FUTURE-1: Auto-Classification Scanner (Netflix Model)

- Instead of per-category folder paths, recursively scan from broad roots (e.g., `Documents/`)
- Auto-classify files using filename keyword patterns
- Infer completeness from date patterns in filenames
- Surface unclassified files for user triage
- Config reduces to classification rules + scan roots
- Trade-off: slower scanning vs. zero folder configuration

### FR-FUTURE-2: Tax Data Compiler Integration

- The dashboard triggers `tax-data-compiler` to extract data from found documents
- Documents stay in OneDrive; compiler accesses them via local OneDrive sync folder
- Extracted data feeds back into the dashboard or a separate report

### FR-FUTURE-3: Interactive Folder Browsing

- Browse OneDrive folders from the UI to select scan targets
- Replace or supplement the config file approach
- `/api/browse` endpoint already supports this

### FR-FUTURE-4: Multi-Year Comparison

- View readiness across multiple tax years side by side

### FR-FUTURE-5: Mac Mini Home Server Hosting

- Run as a persistent service on a Mac Mini for household access
