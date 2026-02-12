# 단일 EXE 구현 계획 (프론트 + 백엔드 함께 실행)

exe 파일 1개만 실행하면 프론트엔드와 백엔드가 함께 동작하도록 하는 구현 계획입니다.  
**소스 관리**: Windows 앱 관련 작업은 **feature/windows-app** 브랜치에서 진행. (브랜치 정책: [BRANCHES.md](BRANCHES.md))

---

## 1. 목표

- **사용자 동작**: exe 1개 더블클릭 → 앱 창이 뜨고, API·화면 모두 동작
- **구조**: 단일 프로세스. Python 실행 파일 하나가 FastAPI(API + 정적 파일 제공) + 네이티브 창(pywebview)을 담당
- **Electron 미사용**: 별도 Node/Electron 없이 Python만으로 패키징

---

## 2. 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│  ETFWeeklyReport.exe (단일 프로세스)                         │
├─────────────────────────────────────────────────────────────┤
│  Python 런타임 (PyInstaller로 번들)                           │
│    ├── FastAPI 앱                                            │
│    │     ├── /api/*  → 기존 라우터 (etfs, news, data, …)     │
│    │     └── /*      → React 빌드(정적 파일) + SPA 폴백       │
│    ├── Uvicorn (127.0.0.1:고정포트)                          │
│    └── pywebview (네이티브 창에서 http://127.0.0.1:포트 로드)  │
├─────────────────────────────────────────────────────────────┤
│  데이터: %APPDATA%\ETFWeeklyReport\ (DB, 설정, 로그)          │
└─────────────────────────────────────────────────────────────┘
```

- **진입점**: 데스크톱 전용 스크립트 1개 (예: `run_windows.py`)
- **프론트**: Vite 빌드 시 `VITE_API_BASE_URL` 비우거나 `/api` 로 빌드 → 같은 출처로 API 호출
- **창**: pywebview로 `http://127.0.0.1:포트` 로드 (브라우저 창 아님, 네이티브 창)

---

## 3. 구현 단계

### Phase 1: 데스크톱용 진입점 및 정적 서빙

| # | 작업 | 내용 |
|---|------|------|
| 1.1 | 데스크톱 진입 스크립트 추가 | `backend/run_windows.py` (또는 `backend/win_main.py`) 생성. `app.main:app` import 후 정적 마운트·SPA 폴백 적용. |
| 1.2 | 정적 파일 마운트 | FastAPI에 `StaticFiles(directory=dist 경로, html=True)` 를 `/` 에 마운트. 경로는 환경 변수 또는 PyInstaller `sys._MEIPASS` 기준. |
| 1.3 | SPA 폴백 라우트 | React Router 대응: `/api` 가 아닌 GET 요청 중 파일이 없으면 `index.html` 반환 (catch-all 또는 404 핸들러). |
| 1.4 | 루트 라우트 조정 | 기존 `GET /` 는 API 안내용이므로, 데스크톱 모드에서는 정적 `index.html` 이 우선되도록 라우트 순서/조건 정리. |

**산출물**: 개발 시 `python run_windows.py` 로 실행하면 같은 프로세스에서 API + 프론트 서빙 가능 (이때 창은 수동으로 브라우저에서 열거나, 3.2에서 pywebview 연동).

---

### Phase 2: 네이티브 창 연동 (pywebview)

| # | 작업 | 내용 |
|---|------|------|
| 2.1 | 의존성 추가 | `pywebview` 를 `requirements-windows.txt` 또는 `requirements.txt` 에 추가. |
| 2.2 | 서버 기동 후 창 열기 | `run_windows.py` 에서 Uvicorn을 **스레드**로 기동 → 헬스체크 대기 → `pywebview.create_window(...)` 로 `http://127.0.0.1:포트` 로드. |
| 2.3 | 종료 시 서버 정리 | pywebview 창이 닫히면 Uvicorn 서버 종료 (이벤트 훅 또는 메인 루프 종료 시 스레드 정리). |
| 2.4 | 포트 고정 | 앱 공통 포트 **18000** 사용 ([BRANCHES.md](BRANCHES.md)#app-ports). 충돌 시 재시도 또는 사용자 메시지는 선택. |

**산출물**: `python run_windows.py` 실행 시 콘솔 없이(또는 최소 로그로) 네이티브 창만 뜨고, 창 닫으면 프로세스 종료.

---

### Phase 3: 데스크톱 전용 설정·경로

| # | 작업 | 내용 |
|---|------|------|
| 3.1 | 데이터 디렉터리 | Windows: `%APPDATA%\ETFWeeklyReport` (또는 `os.getenv('APPDATA')`). DB 경로, `stocks.json`, 로그를 이 루트 아래로. |
| 3.2 | Config 분기 | `backend/app/config.py` 에 “데스크톱 모드” 플래그(환경 변수 등) 두고, 데스크톱일 때만 위 데이터 경로·CORS(필요 시) 적용. |
| 3.3 | CORS | 동일 출처(localhost)만 사용하면 CORS 이슈 최소화. 필요 시 `allow_origins` 에 `http://127.0.0.1:포트` 만 추가. |

**산출물**: 설치 위치와 무관하게 사용자 데이터는 AppData에만 저장.

---

### Phase 4: 프론트엔드 빌드 연동

| # | 작업 | 내용 |
|---|------|------|
| 4.1 | 데스크톱용 빌드 스크립트 | `VITE_API_BASE_URL=`(빈값) 또는 `VITE_API_BASE_URL=/api` 로 프론트 빌드. 산출물은 `frontend/dist/`. |
| 4.2 | 빌드 결과 위치 약속 | PyInstaller가 참조할 수 있도록 `frontend/dist/` 를 데스크톱 빌드 시 한 번 생성하고, 그 경로를 `run_windows.py`(또는 spec)에서 고정. |

**산출물**: 한 번의 프론트 빌드로 데스크톱 exe에 넣을 정적 파일 준비 완료.

---

### Phase 5: PyInstaller 패키징

| # | 작업 | 내용 |
|---|------|------|
| 5.1 | 진입점 지정 | PyInstaller 진입점을 `run_windows.py` 로 지정. |
| 5.2 | 데이터 파일 포함 | `frontend/dist/` 전체, `backend/config/stocks.json` 등을 `datas` 또는 `--add-data` 로 번들. |
| 5.3 | 숨김 import | FastAPI, uvicorn, pywebview, pydantic 등 런타임에만 로드되는 모듈은 `--hidden-import` 로 명시. |
| 5.4 | spec 파일 (선택) | `etf_weekly_report.spec` 작성해 한 번에 빌드 재현 가능하도록 정리. |
| 5.5 | 단일 exe 여부 | `--onefile` 이면 실행 시 압축 해제로 인한 지연 가능. `--onedir` 이면 폴더 1개 + exe 로 더 빠른 기동. 문서에 선택지 명시. |

**산출물**: Windows에서 `ETFWeeklyReport.exe` (또는 `ETFWeeklyReport/` 폴더 + exe) 실행 시 위 아키텍처대로 동작.

---

### Phase 6: 빌드·배포 스크립트 및 문서

| # | 작업 | 내용 |
|---|------|------|
| 6.1 | Windows 빌드 스크립트 | `scripts/build-windows.ps1` 또는 `build-single-exe.ps1`: 프론트 빌드 → (가상환경 활성화) → PyInstaller 실행 → 출력 경로 안내. |
| 6.2 | README/문서 | 단일 exe 빌드 방법, 필요 환경(Python 버전, Node 등), 실행 시 데이터 경로(`%APPDATA%\ETFWeeklyReport`) 안내. |
| 6.3 | (선택) 코드 서명 | Windows 경고 감소를 위한 서명 절차를 문서에만이라도 기재. |

**산출물**: 다른 개발자가 문서만 보고 단일 exe를 빌드·배포할 수 있는 상태.

---

## 4. 파일/경로 정리

| 구분 | 경로/파일 |
|------|-----------|
| Windows 앱 진입점 | `backend/run_windows.py` (신규) |
| 기존 앱 | `backend/app/main.py` (수정 최소화, 데스크톱 전용 라우트는 진입점에서 app 마운트) |
| 설정 분기 | `backend/app/config.py` (데스크톱 데이터 경로 등) |
| Windows 앱 의존성 | `backend/requirements-windows.txt` (pywebview 등) 또는 requirements.txt에 통합 |
| 프론트 빌드 | `frontend/` 에서 `VITE_API_BASE_URL=/api npm run build` |
| PyInstaller | `backend/etf_weekly_report.spec` (선택), 또는 CLI 인자로 빌드 |
| 빌드 스크립트 | `scripts/build-windows.ps1` 또는 동일 역할의 스크립트 |
| 사용자 데이터 | Windows: `%APPDATA%\ETFWeeklyReport` |

---

## 5. 주의사항

- **Selenium/ChromeDriver**: 데스크톱 exe에서도 사용할 경우 Windows 경로·권한·webdriver-manager 다운로드 이슈 검토 필요.
- **콘솔 창**: PyInstaller에서 `--noconsole`(또는 spec의 `console=False`) 사용 시 디버깅은 로그 파일에 의존.
- **안티바이러스**: 단일 exe/패키징 시 오탐 가능성 있음. 코드 서명·공개 빌드 경로 명시 시 완화 가능.

---

이 문서는 **구현 계획만** 기술합니다. 실제 코드 변경은 위 단계에 따라 별도 작업으로 진행하면 됩니다.
