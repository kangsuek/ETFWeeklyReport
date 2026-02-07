# 개발 가이드

## 코드 품질 표준

### Python (백엔드)
- **PEP 8** 준수, 4 spaces 들여쓰기
- 타입 힌트 사용, Docstring 필수
- 비동기 I/O: `async/await` 사용

### JavaScript/React (프론트엔드)
- **ESLint** 규칙 준수, 2 spaces 들여쓰기
- 함수형 컴포넌트 + Hooks
- Props 문서화 (PropTypes 필수, JSDoc 권장)

## 프로젝트 구조
상세 구조는 [ARCHITECTURE.md](./ARCHITECTURE.md), [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) 참고.

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
- **테스트 정책**: [AGENTS.md](../AGENTS.md) 참고

## 성능 최적화

### 백엔드
- 비동기 I/O: `async/await`, `asyncio.gather()`
- 데이터베이스 인덱스 최적화

### 프론트엔드
- React.memo: 불필요한 리렌더링 방지
- Code Splitting: `React.lazy()` 사용

## 보안
상세 항목은 [SECURITY_CHECKLIST.md](./SECURITY_CHECKLIST.md) 참고.
