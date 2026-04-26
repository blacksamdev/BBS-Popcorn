# Security Policy

## Supported versions

Security fixes are provided on the `main` branch only.
Beta builds are supported best-effort during active testing.

## Reporting a vulnerability

If you discover a security vulnerability in BBS Popcorn, please report it privately.

Do **not** open a public GitHub issue for security reports.

Use GitHub private advisories:
[https://github.com/blacksamdev/BBS-Popcorn/security/advisories/new](https://github.com/blacksamdev/BBS-Popcorn/security/advisories/new)

Please include:
- clear reproduction steps
- affected version / commit
- potential impact

We will acknowledge receipt as soon as possible, investigate, and coordinate disclosure once a fix is available.

## Project scope

In scope:
- `src/` application Python code
- `io.github.blacksamdev.Popcorn.json` Flatpak manifest
- release and packaging automation under `.github/workflows/`

Out of scope:
- vulnerabilities in third-party components (`mpv`, `yt-dlp`, `WebKitGTK`, GNOME runtime)
- local OS misconfiguration outside this project

For third-party issues, report directly to the upstream project.
