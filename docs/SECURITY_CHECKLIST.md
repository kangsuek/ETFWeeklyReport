# 보안 체크리스트 (Security Checklist)

## 🔒 현재 보안 구현 상태

### ✅ 구현된 보안 기능

1. **Rate Limiting**
   - ✅ slowapi를 사용한 요청 제한
   - ✅ 엔드포인트별 다른 제한 설정
   - ✅ IP 기반 제한

2. **CORS 설정**
   - ✅ 특정 origin만 허용
   - ✅ preflight 요청 처리

3. **입력 검증**
   - ✅ Pydantic 모델 사용
   - ✅ Query 파라미터 검증
   - ✅ 날짜 범위 검증

4. **에러 처리**
   - ✅ 민감한 정보 숨김 (스택 트레이스 비노출)
   - ✅ 일관된 에러 응답 형식

---

## ⚠️ 개선이 필요한 보안 항목

### 1. 환경 변수 관리 ✅ **현재 정책 반영**

#### 현재 상황:
- `.env.example`은 **프로젝트 루트**에 있으며 커밋됨 ✅
- `.gitignore`에 `.env` 포함됨 ✅
- 백엔드·프론트엔드 모두 **루트의 `.env` 한 파일만** 사용 (`backend/.env`, `frontend/.env` 미사용). 백엔드는 `load_dotenv(루트/.env)`, 프론트는 Vite `envDir: '..'` 사용.

#### 배포 시:
- Render 등에서는 `.env` 파일 없이 **플랫폼 환경 변수**만 사용. 루트 `.env`는 로컬/개발용.

#### 확인:
```bash
git ls-files | grep -E '\.env$'   # 결과 없어야 함 (.env 미커밋)
ls -la .env.example              # 루트에 존재
```

---

### 2. API Key 인증 ⚠️ **중간**

#### 현재 동작 (backend/app/middleware/auth.py, app/dependencies.py):
- 보호된 엔드포인트(수집·설정·DB 초기화·캐시 삭제 등)는 `Depends(verify_api_key_dependency)` 사용.
- **API_KEY 미설정 시**: `verify_api_key_dependency`가 `"dev-mode"`를 반환하여 요청 허용 (개발 편의).
- **API_KEY 설정 시**: `X-API-Key` 헤더 검증, 불일치 시 401 반환.
- `APIKeyAuth.verify_api_key()`는 API_KEY 미설정 시 `False` 반환(거부)하지만, 실제 라우터는 dependency만 사용하므로 미설정 시에는 통과함.

#### 권장 사항:
- **프로덕션 배포 시 반드시 환경 변수 `API_KEY` 설정.** (Render 등에서는 대시보드에서 설정.)
- 개발 시에는 미설정 시 허용으로 편의를 두었으므로, 프로덕션에서는 누락되지 않도록 체크리스트에서 확인.

---

### 3. CORS 설정 ✅ **현재 구현**

#### 현재 코드 (backend/app/main.py):
- `allow_origins`: Config.CORS_ORIGINS (환경 변수, 쉼표 구분)
- `allow_credentials`: True
- `allow_methods`: `["GET", "POST", "PUT", "DELETE", "OPTIONS"]` (명시적)
- `allow_headers`: `["Content-Type", "X-API-Key", "Authorization", "X-No-Cache"]` (명시적)
- `expose_headers`: `["X-Total-Count"]`
- `max_age`: 3600 (preflight 캐시 1시간)

#### 권장 사항 (선택):
- 쿠키를 사용하지 않는다면 `allow_credentials=False` 검토 가능. 프로덕션에서 CORS_ORIGINS를 프론트 도메인으로만 제한할 것.

---

### 4. SQL Injection 방지 ✅ **이미 안전**

현재 모든 쿼리가 parameterized query 사용:
```python
# ✅ 안전한 코드
cursor.execute("SELECT * FROM etfs WHERE ticker = ?", (ticker,))
```

**추가 권장 사항 없음** - 현재 구현이 안전합니다.

---

### 5. 데이터베이스 보안 ⚠️ **낮음**

#### 현재 상황:
- SQLite 파일 권한이 기본값 (누구나 읽기 가능)
- Connection pool 사용 중 ✅

#### 권장 사항:
```bash
# SQLite 파일 권한 제한
chmod 600 backend/data/etf_data.db

# 또는 .gitignore에 추가 (이미 되어 있음 ✅)
```

---

### 6. 민감한 정보 로깅 방지 ⚠️ **중간**

#### 체크 사항:
```python
# ❌ 나쁜 예
logger.info(f"API Key: {api_key}")       # 절대 로깅 금지
logger.info(f"API Key: {api_key[:8]}...")  # 일부도 로깅 금지

# ✅ 좋은 예
logger.info("API Key validation successful")
```

#### 권장 사항:
- 민감한 정보(API Key, 비밀번호, 토큰)는 **전체·일부 모두** 로그에 남기지 않기.
- 인증 실패 시 경로·메서드만 로깅하고, 헤더 값은 로깅하지 않기.

---

### 7. Dependency 취약점 검사 ⚠️ **높음**

#### 현재 상황:
- `requirements.txt`에 버전 고정 ✅
- 정기적인 보안 업데이트 필요

#### 권장 사항:
```bash
# 1. 취약점 스캔 (정기적으로 실행)
cd backend
pip install safety
safety check

# 2. 의존성 업데이트
pip list --outdated

# 3. GitHub Dependabot 활성화 (저장소 설정)
```

---

### 8. 프론트엔드 보안 ⚠️ **중간**

#### XSS 방지
- React는 기본적으로 XSS 방지 ✅
- `dangerouslySetInnerHTML` 사용 금지 (코드 검색 결과 사용 안함 ✅)

#### Content Security Policy (CSP) 권장
- Vite 프로젝트 기준 진입 HTML은 `frontend/index.html`. 필요 시 해당 파일에 CSP 메타 태그 추가 검토.
```html
<!-- frontend/index.html에 추가 (선택) -->
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               script-src 'self' 'unsafe-inline'; 
               style-src 'self' 'unsafe-inline';">
```

---

## 🔐 프로덕션 배포 전 필수 체크리스트

### 환경 설정
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는가?
- [ ] `.env.example` 파일이 저장소에 커밋되었는가?
- [ ] 프로덕션 환경 변수가 별도로 관리되는가?

### 인증 & 권한
- [ ] API_KEY가 프로덕션 환경에 설정되었는가?
- [ ] 프로덕션에서 API Key 검증이 필수인가?
- [ ] Rate Limiting이 활성화되어 있는가?

### 네트워크 보안
- [ ] CORS 설정이 프로덕션 도메인으로 제한되어 있는가?
- [ ] HTTPS 사용이 강제되는가?
- [ ] HTTP → HTTPS 리다이렉트가 설정되어 있는가?

### 데이터 보안
- [ ] 민감한 데이터가 로그에 남지 않는가?
- [ ] 데이터베이스 파일 권한이 적절한가? (600)
- [ ] 백업이 암호화되어 있는가?

### 의존성
- [ ] `safety check` 또는 `npm audit` 통과했는가?
- [ ] 모든 의존성이 최신 보안 패치를 적용했는가?
- [ ] 사용하지 않는 의존성이 제거되었는가?

### 모니터링
- [ ] 비정상적인 요청 패턴 모니터링이 설정되어 있는가?
- [ ] 에러 로그가 수집되고 있는가?
- [ ] Rate limit 초과 알림이 설정되어 있는가?

---

## 📚 참고 자료

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [React Security Best Practices](https://react.dev/learn/security)
- [Python Safety](https://github.com/pyupio/safety)

---

## 🚨 보안 이슈 발견 시

보안 취약점을 발견하면:
1. 공개적으로 이슈를 올리지 **마세요**
2. 프로젝트 관리자에게 비공개로 연락
3. 패치 후 공개
