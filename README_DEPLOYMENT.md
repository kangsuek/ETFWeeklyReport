# 🚀 Render.com 배포 빠른 시작 가이드

이 프로젝트를 Render.com에 무료로 배포하는 방법입니다.

## 📋 배포 전 체크리스트

- [ ] GitHub 저장소에 코드가 푸시되어 있음
- [ ] Render.com 계정 생성 완료
- [ ] Naver API 키 준비 (선택사항, 뉴스 수집 기능 사용 시)

## 🎯 3단계 배포

### 1단계: GitHub에 코드 푸시

```bash
git add .
git commit -m "Add Render.com deployment configuration"
git push origin main
```

### 2단계: Render.com에서 Blueprint 배포

1. **Render.com 대시보드 접속**: https://dashboard.render.com
2. **"New +" 버튼 클릭** → **"Blueprint"** 선택
3. **GitHub 저장소 연결** (처음이면 권한 부여 필요)
4. **저장소 선택** 후 **"Apply"** 클릭
5. Render가 자동으로 다음을 생성합니다:
   - PostgreSQL 데이터베이스
   - Backend 서비스
   - Frontend 서비스

### 3단계: 환경 변수 설정

배포가 완료되면 각 서비스의 환경 변수를 설정하세요.

#### Backend 서비스 설정

1. `etf-report-backend` 서비스 선택
2. "Environment" 탭 클릭
3. 다음 변수 설정:
   - `CORS_ORIGINS`: 프론트엔드 URL (예: `https://etf-report-frontend.onrender.com`)
   - `NAVER_CLIENT_ID`: (선택사항)
   - `NAVER_CLIENT_SECRET`: (선택사항)

#### Frontend 서비스 설정

1. `etf-report-frontend` 서비스 선택
2. "Environment" 탭 클릭
3. 다음 변수 설정:
   - `VITE_API_BASE_URL`: 백엔드 URL + `/api` (예: `https://etf-report-backend.onrender.com/api`)

## ✅ 배포 완료!

이제 다음 URL로 접속할 수 있습니다:
- **Frontend**: `https://etf-report-frontend.onrender.com`
- **Backend API**: `https://etf-report-backend.onrender.com`
- **API 문서**: `https://etf-report-backend.onrender.com/docs`

## 📚 상세 가이드

더 자세한 내용은 다음 문서를 참조하세요:
- [상세 배포 가이드](./docs/RENDER_DEPLOYMENT.md)
- [환경 변수 설정 가이드](./RENDER_ENV_VARS.md)

## ⚠️ 무료 플랜 제한사항

1. **슬리프 모드**: 15분간 요청이 없으면 서비스가 슬리프 모드로 전환됩니다
   - 첫 요청 시 약 30초~1분 정도 지연될 수 있습니다
   - 해결: [UptimeRobot](https://uptimerobot.com) 등 Keep-Alive 서비스 사용

2. **월 750시간 제한**: 무료 플랜은 월 750시간만 사용 가능합니다
   - 2개 서비스(Backend + Frontend) = 월 375시간씩 사용

3. **PostgreSQL 제한**: 90일간 비활성 시 삭제될 수 있습니다

## 🆘 문제 해결

문제가 발생하면:
1. Render 대시보드의 "Logs" 탭에서 로그 확인
2. [상세 배포 가이드](./docs/RENDER_DEPLOYMENT.md)의 트러블슈팅 섹션 참조
