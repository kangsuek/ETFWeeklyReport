# Branch Policy

Source control is divided into the following three branches.

| Branch | Purpose |
|--------|------|
| **main** | Web server·web app (backend API, frontend, deployment) |
| **feature/macos-app** | Mac app — Electron, DMG build (`macos/` folder) |
| **feature/windows-app** | Windows app — single exe or Electron (`windows/` folder) |

- Web-related changes → **main**
- Mac app-related changes → **feature/macos-app**
- Windows app-related changes → **feature/windows-app**
- Before committing, verify the current branch using `git branch` and ensure you are working on the appropriate branch for your changes.

---

## App ports (Mac vs Windows)

Use **different ports per platform** so that (1) Mac and Windows apps can run at the same time (e.g. VM or WSL), and (2) logs and support are easier to tell apart.

| Platform | Port | Notes |
|----------|------|--------|
| **Mac app** (feature/macos-app) | **18000** | Electron backend; build with `VITE_API_BASE_URL=http://localhost:18000/api` |
| **Windows app** (feature/windows-app) | **18001** | Electron or single exe; build with `VITE_API_BASE_URL=http://localhost:18001/api` |

Web development (main) keeps backend **8000** and frontend **5173**.