---
title: "Tax Organizer Requirements"
description: "Functional and non-functional requirements for the tax-organizer project"
ms.date: 2026-02-28
---

# Tax Organizer Requirements

## Problem Statement

Tax-relevant documents are scattered across multiple OneDrive folders (Fidelity, DBS, Chase, employer docs, etc.). There is no consolidated view of what exists, what is missing, and whether the collection is complete for a given tax year. Manually tracking this across folders is tedious and error-prone.

## Goals

1. Provide a single-pane-of-glass web dashboard to view all tax-relevant documents for a given year
2. Scan configured OneDrive folders via Microsoft Graph API without moving files
3. Classify discovered documents by tax year and category
4. Check completeness against a user-defined checklist of expected documents
5. Generate clickable links that open documents directly in OneDrive
6. Serve as the discovery layer that feeds into `tax-data-compiler` for extraction (future)

## Functional Requirements

### FR-1: OneDrive Folder Scanning

- Scan user-configured OneDrive folder paths via Microsoft Graph API
- Retrieve file metadata: name, path, creation date, modified date, size, web URL
- Support recursive scanning within configured folders
- Handle pagination for large folders

### FR-2: Tax Year Classification

- Classify files into tax years using (in priority order):
  1. Filename patterns (e.g., `1099-DIV-2025.pdf`, `W2_2025.pdf`)
  2. Folder path patterns (e.g., `/Fidelity/2025/`)
  3. File creation or modified date as fallback
- Classification rules are configurable

### FR-3: Document Categorization

- Group documents by user-defined categories (e.g., Brokerage, Banking, Employment, Mortgage)
- Categories and their matching rules are defined in the config file
- Each document maps to exactly one category (or "Uncategorized")

### FR-4: Completeness Checking

- User defines a checklist of expected documents per tax year
- Each checklist item specifies: document name/pattern, source, category
- After scanning, compare found documents against the checklist
- Report status per item: found, missing, or multiple matches

### FR-5: Web Dashboard

- Single-page web app served from localhost
- Shows all discovered documents grouped by category
- Each document entry shows: filename, source folder, date, and clickable OneDrive link
- Readiness summary: total found vs. expected, with color-coded status
- Missing documents section highlighting gaps

### FR-6: Configuration

- Config file (JSON or YAML) specifies:
  - OneDrive folders to scan
  - Document categories and matching rules
  - Expected documents checklist
  - Target tax year
- Sample config provided with sensible defaults

## Non-Functional Requirements

### NFR-1: Privacy and Security

- Application runs entirely on localhost; no cloud hosting
- Files never leave OneDrive; only metadata is read via Graph API
- No telemetry or external data transmission
- Credentials stored locally in `.env`, excluded from version control
- Authentication uses Microsoft-standard OAuth flows (device code)

### NFR-2: Simplicity

- Minimal dependencies; avoid heavy frameworks
- Configuration via a single file (not a database)
- Clear error messages when config is wrong or auth fails

### NFR-3: Portability

- Runs on macOS (primary), Linux, and Windows
- Python virtual environments for Python components
- Lightweight Node.js tooling if needed for frontend

## Future Requirements (Deferred)

### FR-FUTURE-1: Tax Data Compiler Integration

- The dashboard triggers `tax-data-compiler` to extract data from found documents
- Documents stay in OneDrive; compiler accesses them via local OneDrive sync folder
- Extracted data feeds back into the dashboard or a separate report

### FR-FUTURE-2: Interactive Folder Browsing

- Browse OneDrive folders from the UI to select scan targets
- Replace or supplement the config file approach

### FR-FUTURE-3: Multi-Year Comparison

- View readiness across multiple tax years side by side

### FR-FUTURE-4: Mac Mini Home Server Hosting

- Run as a persistent service on a Mac Mini for household access
