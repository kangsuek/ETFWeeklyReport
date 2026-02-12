# ETF Weekly Report

Comprehensive analysis web application for Korean high-growth sector **ETFs and stocks**.

This project is an ETF reporting/analysis application with both web and desktop (Electron/DMG) components. The codebase uses JavaScript (frontend) and Python (backend). When looking for features, check both naming conventions - e.g., 'simulation' files may contain backtesting logic.

## User Preferences section
The user's name is 강석 (kangsuek). Communicate in Korean when the user writes in Korean. Default to English for code comments and commit messages unless asked otherwise.

## Git Workflow section
When committing code, always separate changes by branch context: main branch is for web features, feature branches are for desktop app work. Ask which branch before committing if unclear. Use `git status` and `git branch` before any git operations.

## Testing & Verification section
After making multi-file changes, always run the build/test suite to verify nothing is broken before committing. For the frontend: run the build command. For the backend Python code: run existing tests.

## Working Style section
When working on implementation tasks, be concise and act quickly. Do not over-explain or spend excessive time on codebase exploration before starting work. If the user has provided a plan document, follow it directly.

## Core Documentation (Essential)

1. **[README.md](./README.md)** - Project overview, asset configuration, quick start guide
2. **[FEATURES.md](./docs/FEATURES.md)** - Detailed features provided (backend API, frontend)
3. **[DEVELOPMENT_GUIDE.md](./docs/DEVELOPMENT_GUIDE.md)** - Development guide, testing strategy (refer to AGENTS.md)

## Reference Documents

### Technical Documentation
- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - System architecture
- **[API_SPECIFICATION.md](./docs/API_SPECIFICATION.md)** - REST API specification
- **[DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md)** - Database Schema
- **[TECH_STACK.md](./docs/TECH_STACK.md)** - Technology Stack

### Detail Features
- **[INTRADAY.md](./docs/detail_features/INTRADAY.md)** - Intraday chart retrieval and collection

### Development, Configuration, and Deployment
- **[RENDER_DEPLOYMENT.md](./docs/RENDER_DEPLOYMENT.md)** - Render.com deployment (including environment variables)


IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task.
