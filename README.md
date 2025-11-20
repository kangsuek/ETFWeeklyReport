# ETF Weekly Report Web Application

한국 고성장 섹터 6개 종목(ETF 4개 + 주식 2개)에 대한 종합 분석 및 리포팅 웹 애플리케이션

## 📊 대상 종목

### ETF 4개
1. **삼성 KODEX AI전력핵심설비 ETF** (487240) - AI & 전력 인프라
2. **신한 SOL 조선TOP3플러스 ETF** (466920) - 조선업
3. **KoAct 글로벌양자컴퓨팅액티브 ETF** (0020H0) - 양자컴퓨팅
4. **KB RISE 글로벌원자력 iSelect ETF** (442320) - 원자력

### 주식 2개
5. **한화오션** (042660) - 조선/방산
6. **두산에너빌리티** (034020) - 에너지/전력

## ✨ 주요 기능

### 백엔드 API
- **종목 관리**: 전체 종목 조회, 상세 정보, CRUD
- **가격 데이터**: 시가/고가/저가/종가, 거래량, 등락률 (자동 수집 지원)
- **투자자별 매매동향**: 개인/기관/외국인 순매수 추이
- **뉴스**: 종목별 뉴스 수집 및 조회 (네이버 검색 API)
- **종목 비교**: 정규화 가격, 통계, 상관관계 분석
- **배치 API**: N+1 쿼리 최적화 (대시보드)
- **자동 스케줄러**: 평일 15:50 자동 데이터 수집
- **캐시 시스템**: 메모리 기반 LRU 캐시 (TTL 30초~5분)
- **Rate Limiting**: 엔드포인트별 요청 제한

### 프론트엔드
- **대시보드**: 종목 카드 그리드, 정렬/필터, 자동 갱신
- **종목 상세**: 가격 차트, 매매동향, 통계, 뉴스 타임라인
- **종목 비교**: 정규화 가격 차트, 통계 비교, 상관관계 매트릭스
- **설정**: 다크 모드, 종목 관리, 데이터 관리
- **반응형 디자인**: 모바일/태블릿/데스크탑 지원
- **성능 최적화**: Lazy Loading, Code Splitting, 메모이제이션

자세한 기능 목록은 [FEATURES.md](./docs/FEATURES.md)를 참조하세요.

## 🚀 빠른 시작

### 사전 요구사항
- Python 3.11.9, Node.js 18+, npm/yarn

### 백엔드
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m app.database
uvicorn app.main:app --reload
```
→ http://localhost:8000/docs

### 프론트엔드
```bash
cd frontend
npm install && npm run dev
```
→ http://localhost:5173

## 📚 문서
- **[CLAUDE.md](./CLAUDE.md)** - 문서 인덱스
- **[FEATURES.md](./docs/FEATURES.md)** - 제공 기능 상세 (NEW)
- [개발 환경 설정](./docs/SETUP_GUIDE.md)
- [시스템 아키텍처](./docs/ARCHITECTURE.md)
- [API 명세서](./docs/API_SPECIFICATION.md)
- [완료 기준](./docs/DEFINITION_OF_DONE.md)
- [할 일 목록](./docs/project-management/TODO.md)

## 🔧 기술 스택
- **Backend**: FastAPI, Python 3.11.9
- **Frontend**: React 18, Vite, TailwindCSS
- **Database**: SQLite (개발) / PostgreSQL (프로덕션)
- **Charts**: Recharts, **State**: TanStack Query

## 📊 프로젝트 현황
- ✅ Phase 1: Backend Core (61개 테스트, 커버리지 82%)
- ✅ Phase 2: Data Collection (196개 테스트, 커버리지 89%)
- ✅ Phase 3: Frontend Foundation
- 🟢 Phase 4: Charts & Visualization (진행 중)

## 📖 데이터 소스
- **Naver Finance**: 가격 데이터, 투자자별 매매 동향
- **Naver Search API**: 뉴스 데이터
