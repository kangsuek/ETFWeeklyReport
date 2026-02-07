# 프로젝트 파일 구조 (표준 정합성)

현재 구조가 일반적인 풀스택/모노레포 관례에 맞는지 정리한 문서입니다.

---

## 루트 구조

| 경로 | 용도 | 표준 여부 |
|------|------|-----------|
| `README.md` | 프로젝트 소개·실행 방법 | ✅ |
| `.env.example` | 환경 변수 템플릿 (루트 단일) | ✅ |
| `.gitignore` | 무시 목록 | ✅ |
| `.pre-commit-config.yaml` | Pre-commit 훅 | ✅ |
| `.github/workflows/` | CI (예: ci.yml) | ✅ |
| `backend/` | FastAPI 백엔드 | ✅ |
| `frontend/` | React(Vite) 프론트엔드 | ✅ |
| `docs/` | 프로젝트 문서 | ✅ |
| `scripts/` | 루트 수준 스크립트 (서버 시작/종료 등) | ✅ |
| `promptTemplate/` | 프롬프트 템플릿 (AI/외부용) | ✅ (폴더명 표준: Template) |

- **환경 변수**: 백엔드·프론트엔드 모두 **루트의 `.env` 한 파일만** 사용. `backend/.env`, `frontend/.env` 미사용.

---

## 백엔드 (FastAPI)

```
backend/
├── app/                 # 메인 패키지
│   ├── main.py          # 진입점
│   ├── config.py        # 설정
│   ├── database.py      # DB
│   ├── models.py        # Pydantic 모델
│   ├── routers/         # API 라우터
│   ├── services/        # 비즈니스 로직
│   ├── middleware/      # 인증·Rate Limit
│   └── utils/           # 공용 유틸
├── config/              # 설정 파일 (예: stocks.json)
├── tests/               # pytest 테스트 (backend 루트)
├── scripts/             # 백엔드 전용 스크립트
├── requirements.txt     # 운영 의존성
├── requirements-dev.txt # 개발·테스트 의존성
├── pytest.ini           # pytest 설정
├── .flake8, .coveragerc # 린트·커버리지
└── README.md
```

- **표준**: FastAPI 권장 구조(앱 패키지 + routers/services)와 일치.
- **테스트**: `tests/` 를 backend 루트에 두는 pytest 관례 준수.
- **DB 파일**: 기본값 `backend/data/etf_data.db` (상대 경로는 프로젝트 루트 기준). `data/` 는 `.gitignore` 에 포함.

---

## 프론트엔드 (React + Vite)

```
frontend/
├── index.html           # 진입 HTML
├── vite.config.js       # Vite 설정 (envDir: '..' → 루트 .env)
├── vitest.config.js     # Vitest 설정
├── tailwind.config.js   # Tailwind
├── package.json
├── public/              # 정적 자산
├── src/
│   ├── main.jsx        # 진입점
│   ├── App.jsx         # 라우팅
│   ├── pages/          # 페이지 컴포넌트
│   ├── components/     # 공용 컴포넌트 (기능별 하위 폴더)
│   ├── hooks/          # 커스텀 훅
│   ├── services/       # API 클라이언트
│   ├── contexts/       # React Context
│   ├── utils/          # 유틸
│   ├── styles/         # 전역 스타일
│   └── test/           # 테스트 setup, mocks
└── README.md
```

- **표준**: Vite 기본 구조 + React 도메인별 폴더(pages/components/hooks/services) 관례와 일치.
- **테스트**: 컴포넌트 옆 `*.test.jsx` + `src/test/` 설정·목 업.
- **환경 변수**: `vite.config.js` 의 `envDir: '..'` 로 루트 `.env` 사용.

---

## 문서 (docs/)

**표준**: 환경 설정·실행 절차는 **SETUP_GUIDE.md** 단일 소스. 루트/backend/frontend README는 요약만 두고 상세는 본 문서로 링크.

| 문서 | 용도 |
|------|------|
| `API_SPECIFICATION.md` | REST API 명세 |
| `ARCHITECTURE.md` | 시스템·디렉터리 구조 |
| `FEATURES.md` | 기능 목록 |
| `SETUP_GUIDE.md` | 환경 설정·실행 (단일 소스) |
| `DATABASE_SCHEMA.md` | DB 스키마 |
| `DEVELOPMENT_GUIDE.md` | 개발 가이드 |
| `INTRADAY.md` | 분봉 조회·수집 방식 |
| `PROJECT_STRUCTURE.md` | 이 문서 (구조 표준 정합성) |
| `RENDER_DEPLOYMENT.md` | Render.com 배포 |
| `SECURITY_CHECKLIST.md` | 보안 체크리스트 |
| `TECH_STACK.md` | 기술 스택 |

---

## 적용한 수정 사항 (검토 시 반영)

1. **폴더명**: `promptTemplet` → `promptTemplate` (표준 철자).
2. **환경 변수**: 백엔드/프론트 모두 루트 `.env` 만 사용하도록 통일 (이미 코드 반영, 문서 정리).
3. **ARCHITECTURE.md**: 백엔드 라우터·서비스·프론트 페이지·컴포넌트 목록을 현재 코드 기준으로 최신화.

---

## 참고

- FastAPI: [Project Structure](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- Vite: [Project Root](https://vitejs.dev/guide/#index-html-and-project-root)
- React: 기능별 폴더 구조 (pages, components, hooks, services 등)는 팀/프로젝트 규모에 따라 유연히 사용.
