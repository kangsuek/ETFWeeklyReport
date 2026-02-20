# ETF Weekly Report - just 명령 모음
# 사용: just <레시피>  또는  just --list
# 설치: https://github.com/casey/just#installation  (brew install just 등)

# 프로젝트 루트 (justfile 위치 기준)
project_root := justfile_directory()

# 기본 레시피: 사용 가능한 명령 목록
default:
    @just --list

# 백엔드 개발 서버 (8000)
backend:
    cd {{project_root}}/backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 프론트엔드 개발 서버 (5173)
frontend:
    cd {{project_root}}/frontend && npm run dev

# 백엔드 + 프론트엔드 동시 시작 (스크립트 사용)
dev:
    ./scripts/start-servers.sh

start: dev

# 실행 중인 서버 종료
stop:
    ./scripts/stop-servers.sh

# 전체 실행 (의존성 설치 + DB 초기화 + 서버) — run.sh 래퍼
run:
    ./run.sh

# 환경 설정: 백엔드 uv venv·의존성, 프론트 npm install, .env 복사
setup:
    cd {{project_root}}/backend && uv venv && uv pip install -r requirements-dev.txt
    @test -f {{project_root}}/.env || cp {{project_root}}/.env.example {{project_root}}/.env
    cd {{project_root}}/frontend && npm install
    @echo "✅ 설정 완료. DB 초기화: just db"

# 백엔드 의존성만 설치
install-backend:
    cd {{project_root}}/backend && uv venv && uv pip install -r requirements-dev.txt

# 프론트엔드 의존성만 설치
install-frontend:
    cd {{project_root}}/frontend && npm install

# DB 초기화 (backend에서)
db:
    cd {{project_root}}/backend && uv run python -m app.database

db-init: db

# 테스트: 백엔드 + 프론트엔드
test:
    just test-backend
    just test-frontend

# 백엔드 테스트
test-backend:
    cd {{project_root}}/backend && uv run pytest -v

# 백엔드 테스트 (커버리지)
test-backend-cov:
    cd {{project_root}}/backend && uv run pytest --cov=app --cov-report=term-missing -v

# 프론트엔드 테스트
test-frontend:
    cd {{project_root}}/frontend && npm test -- --run

# 프론트엔드 테스트 (커버리지)
test-frontend-cov:
    cd {{project_root}}/frontend && npm run test:coverage

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

# 개발용 PostgreSQL 컨테이너 시작 (포트 5432, 데이터 영구 보존)
pg-up-dev:
    docker-compose up -d postgres
    @echo "Waiting for PostgreSQL dev to be ready..."
    @until docker exec etf_postgres pg_isready -U etf_user -d etf_dev > /dev/null 2>&1; do sleep 1; done
    @echo "PostgreSQL dev ready at localhost:5432"

# 개발용 PostgreSQL 컨테이너 종료
pg-down-dev:
    docker-compose stop postgres

# PostgreSQL 개발환경으로 백엔드 + 프론트엔드 시작
dev-postgres: pg-up-dev
    -./scripts/stop-servers.sh 2>/dev/null; true
    DATABASE_URL=postgresql://etf_user:etf_pass@localhost:5432/etf_dev \
    ./scripts/start-servers.sh

# PostgreSQL 환경으로 백엔드만 시작
backend-postgres: pg-up-dev
    cd {{project_root}}/backend && \
    DATABASE_URL=postgresql://etf_user:etf_pass@localhost:5432/etf_dev \
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 테스트용 PostgreSQL 컨테이너 시작 (포트 5433)
pg-up:
    docker-compose up -d postgres-test
    @echo "Waiting for PostgreSQL to be ready..."
    @until docker exec etf_postgres_test pg_isready -U etf_user -d etf_test > /dev/null 2>&1; do sleep 1; done
    @echo "PostgreSQL test instance ready at localhost:5433"

# PostgreSQL 테스트 컨테이너 종료
pg-down:
    docker-compose stop postgres-test
    docker-compose rm -f postgres-test

# PostgreSQL 전용 테스트 실행 (just pg-up 먼저 실행 필요)
test-postgres:
    cd {{project_root}}/backend && \
    DATABASE_URL=postgresql://etf_user:etf_pass@localhost:5433/etf_test \
    uv run pytest tests/test_postgres_specific.py -v --no-cov

# 백엔드 보안 스캔 (safety)
security:
    cd {{project_root}}/backend && ./scripts/security_check.sh
