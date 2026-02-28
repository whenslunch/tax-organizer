---
description: "Required working instructions for Copilot when contributing to tax-organizer"
applyTo: '**'
---

# Copilot Working Instructions

## Documentation Requirements

Every meaningful work session must produce or update documentation artifacts:

- Update `docs/requirements.md` when requirements change or are clarified
- Append to `docs/decisions.md` when a design or implementation decision is made
- Make git commits at logical checkpoints to preserve context for future sessions
- Commit messages follow Conventional Commits (see `commit-message.instructions.md`)

## Development Environment

- Use Python virtual environments (`.venv`) for all Python work
- For Node.js/frontend, prefer lightweight tooling (no heavy frameworks unless justified)
- Keep dependencies minimal; document why each dependency exists

## Security and Privacy

- Tax documents never leave OneDrive; the app only reads metadata and generates links
- No telemetry, no external API calls except Microsoft Graph API
- Credentials and tokens stay local; use `.env` files excluded from git
- Never log or display file contents, only metadata (name, path, dates, size)

## Architecture Principles

- Local-first: the app runs on localhost, no cloud hosting required
- Config-driven: folder paths and checklists come from user-editable config files
- Read-only: Graph API access is read-only; files are never moved, copied, or modified
- Modular: scanner, classifier, checker, and reporter are separate concerns

## Git Workflow

- Commit after completing each logical unit of work
- Use descriptive commit messages following Conventional Commits format
- Push to `origin main` regularly to preserve progress

## File Organization

```text
docs/              - Requirements, decisions, architecture docs
mockup/            - Static HTML/CSS mockups for UI review
src/               - Application source code
config/            - Sample configuration files
.github/           - Instructions, workflows
```
