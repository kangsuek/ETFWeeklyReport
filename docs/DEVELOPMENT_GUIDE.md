# 개발 가이드

## 코드 품질 표준

### Python (백엔드)
- **PEP 8** 준수, 4 spaces 들여쓰기
- 타입 힌트 사용, Docstring 필수
- 비동기 I/O: `async/await` 사용

### JavaScript/React (프론트엔드)
- **ESLint** 규칙 준수, 2 spaces 들여쓰기
- 함수형 컴포넌트 + Hooks
- Props 문서화 (JSDoc)

## 프로젝트 구조

### 백엔드
```
backend/app/
├── routers/      # API 엔드포인트
├── services/      # 비즈니스 로직
├── models.py     # Pydantic 모델
├── database.py   # DB 연결
└── main.py       # FastAPI 앱
```

### 프론트엔드
```
frontend/src/
├── pages/        # 라우트 컴포넌트
├── components/   # 재사용 컴포넌트
├── hooks/        # Custom Hooks
├── services/     # API 클라이언트
└── utils/        # 유틸리티 함수
```

## 네이밍 규칙

### 백엔드 (Python)
- 변수/함수: `snake_case`
- 클래스: `PascalCase`
- 상수: `UPPER_CASE`

### 프론트엔드 (JavaScript/React)
- 변수/함수: `camelCase`
- 컴포넌트: `PascalCase`
- 상수: `UPPER_CASE`

## Git 워크플로우

### 커밋 메시지 규칙
```
type(scope): subject

예시: feat(backend): ETF 가격 데이터 수집 기능 추가
```

**Type**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## 테스트 전략
- **커버리지 목표**: 백엔드 80%, 프론트엔드 70%, Critical Path 100%
- **패턴**: Given-When-Then 구조
- **⚠️ 중요**: 모든 기능은 테스트 100% 완료 후 다음 단계로 진행

## 성능 최적화

### 백엔드
- 비동기 I/O: `async/await`, `asyncio.gather()`
- 데이터베이스 인덱스 최적화

### 프론트엔드
- React.memo: 불필요한 리렌더링 방지
- Code Splitting: `React.lazy()` 사용

## 보안 체크리스트
- [ ] `.env` 파일을 `.gitignore`에 추가
- [ ] CORS 설정: 허용된 origin만 명시
- [ ] SQL Injection 방지: 파라미터화된 쿼리
- [ ] XSS 방지: 사용자 입력 sanitize
- [ ] HTTPS 사용 (프로덕션)
