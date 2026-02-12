# Windows 데스크톱 앱 전환 계획

현재 프로그램(ETF Weekly Report)을 **Windows 데스크톱 앱**으로 배포하기 위한 단계별 계획입니다.

---

## 1. 현재 구조 요약

| 구분 | 기술 | 비고 |
|------|------|------|
| **프론트엔드** | React 18, Vite, Tailwind, Recharts | 포트 5173 (개발) / 빌드 시 `dist/` |
| **백엔드** | Python 3.11+, FastAPI, Uvicorn | 포트 8000 |
| **DB** | SQLite (로컬) / PostgreSQL (선택) | `backend/data/etf_data.db` |
| **실행** | `run.sh`로 백엔드·프론트 동시 기동 | 두 프로세스 |
| **기존 Mac 앱** | Electron (feature/macos-app) | macOS DMG 빌드만 존재 |

→ **목표**: 동일한 스택을 유지하면서, Windows에서 **단일 설치 파일(또는 포터블)** 로 실행되는 데스크톱 앱 제공.

---

## 2. 권장 아키텍처: Electron + 내장 백엔드

```
┌─────────────────────────────────────────────────────────────┐
│  Windows 데스크톱 앱 (단일 프로세스처럼 보이게)                  │
├─────────────────────────────────────────────────────────────┤
│  Electron (메인 프로세스)                                     │
│    ├── 브라우저 창: file:// 또는 localhost (빌드된 React)      │
│    └── 백엔드 자식 프로세스 실행·종료 제어                      │
├─────────────────────────────────────────────────────────────┤
│  백엔드 (자식 프로세스)                                        │
│    ├── 옵션 A: 패키징된 Python 실행 파일 (PyInstaller/Nuitka)  │
│    └── 옵션 B: 임베디드 Python + venv (폴더 형태로 동봉)       │
│    └── FastAPI(Uvicorn) → localhost:18000 (앱 공통 포트)        │
├─────────────────────────────────────────────────────────────┤
│  데이터                                                       │
│    └── %APPDATA%/ETFWeeklyReport/ (설정, DB, 로그)            │
└─────────────────────────────────────────────────────────────┘
```

- **Electron**: 기존 feature/macos-app의 Electron 구조를 확장해 Windows 타깃 추가.
- **프론트**: `VITE_API_BASE_URL=http://localhost:18000/api` 로 빌드 (Mac/Windows 앱 공통 포트, [BRANCHES.md](BRANCHES.md)#app-ports 참고).
- **백엔드**: 앱 설치 경로(또는 AppData)에서 Python 런타임/실행파일을 실행하고, 앱 종료 시 프로세스 정리.

---

## 3. 단계별 작업 계획

### Phase 1: Electron 데스크톱 레이어 (Windows 지원)

| 순서 | 작업 | 상세 |
|------|------|------|
| 1.1 | Electron 앱 소스 구성 | `feature/macos-app` 브랜치의 Mac 앱(Electron) 소스를 참고해 Windows용 구조 생성 또는 확장. |
| 1.2 | Electron 메인 프로세스 | `main.js`: 창 생성, `file://` 또는 `loadURL('http://localhost:포트')` 로 프론트 로드, **백엔드 서브프로세스 기동/종료** 로직 추가. |
| 1.3 | preload / 보안 | `preload.js`: 필요 시 `contextBridge`로 API 노출. Windows에서도 동일 정책 적용. |
| 1.4 | electron-builder Windows 설정 | `electron-builder.yml`에 `win` 타깃 추가 (nsis 인스톨러 또는 portable). |
| 1.5 | 아이콘·리소스 | Windows용 `.ico` (256x256 등) 준비, `build/icon.ico` 등으로 지정. |

**결과**: Windows에서 “프론트만” Electron으로 띄우고, 백엔드는 수동으로 `run.sh`와 유사하게 켜둔 상태로 테스트 가능.

---

### Phase 2: 백엔드 패키징 (Windows)

| 순서 | 작업 | 상세 |
|------|------|------|
| 2.1 | 패키징 방식 선택 | **옵션 A** PyInstaller/Nuitka로 단일 실행 파일. **옵션 B** Windows Embeddable Python + `venv`를 압축해 동봉. (초기에는 B가 구현·디버깅이 수월할 수 있음.) |
| 2.2 | 진입점 스크립트 | `backend/win_main.py` 또는 기존 `uvicorn app.main:app --host 127.0.0.1 --port 18000` 를 한 번 감싼 배치/스크립트. |
| 2.3 | 경로·설정 Windows 대응 | `Config`: 데이터 디렉터리를 `%APPDATA%/ETFWeeklyReport`(또는 `os.getenv('APPDATA')`) 기준으로 설정. DB 경로, `stocks.json`, 로그 경로를 모두 이 루트 아래로. |
| 2.4 | CORS | Electron에서 로드하는 프론트 오리진(`file://` 또는 `http://localhost:18000`)을 `Config.CORS_ORIGINS`에 추가. |
| 2.5 | 의존성 정리 | Selenium, ChromeDriver: Windows용 드라이버 자동 다운로드(webdriver-manager) 또는 번들. 바이너리 크기·라이선스 확인. |

**결과**: Windows 전용 “백엔드 실행 패키지”(실행 파일 또는 python+venv 폴더)가 준비되고, 지정 포트에서 단독 기동 가능.

---

### Phase 3: Electron에서 백엔드 라이프사이클

| 순서 | 작업 | 상세 |
|------|------|------|
| 3.1 | 백엔드 프로세스 스폰 | Electron `main.js`에서 `child_process.spawn`으로 백엔드 실행 경로 지정. 옵션: `cwd`를 앱 리소스 디렉터리로. |
| 3.2 | 준비 대기 | 백엔드 기동 후 `http://127.0.0.1:18000/api/health` 등으로 헬스체크, 성공 시에만 `BrowserWindow.loadURL` 또는 `loadFile`. |
| 3.3 | 로딩 UI | 기존 `loading.html`처럼 “백엔드 시작 중…” 화면 표시, 타임아웃·재시도 처리. |
| 3.4 | 종료 시 정리 | `app.on('window-all-closed')`, `app.on('before-quit')`에서 백엔드 자식 프로세스 `kill`. |

**결과**: 사용자가 앱 실행 → 백엔드 자동 기동 → 창에 프론트 표시 → 앱 종료 시 백엔드까지 함께 종료.

---

### Phase 4: 빌드·패키징 파이프라인

| 순서 | 작업 | 상세 |
|------|------|------|
| 4.1 | 프론트엔드 빌드 | `ELECTRON_BUILD=1 VITE_API_BASE_URL=http://localhost:18000/api npm run build` (앱 공통 포트 18000). |
| 4.2 | 백엔드 패키지 산출물 | PyInstaller면 `dist/etf-backend.exe` 등, Embeddable이면 `backend-runtime/` 폴더를 electron-builder의 `extraResources`에 포함. |
| 4.3 | electron-builder | `npx electron-builder --win` (nsis 또는 portable). `extraResources`로 백엔드 실행 파일/폴더 복사. |
| 4.4 | 스크립트 정리 | `scripts/build-windows.ps1` 또는 `scripts/build-windows.sh` (WSL)에서 순서: 프론트 빌드 → 백엔드 패키징 → Electron 빌드. |
| 4.5 | CI (선택) | GitHub Actions에 `windows-latest` 워커로 위 빌드 스크립트 실행, `.exe`/인스톨러 아티팩트 업로드. |

**결과**: 한 번의 빌드 명령으로 Windows용 설치 파일(또는 포터블 ZIP) 생성.

---

### Phase 5: 설치·실행 경험 정리

| 순서 | 작업 | 상세 |
|------|------|------|
| 5.1 | 설치 경로 | NSIS 기본 설치 경로(예: `C:\Users\<User>\AppData\Local\Programs\etf-weekly-report`). |
| 5.2 | 사용자 데이터 | 첫 실행 시 `%APPDATA%\ETFWeeklyReport` 생성, DB·설정·로그 저장. |
| 5.3 | 포트 충돌 | 18000 사용 중이면 재시도 또는 사용자에게 “다른 인스턴스가 실행 중” 메시지. |
| 5.4 | 바이러스/방화벽 | 코드 서명(선택): 인증서로 서명 시 Windows 경고 감소. |

---

## 4. 기술 선택 요약

| 항목 | 권장 |
|------|------|
| **데스크톱 셸** | Electron (기존 macOS와 동일) |
| **백엔드 패키징** | 단기: Windows Embeddable Python + venv 동봉 / 중기: PyInstaller 또는 Nuitka로 단일 exe |
| **설치 형태** | NSIS 인스톨러 (.exe) + 선택적 portable (.zip) |
| **API Base URL** | 빌드 시 `http://localhost:18000/api` 고정 (Mac/Windows 공통) |
| **데이터 디렉터리** | `%APPDATA%\ETFWeeklyReport` |

---

## 5. 리스크·주의사항

- **Selenium/ChromeDriver**: Windows에서 경로·권한 이슈 가능. webdriver-manager 사용 시 네트워크 필요.
- **Python 임베드**: 용량 증가. PyInstaller는 바이너리 크기·안티바이러스 오탐 가능성.
- **코드 서명**: 서명 없이 배포 시 SmartScreen 등 경고가 나올 수 있음.
- **단일 인스턴스**: 같은 PC에서 앱 두 번 실행 방지(선택) 시 `electron-single-instance` 등 고려.

---

## 6. 추천 진행 순서 (체크리스트)

- [ ] **1단계**: Electron 소스 통합 및 프론트만 로드 (백엔드 수동 실행) → Windows에서 창까지 확인.
- [ ] **2단계**: 백엔드 경로·CORS·AppData 적용 후, Windows에서 백엔드 단독 실행·API 동작 확인.
- [ ] **3단계**: Electron에서 백엔드 spawn + 헬스체크 + 종료 시 kill 연동.
- [ ] **4단계**: electron-builder로 Windows 인스톨러(또는 portable) 빌드 스크립트 작성 및 실행.
- [ ] **5단계**: 문서화, 사용자용 “설치·실행 방법” 정리.

이 순서대로 진행하면 기존 웹 앱을 유지하면서 Windows 데스크톱 앱을 단계적으로 완성할 수 있습니다.
