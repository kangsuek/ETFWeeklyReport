# 배포 가이드

## 프론트엔드 배포

### 환경 변수 설정

프로덕션 배포 전에 `.env.production` 파일을 수정하세요:

```bash
# .env.production
VITE_API_BASE_URL=https://your-backend-domain.com/api
VITE_APP_TITLE=ETF Weekly Report
```

### 빌드

```bash
npm run build
```

빌드 결과물은 `dist/` 디렉토리에 생성됩니다.

### 로컬 미리보기

프로덕션 빌드를 로컬에서 테스트:

```bash
npm run preview
```

브라우저에서 http://localhost:4173 접속

### Vercel 배포 (권장)

1. Vercel 계정 생성 (https://vercel.com)
2. GitHub 저장소 연결
3. 프로젝트 import
4. 환경 변수 설정:
   - `VITE_API_BASE_URL`: 백엔드 API URL
   - `VITE_APP_TITLE`: ETF Weekly Report
5. 배포 완료

### Netlify 배포

1. Netlify 계정 생성 (https://netlify.com)
2. GitHub 저장소 연결
3. 빌드 설정:
   - Build command: `npm run build`
   - Publish directory: `dist`
4. 환경 변수 설정 (위와 동일)
5. 배포 완료

## 백엔드 배포

### 환경 변수 설정

프로덕션 배포 전에 환경 변수를 설정하세요:

```bash
# 데이터베이스 (PostgreSQL 사용 권장)
DATABASE_URL=postgresql://user:password@host:port/database

# CORS 설정 (프론트엔드 도메인)
CORS_ORIGINS=https://your-frontend-domain.com

# Naver API 키 (뉴스 수집용)
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
```

### Railway 배포 (권장)

1. Railway 계정 생성 (https://railway.app)
2. PostgreSQL 인스턴스 생성
3. GitHub 저장소 연결
4. 환경 변수 설정
5. 배포 완료

### Render 배포

1. Render 계정 생성 (https://render.com)
2. PostgreSQL 데이터베이스 생성
3. Web Service 생성 (GitHub 연결)
4. 빌드 설정:
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. 환경 변수 설정
6. 배포 완료

## 브라우저 호환성

이 애플리케이션은 다음 브라우저에서 테스트되었습니다:

### 데스크톱
- ✅ Chrome (최신)
- ✅ Firefox (최신)
- ✅ Safari (최신)
- ✅ Edge (최신)

### 모바일
- ✅ iOS Safari (최신)
- ✅ Android Chrome (최신)

### 최소 요구사항
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 성능 최적화

### 빌드 최적화

- ✅ 코드 스플리팅 (React, React Query 분리)
- ✅ 압축 (esbuild minification)
- ✅ Gzip 압축
- ✅ 청크 크기 제한 (600KB)

### 번들 크기

```
react-vendor: 161.75 kB (gzip: 52.75 kB)
query-vendor: 38.75 kB (gzip: 11.90 kB)
index (앱 코드): 66.47 kB (gzip: 23.32 kB)
```

**총 크기**: 267 kB (gzip: 88.73 kB)

### Lighthouse 점수 목표

- Performance: 80+
- Accessibility: 90+
- Best Practices: 90+
- SEO: 90+

## 모니터링

### 프론트엔드

- Vercel Analytics (자동)
- Google Analytics (선택사항)

### 백엔드

- Railway/Render 대시보드
- 로그 모니터링

## 트러블슈팅

### CORS 에러

프론트엔드에서 백엔드 API 호출 시 CORS 에러 발생 시:

1. 백엔드 `CORS_ORIGINS` 환경 변수에 프론트엔드 도메인 추가
2. `app/main.py`의 CORS 설정 확인

### API 호출 실패

1. `.env.production`의 `VITE_API_BASE_URL` 확인
2. 백엔드 서버 상태 확인 (Health Check: `/api/health`)
3. 네트워크 탭에서 요청/응답 확인

### 빌드 에러

1. Node.js 버전 확인 (v18+ 권장)
2. `node_modules` 삭제 후 재설치: `rm -rf node_modules && npm install`
3. 캐시 삭제: `npm cache clean --force`
