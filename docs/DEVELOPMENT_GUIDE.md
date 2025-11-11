# 개발 가이드

## 코드 품질 표준

### Python (백엔드)

#### 스타일 가이드

- **PEP 8** 준수
- 들여쓰기: 4 spaces
- 최대 줄 길이: 100자
- 타입 힌트 사용

#### 코드 패턴

```python
async def function_name(param: Type) -> ReturnType:
    """Docstring 필수"""
    try:
        return result
    except Exception as e:
        logger.error(f"에러: {e}")
        return None
```

#### 함수 작성 규칙

1. **단일 책임 원칙**: 한 함수는 하나의 작업만 수행
2. **Docstring 필수**: 모든 public 함수에 작성
3. **타입 힌트**: 파라미터 및 반환값에 타입 명시
4. **에러 처리**: try-except로 예외 처리, 로깅 포함
5. **비동기 I/O**: 네트워크/파일 작업은 async/await 사용

---

### JavaScript/React (프론트엔드)

#### 스타일 가이드

- **ESLint** 규칙 준수
- 들여쓰기: 2 spaces
- 함수형 컴포넌트 + Hooks 사용
- PropTypes 또는 TypeScript 사용 권장

#### 컴포넌트 패턴

```javascript
export default function Component({ props }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['key', props.id],
    queryFn: () => api.getData(props.id),
  })
  if (isLoading) return <Spinner />
  if (error) return <Error message={error.message} />
  return <div>{/* UI */}</div>
}
```

#### 컴포넌트 작성 규칙

1. **작고 집중된 컴포넌트**: 한 파일당 100줄 이하 권장
2. **Props 문서화**: JSDoc 주석 작성
3. **상태 관리**:
   - 서버 데이터: React Query
   - 로컬 UI 상태: useState
4. **로딩/에러 처리**: 항상 포함
5. **재사용성**: 공통 로직은 custom hooks로 추출

---

## 프로젝트 구조 규칙

### 백엔드 파일 구조

```
backend/app/
├── routers/      # API 엔드포인트
├── services/      # 비즈니스 로직
├── models.py     # Pydantic 모델
├── database.py   # DB 연결
└── main.py       # FastAPI 앱
```

**역할**: routers(HTTP) → services(로직) → database(DB)

### 프론트엔드 파일 구조

```
frontend/src/
├── pages/        # 라우트 컴포넌트
├── components/   # 재사용 컴포넌트 (layout, etf, common)
├── hooks/        # Custom Hooks
├── services/     # API 클라이언트
└── utils/        # 유틸리티 함수
```

---

## 네이밍 규칙

### 백엔드 (Python)

```python
# 변수/함수: snake_case
user_data = get_user_data()

# 클래스: PascalCase
class ETFDataCollector:
    pass

# 상수: UPPER_CASE
MAX_RETRY_COUNT = 3

# Private: 언더스코어 prefix
def _internal_helper():
    pass
```

### 프론트엔드 (JavaScript/React)

```javascript
// 변수/함수: camelCase
const userData = getUserData()

// 컴포넌트: PascalCase
function ETFCard() {}

// 상수: UPPER_CASE
const API_BASE_URL = 'http://localhost:8000'

// 파일명:
// - 컴포넌트: PascalCase (ETFCard.jsx)
// - 유틸리티: camelCase (formatters.js)
```

---

## Git 워크플로우

### 브랜치 전략

```
main (프로덕션)
├── develop (개발)
│   ├── feature/dashboard
│   ├── feature/data-collection
│   └── fix/api-error
```

### 커밋 메시지 규칙

```
type(scope): subject

body (optional)

footer (optional)
```

**Type:**
- `feat`: 새로운 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅
- `refactor`: 리팩토링
- `test`: 테스트 추가
- `chore`: 빌드/설정 변경

**예시**: `feat(backend): ETF 가격 데이터 수집 기능 추가`

---

## 테스트 전략

> **⚠️ 중요**: 모든 기능은 테스트 100% 완료 후 다음 단계로 진행합니다.  
> 자세한 내용은 **[Definition of Done](./DEFINITION_OF_DONE.md)** 참조

### 테스트 정책

- **커버리지 목표**: 백엔드 80%, 프론트엔드 70%, Critical Path 100%
- **테스트 종류**: 유닛 테스트, 통합 테스트, E2E 테스트
- **패턴**: Given-When-Then 구조 사용

---

## 데이터 수집 전략

### 수집 타이밍

1. **초기 로드**: 최근 1년 히스토리 데이터
2. **일일 업데이트**: 장 마감 후 15:30 KST
3. **실시간 업데이트**: 사용자 요청 시 (캐시 TTL: 10분)

### 에러 처리 패턴
- 재시도 로직: Exponential Backoff 사용
- Rate Limiting: 요청 간 최소 간격 보장

---

## 성능 최적화

### 백엔드
- 비동기 I/O: `async/await`, `asyncio.gather()` 사용
- 데이터베이스 인덱스: 자주 조회하는 컬럼에 인덱스 생성
- 쿼리 최적화: N+1 쿼리 방지, 단일 쿼리 사용

### 프론트엔드
- React.memo: 불필요한 리렌더링 방지
- Code Splitting: `React.lazy()` 사용
- 이미지 최적화: `loading="lazy"`, width/height 지정

---

## 한국어 처리

### 인코딩

- 모든 파일: **UTF-8**
- HTTP 헤더: `Content-Type: application/json; charset=utf-8`

### 폰트

```css
/* TailwindCSS 설정 */
@layer base {
  body {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  }
}
```

### 금액/날짜 포맷팅
- `Intl.NumberFormat`: 금액 포맷팅 (한국어, KRW)
- `Intl.DateTimeFormat`: 날짜 포맷팅 (한국어)

---

## 보안 체크리스트

- [ ] `.env` 파일을 `.gitignore`에 추가
- [ ] CORS 설정: 허용된 origin만 명시
- [ ] SQL Injection 방지: 파라미터화된 쿼리 사용
- [ ] XSS 방지: 사용자 입력 sanitize
- [ ] API Rate Limiting 구현
- [ ] HTTPS 사용 (프로덕션)
- [ ] 민감한 정보 로깅 금지

---

**Last Updated**: 2025-11-06

