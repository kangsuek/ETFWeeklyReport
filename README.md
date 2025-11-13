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

## 🚀 빠른 시작

### 사전 요구사항
- Python 3.10+, Node.js 18+, npm/yarn

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
- [개발 환경 설정](./docs/SETUP_GUIDE.md)
- [시스템 아키텍처](./docs/ARCHITECTURE.md)
- [API 명세서](./docs/API_SPECIFICATION.md)
- [완료 기준](./docs/DEFINITION_OF_DONE.md)
- [할 일 목록](./project-management/TODO.md)

## 🔧 기술 스택
- **Backend**: FastAPI, Python 3.10+
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
