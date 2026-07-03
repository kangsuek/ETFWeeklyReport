# Branch Policy

Source control is divided into the following three branches.

| Branch | Purpose |
|--------|------|
| **main** | Web server·web app (backend API, frontend, deployment). Historical `macos/` files exist here too, but the Mac app is maintained on its own branch |
| **feature/macos-app** | Mac app — Electron, DMG build (`macos/` folder) |
| **feature/windows-app** | Windows app — single exe or Electron (`windows/` folder) |

- Web-related changes → **main**
- Mac app-related changes → **feature/macos-app**
- Windows app-related changes → **feature/windows-app**
- Before committing, verify the current branch using `git branch` and ensure you are working on the appropriate branch for your changes.

> ⚠️ **main and feature/macos-app have diverged in parallel** (they are forks, not ahead/behind).
> Do **not** mechanically merge/sync between them — web files differ by dozens of commits and a
> blind sync risks regressions. Port changes individually after verifying each one on the target branch.

---

## App ports

All app builds (Mac, Windows) use the same port **18000** for the backend.

| Mode | Port | Notes |
|------|------|--------|
| **App** (Mac / Windows) | **18000** | Build with `VITE_API_BASE_URL=http://localhost:18000/api` |
| **Web dev** (main) | **8000** / **5173** | Backend 8000, Frontend 5173 |