# ETF Weekly Report - just 명령 모음
# 사용: just <레시피>  또는  just --list
# 설치: https://github.com/casey/just#installation  (brew install just 등)

# 프로젝트 루트 (justfile 위치 기준)
project_root := justfile_directory()

# 기본 레시피: 사용 가능한 명령 목록
default:
    @just --list

# ─────────────────────────────────────────────────────────────
# 공통: 환경 설정 / 빌드 / 린트 / 보안
# ─────────────────────────────────────────────────────────────

# 환경 설정: 백엔드 uv venv·의존성, 프론트 npm install, .env 복사
setup:
    cd {{project_root}}/backend && uv venv && uv pip install -r requirements-dev.txt
    @test -f {{project_root}}/.env || cp {{project_root}}/.env.example {{project_root}}/.env
    cd {{project_root}}/frontend && npm install
    @echo "✅ 설정 완료. 서버 실행: just dev"

# 백엔드 의존성만 설치
install-backend:
    cd {{project_root}}/backend && uv venv && uv pip install -r requirements-dev.txt

# 프론트엔드 의존성만 설치
install-frontend:
    cd {{project_root}}/frontend && npm install

# 린트: 백엔드 + 프론트엔드
lint:
    just lint-backend
    just lint-frontend

# 백엔드 린트
lint-backend:
    cd {{project_root}}/backend && uv run flake8 app/ tests/ --max-line-length=100

# 프론트엔드 린트
lint-frontend:
    cd {{project_root}}/frontend && npm run lint

# Pre-commit 훅 설정
pre-commit:
    ./scripts/setup-pre-commit.sh

# 백엔드 보안 스캔 (safety)
security:
    cd {{project_root}}/backend && ./scripts/security_check.sh

# ─────────────────────────────────────────────────────────────
# [Mac 앱] Electron 개발 / 빌드
# ─────────────────────────────────────────────────────────────

# Mac 앱 개발 모드 실행
macos-dev:
    cd {{project_root}}/macos && npm start

# Mac 앱 빌드 (DMG 생성)
macos-build:
    bash {{project_root}}/macos/scripts/build.sh

# ─────────────────────────────────────────────────────────────
# [SQLite] 기본 개발 환경
# ─────────────────────────────────────────────────────────────

# SQLite: 백엔드 + 프론트엔드 동시 시작
dev:
    ./scripts/start-servers.sh

start: dev

# SQLite: 백엔드 개발 서버만 (8000)
backend:
    cd {{project_root}}/backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# SQLite: 프론트엔드 개발 서버만 (5173)
frontend:
    cd {{project_root}}/frontend && npm run dev

# SQLite: 실행 중인 서버 종료
stop:
    ./scripts/stop-servers.sh

# SQLite: 전체 실행 (의존성 설치 + DB 초기화 + 서버) — run.sh 래퍼
run:
    ./run.sh

# SQLite: DB 초기화
db:
    cd {{project_root}}/backend && uv run python -m app.database

db-init: db

# SQLite: 백엔드 테스트 (SQLite in-memory)
test-backend:
    cd {{project_root}}/backend && uv run pytest -v

# SQLite: 백엔드 테스트 (커버리지)
test-backend-cov:
    cd {{project_root}}/backend && uv run pytest --cov=app --cov-report=term-missing -v

# SQLite: 프론트엔드 테스트
test-frontend:
    cd {{project_root}}/frontend && npm test -- --run

# SQLite: 프론트엔드 테스트 (커버리지)
test-frontend-cov:
    cd {{project_root}}/frontend && npm run test:coverage

# SQLite: 백엔드 + 프론트엔드 테스트 전체
test:
    just test-backend
    just test-frontend
