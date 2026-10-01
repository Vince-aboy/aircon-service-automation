# VPS and GitHub Release Plan

## Decision summary

This project will be developed locally, versioned in a **private GitHub repository**, and later transferred to the personal VPS for a private staging deployment. A public demo or public repository is a separate release decision and requires explicit approval after the security gate passes.

The repository is `Vince-aboy/aircon-service-automation`. The approved target route is `https://vinceaboy.com/balik-lamig/`, alongside the existing `/profiles/` site. No VPS directory, database, service, reverse-proxy route, or deployment has been changed by this plan.

## Release sequence

```text
Local development and tests
  → local secret and privacy review
  → private GitHub commit and push
  → VPS security/current-state audit
  → isolated private staging deployment
  → staging verification and rollback check
  → explicit approval for any public deployment or public source release
```

## GitHub policy

- Keep the repository private while the project is built and reviewed.
- Commit application source, tests, migrations, non-sensitive documentation, fictional seed data, and `.env.example` only.
- Never commit `.env`, credentials, private keys, database dumps, production logs, customer data, n8n credentials/exports containing secrets, local virtual environments, or backups.
- Before the first push, run a secret-pattern scan and manually inspect tracked files. A scan reduces risk; it does not prove that no sensitive information exists.
- Use GitHub branch protection and pull-request review if the selected GitHub plan supports it; otherwise use the local-first review gate and descriptive commits.
- If a public portfolio repository is wanted later, create a separately reviewed, sanitized version rather than changing the private working repository’s visibility by default.

## VPS deployment baseline

The Second Brain records a previously hardened VPS: key-based SSH, restricted firewall, Fail2Ban, unattended upgrades, Docker, and PostgreSQL listening on localhost. [UNCONFIRMED] These findings are historical records (primarily 2026-09-01 to 2026-09-03) and must be re-audited read-only immediately before any deployment.

For this project, use a separate, least-privilege deployment boundary:

- A dedicated non-root application user and dedicated application directory.
- A new PostgreSQL database and restricted database role only for this application; never use `postgres` from the application.
- Secrets stored only in a VPS environment file with restrictive permissions; no secrets in Git, project Markdown, or screenshots.
- Application bound to loopback/private network behind the existing HTTPS reverse proxy; PostgreSQL stays non-public.
- Deploy a specific reviewed Git commit. Record the commit, verification result, and rollback target.
- Keep n8n private and disconnected from real messaging providers until that separate scope is approved.

## GitHub-to-VPS access

The VPS will receive source by cloning/pulling the private repository over SSH with a repository-specific GitHub deploy key. The deploy key will be read-only; it cannot push code or administer the GitHub account. Its private half stays on the VPS with restrictive file permissions, and its public half is registered only on the intended repository.

Do not place a personal GitHub password or personal access token in a VPS shell history, Git remote URL, service file, repository, or project document. Creating the deploy key and adding it to GitHub are external changes and require Vince's confirmation at the Phase 7 security gate.

## Security gate before any VPS transfer

1. Confirm all tests pass locally.
2. Review `.gitignore`, tracked files, repository history, and configuration examples.
3. Scan for secrets and remove/rotate anything discovered before it is pushed or deployed.
4. Confirm synthetic data only and no customer/contact information.
5. Audit current VPS access, firewall, patch state, reverse-proxy route, storage, backups, and existing port exposure read-only.
6. Create the isolated application user, database role, and environment-file plan only after Vince approves the VPS changes.
7. Deploy privately, run smoke tests, and verify a rollback procedure.
8. Request explicit approval before publishing a public URL, enabling external notifications, or changing repository visibility.

## Portfolio positioning

Describe the result as a learning and portfolio prototype. The portfolio case study may show sanitized diagrams, fictional screenshots, the test strategy, architecture, and security decisions. It must not claim production deployment, real customer use, bookings, or business results unless independently verified and explicitly approved.
