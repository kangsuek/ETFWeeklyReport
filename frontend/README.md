# ETF Weekly Report - Frontend

React + Vite 기반 프론트엔드 애플리케이션

## 기술 스택

- **프레임워크**: React 18.2.0
- **빌드 도구**: Vite 5.0.0
- **라우팅**: React Router DOM 6.20.0
- **상태 관리**: @tanstack/react-query 5.8.4
- **HTTP 클라이언트**: Axios 1.6.2
- **스타일링**: Tailwind CSS 3.3.5
- **차트**: Recharts 2.10.3
- **날짜 처리**: date-fns 2.30.0
- **테스트**: Vitest 4.0.8, React Testing Library 16.3.0

## 시작하기

### 1. 환경 설정

```bash
# 패키지 설치
npm install

# 환경 변수 파일 생성
cp .env.example .env
```

`.env` 파일 수정:
```bash
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_TITLE=ETF Weekly Report
```

### 2. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 http://localhost:5173 접속

### 3. 프로덕션 빌드

```bash
npm run build
```

빌드 결과물: `dist/` 디렉토리

### 4. 빌드 미리보기

```bash
npm run preview
```

브라우저에서 http://localhost:4173 접속

## 프로젝트 구조

```
frontend/
├── src/
│   ├── components/          # React 컴포넌트
│   │   ├── common/          # 공통 컴포넌트 (Skeleton 등)
│   │   ├── etf/             # ETF 관련 컴포넌트
│   │   └── layout/          # 레이아웃 컴포넌트 (Header, Footer)
│   ├── pages/               # 페이지 컴포넌트
│   │   ├── Dashboard.jsx    # 메인 대시보드
│   │   ├── ETFDetail.jsx    # 종목 상세 페이지
│   │   └── Comparison.jsx   # 종목 비교 페이지
│   ├── services/            # API 서비스 레이어
│   │   └── api.js           # Axios 인스턴스 및 API 함수
│   ├── hooks/               # Custom Hooks (추후 추가)
│   ├── utils/               # 유틸리티 함수
│   ├── styles/              # 전역 스타일
│   │   └── index.css        # Tailwind CSS 설정
│   ├── App.jsx              # 앱 루트 컴포넌트
│   └── main.jsx             # 앱 진입점
├── public/                  # 정적 파일
├── dist/                    # 빌드 결과물 (gitignore)
├── vite.config.js           # Vite 설정
├── tailwind.config.js       # Tailwind CSS 설정
├── vitest.config.js         # Vitest 설정
└── package.json
```

## 주요 기능

### 1. Dashboard (메인 페이지)
- 6개 종목(ETF 4개 + 주식 2개) 카드 표시
- 실시간 가격 정보 (종가, 등락률, 거래량)
- 정렬 기능 (이름순, 타입별, 코드순)
- 자동/수동 새로고침
- 반응형 디자인 (모바일/태블릿/데스크톱)

### 2. API 통합
- React Query로 데이터 캐싱 및 자동 갱신
- 에러 처리 및 재시도 로직
- 로딩/에러 상태 UI

### 3. 레이아웃
- Header: 네비게이션 메뉴, GitHub 링크
- Footer: 저작권 정보, 데이터 출처, 업데이트 시간
- 모바일 햄버거 메뉴

## API 엔드포인트

### ETF API
- `GET /api/etfs` - 전체 종목 조회
- `GET /api/etfs/{ticker}` - 개별 종목 정보
- `GET /api/etfs/{ticker}/prices` - 가격 데이터
- `GET /api/etfs/{ticker}/trading-flow` - 매매 동향

### News API
- `GET /api/news/{ticker}` - 종목별 뉴스

### Data Collection API
- `POST /api/data/collect-all` - 전체 데이터 수집
- `POST /api/data/backfill` - 히스토리 백필
- `GET /api/data/status` - 수집 상태 조회

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

### 번들 크기 (gzip)
- react-vendor: 52.75 kB
- query-vendor: 11.90 kB
- index (앱 코드): 23.32 kB
- **총 크기**: 88.73 kB

### 최적화 기법
- ✅ 코드 스플리팅 (React, React Query 분리)
- ✅ Esbuild minification
- ✅ 압축 (Gzip)
- ✅ React Query 캐싱 (staleTime: 5분)
- ✅ 윈도우 포커스 시 자동 갱신

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

### 개발 환경 (.env)
```bash
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_TITLE=ETF Weekly Report
```

### 프로덕션 환경 (.env.production)
```bash
VITE_API_BASE_URL=https://your-backend-domain.com/api
VITE_APP_TITLE=ETF Weekly Report
```

## 개발 가이드

### 컴포넌트 작성 규칙
1. 함수형 컴포넌트 사용
2. PropTypes 또는 TypeScript 타입 정의 (추후)
3. Hooks 사용 (useState, useEffect, useQuery 등)
4. Tailwind CSS로 스타일링

### API 호출 패턴
```javascript
// React Query 사용
const { data, isLoading, error } = useQuery({
  queryKey: ['etfs'],
  queryFn: () => etfApi.getAll(),
  staleTime: 5 * 60 * 1000, // 5분
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
