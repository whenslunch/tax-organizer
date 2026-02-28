---
title: "Tax Organizer Decision Log"
description: "Record of design and implementation decisions for the tax-organizer project"
ms.date: 2026-02-28
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
- **Context:** Some categories (Home Maintenance, Donations) have a variable number of documents — no fixed expected count.
- **Decision:** Categories with `"variableCount": true` in config are excluded from readiness tracking. They display a count badge ("N found") instead of "N / M."
- **Rationale:** Readiness percentage should reflect only categories where completeness can be meaningfully measured.
