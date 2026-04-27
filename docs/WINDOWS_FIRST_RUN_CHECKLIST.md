# Windows 설치 후 첫 실행 체크리스트

Windows 앱이 웹서버와 동일 기능으로 정상 동작하는지 빠르게 검증하는 체크리스트입니다.

## 1) 설치 직후 기본 확인

- 설치 파일(NSIS)로 앱 설치 후 실행
- 로딩 화면에서 `uv 설치 중` / `Python 런타임 확인 중` / `Python 패키지 설치 중` 메시지 확인
- 메인 화면 진입 확인 (앱 비정상 종료 없음)

## 2) 백엔드 기동 확인

- 앱 내부에서 `/api/health` 요청이 성공하는지 확인 (메인 화면 진입 시점에 자동 확인됨)
- 로그 확인 경로:
  - `%APPDATA%/ETF Weekly Report/logs/app.log`
- 다음 항목이 로그에 존재하는지 확인:
  - `Starting backend`
  - `Backend ready`

## 3) 웹서버 기능 동등성 확인

아래 핵심 기능이 웹과 동일하게 동작하는지 확인합니다.

- 대시보드: 카드 로딩, 정렬/필터, 자동 갱신
- 종목 상세: 가격/지표/차트/뉴스
- 포트폴리오: 손익/비중/기여도
- 시뮬레이션: 일시/적립식/포트폴리오 시뮬레이션 결과
- 설정: 종목 추가/수정/삭제, 재정렬, 데이터 수집
- 알림: 규칙 생성/수정/삭제

## 4) 첫 실행 자동 설치 검증 포인트

- `uv` 미설치 환경에서 자동 설치 후 정상 진행
- Python 3.11 런타임 자동 설치 확인
- `.venv` 자동 생성 및 `requirements.txt` 자동 설치 확인
- `.venv` 손상 상태(`Scripts/python.exe` 누락)에서도 재설치/복구 확인

## 5) 실패 시 점검 순서

1. 인터넷 연결/회사망 프록시 확인
2. 백신/EDR 차단 예외 등록
3. PowerShell 실행 정책 및 권한 확인
4. 디스크 여유 공간 및 `%APPDATA%` 쓰기 권한 확인
5. `app.log`의 마지막 100줄 확인 후 재실행

## 6) 수동 복구(필요 시)

- 앱 종료
- `%APPDATA%/ETF Weekly Report/` 폴더 백업 후 삭제
- 앱 재실행하여 런타임/패키지 자동 재설치 유도

## 7) VM 자동 검증 실행 (PowerShell)

Windows VM 내부에서 아래 명령으로 설치 + 기능 검증을 자동 실행할 수 있습니다.

```powershell
cd <repo>\windows\tests
.\run-windows-e2e.ps1
```

실행 모드(설치형/실행형) 구분:

- 설치형 EXE(기본): `-PackageType install`
- 실행형 EXE(포터블): `-PackageType portable`

옵션:

- 설치를 생략하고 이미 설치된 앱만 검증:

```powershell
.\run-windows-e2e.ps1 -SkipInstall
```

- 설치 파일 경로를 직접 지정:

```powershell
.\run-windows-e2e.ps1 -PackageType install -InstallerPath "C:\path\to\ETF Weekly Report Setup 1.0.0.exe"
```

- 설치 없이 실행형 EXE를 바로 실행(포터블/`win-unpacked`):

```powershell
.\run-windows-e2e.ps1 -PackageType portable -AppExePath "C:\path\to\ETF Weekly Report.exe"
```

참고:

- 기존 옵션 `-UseDirectExe`도 계속 동작하며, 내부적으로 `-PackageType portable`로 처리됩니다.

실행 결과:

- 리포트 저장 위치: `windows/tests/reports/windows-e2e-<timestamp>.json`
- 실패 항목이 있으면 콘솔에 항목별 원인이 출력됩니다.

