# ETF Weekly Report - Frontend

React + Vite 기반 프론트엔드 애플리케이션

**전체 환경 설정·실행**: [docs/SETUP_GUIDE.md](../docs/SETUP_GUIDE.md) · **기술 스택 상세**: [docs/TECH_STACK.md](../docs/TECH_STACK.md)

## 시작하기

```bash
npm install
npm run dev   # http://localhost:5173
npm run build # dist/
npm run preview
```

환경 변수는 **프로젝트 루트**의 `.env` 한 파일만 사용합니다 (`vite.config.js` `envDir: '..'`). 로컬 개발 시 프록시로 `/api` → 백엔드 연결되며 별도 설정 없이 동작합니다.

## 프로젝트 구조

```
frontend/
├── src/
│   ├── components/          # React 컴포넌트
│   │   ├── common/          # 공통 (ErrorBoundary, Spinner, Toast, Skeleton 등)
│   │   ├── dashboard/       # DashboardFilters, ETFCardGrid, PortfolioHeatmap
│   │   ├── etf/             # ETFCard, ETFHeader, ETFCharts, StrategySummary, StatsSummary, PriceTable 등
│   │   ├── charts/          # PriceChart, TradingFlowChart, IntradayChart, RSIChart, MACDChart, DateRangeSelector
│   │   ├── comparison/      # TickerSelector, NormalizedPriceChart, ComparisonTable
│   │   ├── portfolio/       # PortfolioSummaryCards, AllocationPieChart, PortfolioTrendChart, ContributionTable 등
│   │   ├── settings/        # TickerManagementPanel, TickerForm, GeneralSettingsPanel, DataManagementPanel
│   │   ├── news/            # NewsTimeline
│   │   └── layout/          # Header, Footer
│   ├── pages/               # 페이지
│   │   ├── Dashboard.jsx    # 대시보드 (히트맵 + 카드 그리드)
│   │   ├── ETFDetail.jsx    # 종목 상세 (인사이트, 차트, 분봉, 뉴스)
│   │   ├── Comparison.jsx   # 종목 비교
│   │   ├── Portfolio.jsx    # 포트폴리오 (요약, 비중, 추이, 기여도)
│   │   └── Settings.jsx     # 설정 (종목 관리, 일반 설정, 데이터 관리)
│   ├── services/            # api.js (etfApi, newsApi, dataApi, settingsApi)
│   ├── contexts/            # SettingsContext, ToastContext
│   ├── hooks/               # useContainerWidth, useWindowSize 등
│   ├── utils/               # format, dateRange, portfolio, technicalIndicators 등
│   ├── styles/              # index.css (Tailwind)
│   ├── App.jsx
│   └── main.jsx
├── public/
├── dist/                    # 빌드 결과물 (gitignore)
├── vite.config.js           # envDir: '..' (루트 .env 사용)
├── tailwind.config.js
├── vitest.config.js
└── package.json
```

## 주요 기능

### 1. Dashboard (메인 페이지)
- **히트맵**: 등록된 종목 전체 현황, 일간 변동률·주간 수익률, 투자/관심 종목 구분
- **카드 그리드**: 종가, 등락률, 거래량, 미니 차트, 매매동향, 뉴스 미리보기
- 정렬: 설정 순서, 타입, 이름, 테마, 사용자 지정 순서 (드래그앤드롭)
- 자동/수동 새로고침
- 반응형 (모바일/태블릿/데스크톱)

### 2. 종목 상세·비교·포트폴리오
- **종목 상세**: 인사이트, 가격/통계, 가격·매매동향·RSI·MACD·분봉 차트, 뉴스 타임라인
- **종목 비교**: 2~6종목, 정규화 가격 차트, 수익률·변동성·MDD·샤프 비교
- **포트폴리오**: 총 투자금·평가금·수익률, 비중 차트, 일별 추이, 종목별 기여도

### 3. API 통합·레이아웃
- TanStack Query로 캐싱·갱신 (staleTime 등), 배치 API(batch-summary)로 N+1 최소화
- 에러 바운더리, 로딩/에러 UI
- Header/Footer, 다크 모드

## API 엔드포인트 (사용처)

### ETF API
- `GET /api/etfs`, `GET /api/etfs/{ticker}` - 종목 목록·상세
- `GET /api/etfs/{ticker}/prices`, `trading-flow`, `metrics`, `insights`, `intraday` - 가격·매매동향·지표·인사이트·분봉
- `POST /api/etfs/batch-summary` - 대시보드/포트폴리오 일괄 요약
- `GET /api/etfs/compare` - 종목 비교

### News / Data / Settings
- `GET /api/news/{ticker}` - 종목별 뉴스
- `POST /api/data/collect-all`, `GET /api/data/scheduler-status`, `GET /api/data/stats` 등
- `GET/POST /api/settings/stocks`, `GET /api/settings/stocks/search` 등

상세: [docs/API_SPECIFICATION.md](../docs/API_SPECIFICATION.md)

## 테스트

```bash
# 테스트 실행
npm test

# 테스트 UI
npm run test:ui

# 커버리지 확인
npm run test:coverage
```

## 성능 최적화

- ✅ 코드 스플리팅 (manualChunks: react-vendor, query-vendor 등)
- ✅ Esbuild minification, 압축
- ✅ React Query 캐싱 (staleTime/gcTime, constants.js)
- ✅ 배치 API(batch-summary)로 N+1 방지
- ✅ Lazy loading (페이지 단위 React.lazy)

## 브라우저 호환성

### 지원 브라우저
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- iOS Safari (최신)
- Android Chrome (최신)

## 배포

자세한 배포 가이드는 [DEPLOYMENT.md](./DEPLOYMENT.md) 참조

### Vercel (권장)
```bash
# Vercel CLI 설치
npm install -g vercel

# 배포
vercel
```

### Netlify
```bash
# 빌드 설정
Build command: npm run build
Publish directory: dist
```

## 환경 변수

**프로젝트 루트** `.env`만 사용. `VITE_API_BASE_URL`, `VITE_APP_TITLE` 등 (상세: [SETUP_GUIDE.md](../docs/SETUP_GUIDE.md))

## 개발 가이드

### 컴포넌트 작성 규칙
1. 함수형 컴포넌트 + Hooks (useState, useEffect, useQuery 등)
2. PropTypes 필수 ([AGENTS.md](../AGENTS.md))
3. Tailwind CSS 스타일링

### API 호출 패턴
```javascript
// TanStack Query (constants.js의 CACHE_STALE_TIME_* 사용)
const { data, isLoading, error } = useQuery({
  queryKey: ['etfs'],
  queryFn: async () => (await etfApi.getAll()).data,
  staleTime: CACHE_STALE_TIME_STATIC, // 정적 데이터 5분 등
  retry: 2,
});
```

### 에러 처리
```javascript
if (error) {
  return <div className="error">에러: {error.message}</div>;
}
```

### 로딩 상태
```javascript
if (isLoading) {
  return <ETFCardSkeleton />;
}
```

## 트러블슈팅

### CORS 에러
백엔드 서버의 CORS 설정 확인:
```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    ...
)
```

### API 호출 실패
1. 백엔드 서버 실행 확인 (http://localhost:8000)
2. 환경 변수 확인 (VITE_API_BASE_URL)
3. 네트워크 탭에서 요청/응답 확인

### 빌드 에러
```bash
# node_modules 재설치
rm -rf node_modules package-lock.json
npm install

# 캐시 삭제
npm cache clean --force
```

## 라이센스

MIT
