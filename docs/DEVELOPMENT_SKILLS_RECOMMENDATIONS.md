# 개발 스킬 추천 가이드

## 📋 개요

현재 프로젝트에 적용하면 좋을 개발 스킬과 도구를 우선순위별로 정리했습니다.

---

## 🔥 우선순위 높음 (즉시 적용 권장)

### 1. Pre-commit Hooks (코드 품질 자동화)

**목적**: 커밋 전 자동으로 코드 품질 검사 및 포매팅

**도구**: `pre-commit`

**설치 및 설정**:
```bash
# 백엔드
cd backend
pip install pre-commit
pre-commit install

# .pre-commit-config.yaml 생성
```

**설정 파일 예시** (`backend/.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.9
        args: [--line-length=100]

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black, --line-length=100]

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --extend-ignore=E203]

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: [-v, --tb=short]
```

**프론트엔드** (`frontend/.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.53.0
    hooks:
      - id: eslint
        additional_dependencies: ['eslint@8.53.0']
        args: [--fix]

  - repo: local
    hooks:
      - id: npm-test
        name: npm test
        entry: npm test
        language: system
        pass_filenames: false
        always_run: true
```

**장점**:
- 커밋 전 자동 검사로 코드 품질 일관성 유지
- 리뷰 시간 단축
- 실수 방지

---

### 2. GitHub Actions CI/CD 파이프라인

**목적**: 자동화된 테스트 및 배포

**설정 파일** (`.github/workflows/ci.yml`):
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        working-directory: ./backend
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        working-directory: ./backend
        run: pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Run tests
        working-directory: ./frontend
        run: npm test -- --coverage
      
      - name: Lint
        working-directory: ./frontend
        run: npm run lint

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Python security check
        working-directory: ./backend
        run: |
          pip install safety
          safety check
      
      - name: Node.js security check
        working-directory: ./frontend
        run: npm audit --audit-level=moderate
```

**장점**:
- 자동화된 테스트 실행
- 코드 품질 보장
- 배포 전 검증

---

### 3. 의존성 취약점 스캔

**목적**: 보안 취약점 자동 감지

**백엔드**:
```bash
# Safety 설치
pip install safety

# 스캔 실행
safety check

# requirements.txt 업데이트 후 자동 체크
safety check --file requirements.txt
```

**프론트엔드**:
```bash
# npm audit (이미 내장)
npm audit

# 심각한 취약점만 표시
npm audit --audit-level=high
```

**자동화**:
- GitHub Actions에 통합
- 주간 자동 스캔 스케줄 설정

---

### 4. 구조화된 로깅 (Structured Logging)

**목적**: 로그 분석 및 모니터링 개선

**현재**: 기본 `logging` 모듈 사용

**개선안**: `structlog` 사용

**설치**:
```bash
pip install structlog
```

**설정 예시** (`backend/app/utils/structured_logging.py`):
```python
import structlog
import logging

def setup_structured_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

**사용 예시**:
```python
import structlog

logger = structlog.get_logger()

# 구조화된 로깅
logger.info("price_fetched", 
            ticker="487240", 
            price=12500, 
            date="2025-01-27",
            duration_ms=45)
```

**장점**:
- JSON 형식으로 로그 분석 용이
- 필드별 검색 가능
- 모니터링 도구 연동 쉬움

---

## 🟡 우선순위 중간 (단기간 내 적용 권장)

### 5. 에러 추적 및 모니터링 (Sentry)

**목적**: 프로덕션 에러 자동 수집 및 알림

**설치**:
```bash
# 백엔드
pip install sentry-sdk[fastapi]

# 프론트엔드
npm install @sentry/react
```

**백엔드 설정** (`backend/app/main.py`):
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
    ],
    traces_sample_rate=0.1,  # 성능 모니터링 샘플링
    environment=os.getenv("ENV", "development"),
)
```

**프론트엔드 설정** (`frontend/src/main.jsx`):
```javascript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  integrations: [
    new Sentry.BrowserTracing(),
  ],
  tracesSampleRate: 0.1,
  environment: import.meta.env.MODE,
});
```

**장점**:
- 실시간 에러 알림
- 스택 트레이스 자동 수집
- 사용자 영향도 분석

---

### 6. API 성능 모니터링

**목적**: 느린 API 엔드포인트 식별

**도구**: FastAPI 내장 미들웨어 + 커스텀 메트릭

**구현 예시** (`backend/app/middleware/performance.py`):
```python
from fastapi import Request
import time
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# 성능 메트릭 저장
performance_metrics = defaultdict(list)

@app.middleware("http")
async def performance_monitoring(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    endpoint = f"{request.method} {request.url.path}"
    
    # 느린 요청 로깅 (1초 이상)
    if process_time > 1.0:
        logger.warning(
            f"Slow request detected: {endpoint} took {process_time:.3f}s",
            extra={
                "endpoint": endpoint,
                "duration": process_time,
                "status": response.status_code
            }
        )
    
    # 메트릭 저장
    performance_metrics[endpoint].append(process_time)
    
    # 응답 헤더에 추가
    response.headers["X-Process-Time"] = str(process_time)
    
    return response
```

**장점**:
- 성능 병목 지점 식별
- 최적화 우선순위 결정

---

### 7. E2E 테스트 (Playwright)

**목적**: 실제 사용자 시나리오 테스트

**설치**:
```bash
npm install -D @playwright/test
npx playwright install
```

**설정** (`frontend/playwright.config.js`):
```javascript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

**테스트 예시** (`frontend/e2e/dashboard.spec.js`):
```javascript
import { test, expect } from '@playwright/test';

test('Dashboard loads and displays ETF cards', async ({ page }) => {
  await page.goto('/');
  
  // ETF 카드가 표시되는지 확인
  await expect(page.locator('[data-testid="etf-card"]')).toHaveCount(6);
  
  // 첫 번째 카드 클릭
  await page.locator('[data-testid="etf-card"]').first().click();
  
  // 상세 페이지로 이동 확인
  await expect(page).toHaveURL(/\/etf\/\d+/);
});
```

**장점**:
- 실제 사용자 시나리오 검증
- 회귀 테스트 자동화

---

## 🟢 우선순위 낮음 (장기 개선)

### 8. TypeScript 마이그레이션

**목적**: 타입 안정성 향상

**단계적 마이그레이션**:
1. `tsconfig.json` 설정
2. `.jsx` → `.tsx` 점진적 변환
3. JSDoc 타입 주석으로 시작

**장점**:
- 컴파일 타임 에러 감지
- IDE 자동완성 개선
- 리팩토링 안전성 향상

---

### 9. API 문서 자동화 개선

**목적**: OpenAPI 스키마 기반 문서 개선

**현재**: FastAPI 자동 생성 (`/docs`)

**개선안**:
- 예시 응답 추가
- 에러 케이스 문서화
- Postman Collection 자동 생성

---

### 10. 성능 프로파일링

**목적**: 메모리 및 CPU 사용량 분석

**도구**:
- Python: `cProfile`, `memory_profiler`
- React: React DevTools Profiler

**사용 예시**:
```bash
# 백엔드 프로파일링
python -m cProfile -o profile.stats app/main.py

# 분석
python -m pstats profile.stats
```

---

## 📊 적용 우선순위 요약

| 우선순위 | 스킬 | 예상 시간 | 효과 |
|---------|------|----------|------|
| 🔥 높음 | Pre-commit Hooks | 1시간 | 코드 품질 자동화 |
| 🔥 높음 | GitHub Actions CI/CD | 2-3시간 | 자동화된 테스트 |
| 🔥 높음 | 의존성 취약점 스캔 | 30분 | 보안 강화 |
| 🔥 높음 | 구조화된 로깅 | 2시간 | 로그 분석 개선 |
| 🟡 중간 | Sentry 에러 추적 | 2시간 | 에러 모니터링 |
| 🟡 중간 | 성능 모니터링 | 1-2시간 | 성능 최적화 |
| 🟡 중간 | E2E 테스트 | 3-4시간 | 사용자 시나리오 검증 |
| 🟢 낮음 | TypeScript | 장기 | 타입 안정성 |
| 🟢 낮음 | API 문서 개선 | 1-2시간 | 문서화 |
| 🟢 낮음 | 성능 프로파일링 | 1시간 | 성능 분석 |

---

## 🚀 빠른 시작 가이드

### 1단계: Pre-commit Hooks 설정 (30분)

```bash
cd backend
pip install pre-commit
# .pre-commit-config.yaml 생성 (위 예시 참고)
pre-commit install

cd ../frontend
npm install --save-dev husky lint-staged
# package.json에 scripts 추가
```

### 2단계: GitHub Actions 설정 (1시간)

```bash
mkdir -p .github/workflows
# ci.yml 파일 생성 (위 예시 참고)
git add .github/workflows/ci.yml
git commit -m "Add CI/CD pipeline"
```

### 3단계: 의존성 스캔 자동화 (30분)

```bash
# backend/scripts/security_check.sh 생성
#!/bin/bash
pip install safety
safety check

# package.json에 스크립트 추가
"scripts": {
  "security:check": "npm audit --audit-level=moderate"
}
```

---

## 📚 참고 자료

- [Pre-commit 공식 문서](https://pre-commit.com/)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Sentry 문서](https://docs.sentry.io/)
- [Playwright 문서](https://playwright.dev/)
- [Safety 문서](https://github.com/pyupio/safety)

---

## 💡 추가 제안

### 코드 리뷰 프로세스
- Pull Request 템플릿 생성
- 코드 리뷰 체크리스트

### 문서화 자동화
- API 변경 시 자동 문서 업데이트 알림
- CHANGELOG 자동 생성

### 성능 벤치마크
- API 응답 시간 벤치마크 설정
- 성능 회귀 테스트
