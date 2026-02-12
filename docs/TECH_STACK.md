# Technology Stack

## Backend

| Technology | Version | Purpose |
|------|------|------|
| **Python** | 3.11+ | Programming language |
| **FastAPI** | 0.104.1 | Web framework |
| **Uvicorn** | 0.24.0 | ASGI server |
| **Pydantic** | 2.5.0 | Data validation and schema configuration |
| **pydantic-settings** | 2.1.0 | Environment variable-based configuration |
| **pandas** | 2.1.3 | Data analysis and processing |
| **numpy** | 1.26.2 | Numerical computation |
| **requests** | 2.31.0 | HTTP requests (synchronous) |
| **BeautifulSoup4** | 4.12.2 | HTML parsing |
| **lxml** | 4.9.3 | Accelerated XML/HTML parsing |
| **finance-datareader** | 0.9.96 | Financial data collection helper |
| **aiofiles** | 23.2.1 | Asynchronous file I/O |
| **APScheduler** | 3.10.4 | Scheduled tasks (daily data collection) |
| **slowapi** | 0.1.9 | Rate limiting |
| **limits** | 4.2 | Rate limit backend |
| **python-dotenv** | 1.0.0 | Load root `.env` |
| **python-multipart** | 0.0.6 | Multipart form parsing |
| **structlog** | 23.2.0 | Structured logging |
| **Selenium** | 4.15.2 | Browser automation (candlestick charts, etc.) |
| **webdriver-manager** | 4.0.1 | WebDriver automated management |
| **psycopg2-binary** | 2.9.9 | PostgreSQL driver (production) |
| **SQLite** | - | Development/Basic DB |
| **PostgreSQL** | - | Production DB (Optional) |

**Primary Data Sources**: Naver Finance (prices, trading trends, tick data), Naver Search API (News)

## Frontend

| Technology | Version | Purpose |
|------|------|------|
| **React** | 18.3.1 | UI Library |
| **Vite** | 5.4.21 | Build·Development Server |
| **React Router** | 6.30.3 | Routing |
| **TanStack Query** | 5.90.7 | Server State·Cache |
| **Axios** | 1.13.2 | HTTP Client |
| **TailwindCSS** | 3.4.18 | Utility CSS |
| **Recharts** | 2.15.4 | Charts (price, trading trends, comparisons, portfolios, screening heatmap/treemap, simulation charts) |
| **date-fns** | 2.30.0 | Date formatting and calculations |
| **@dnd-kit/core** | 6.3.1 | Drag and drop (card reordering) |
| **@dnd-kit/sortable** | 10.0.0 | Sortable lists |
| **@dnd-kit/utilities** | 3.2.2 | dnd-kit utilities |
| **clsx** | 2.1.1 | Conditional class names |
| **prop-types** | 15.8.1 | Runtime props validation |

## Development Tools

| Category | Tool | Purpose |
|------|------|------|
| **Local Python Environment** | uv | Package·virtual environment management (essential). `uv venv`, `uv pip install`, `uv run` |
| **Backend Testing** | pytest, pytest-asyncio, pytest-cov, pytest-mock, httpx | Unit·API testing, coverage (requirements-dev.txt) |
| **Backend Formatting** | black, isort | Code formatting (line-length 100) |
| **Backend Linting** | flake8, pylint | Style·static analysis |
| **Backend Typing** | mypy | Static type checking |
| **Backend Miscellaneous** | pre-commit, coverage | Hooks·Coverage Reporting |
| **Frontend Testing** | Vitest, React Testing Library, @testing-library/user-event, MSW, jsdom | Unit·Component Testing, API Mockups |
| **Frontend Linting** | ESLint (react, hooks, refresh) | Linting |
| **Frontend Build** | PostCSS, autoprefixer | CSS Post-processing (Tailwind) |

## Deployment

| Category | Option |
|------|------|
| **Frontend** | Vite build → `dist/` static hosting (Render Static Site, Vercel, Netlify, etc.) |
| **Backend** | Uvicorn-based (Render Web Service, Railway, Fly.io, etc.). `render.yaml` Blueprint support. |
| **Database** | SQLite (local·default) or PostgreSQL (production on Render etc.) |

Version locking: Backend refer to `requirements.txt` / `requirements-dev.txt`, Frontend refer to `package.json` (^ scope).