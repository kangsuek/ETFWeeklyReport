# ETF Weekly Report - 문서 인덱스

이 프로젝트는 한국 고성장 섹터 4개 ETF에 대한 종합 분석 및 리포팅 웹 애플리케이션입니다.

---

## 📚 프로젝트 문서

### 정적 문서 (참조용)

프로젝트의 핵심 설계 및 명세를 담은 문서입니다. 자주 변경되지 않습니다.

1. **[시스템 아키텍처](./docs/ARCHITECTURE.md)**
   - 전체 시스템 구조
   - 백엔드/프론트엔드 아키텍처
   - 데이터 흐름
   - 배포 구조

2. **[API 명세서](./docs/API_SPECIFICATION.md)**
   - REST API 엔드포인트 목록
   - 요청/응답 형식
   - 에러 코드

3. **[데이터베이스 스키마](./docs/DATABASE_SCHEMA.md)**
   - ERD 다이어그램
   - 테이블 정의
   - 쿼리 예시

4. **[기술 스택](./docs/TECH_STACK.md)**
   - 사용 기술 목록
   - 버전 정보
   - 선택 이유

5. **[개발 가이드](./docs/DEVELOPMENT_GUIDE.md)**
   - 코딩 컨벤션
   - 네이밍 규칙
   - Git 워크플로우
   - 테스트 전략

---

### 동적 문서 (진행 상황)

프로젝트 진행 상황 및 할 일을 추적하는 문서입니다. 자주 업데이트됩니다.

1. **[할 일 목록](./project-management/TODO.md)**
   - Phase별 작업 목록
   - 우선순위
   - 완료 여부
   - Acceptance Criteria

2. **[진행 상황](./project-management/PROGRESS.md)**
   - 날짜별 작업 기록
   - 완료된 작업
   - 이슈 및 해결 방안

3. **[마일스톤](./project-management/MILESTONES.md)**
   - 프로젝트 일정
   - Phase별 목표 및 완료 조건
   - 리스크 관리

---

### 품질 기준

1. **[Definition of Done](./docs/DEFINITION_OF_DONE.md)** ⭐ 중요
   - 작업 완료 기준
   - 테스트 정책
   - Phase별 필수 체크리스트
   - **모든 기능은 테스트 100% 완료 후 다음 단계 진행**

---

## 🚀 빠른 시작

### 문서 읽는 순서 (처음 시작하는 경우)

1. **[README.md](./README.md)** - 프로젝트 개요 및 빠른 시작
2. **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)** - 시스템 구조 파악
3. **[docs/TECH_STACK.md](./docs/TECH_STACK.md)** - 사용 기술 확인
4. **[project-management/TODO.md](./project-management/TODO.md)** - 현재 할 일 확인
5. **[docs/DEVELOPMENT_GUIDE.md](./docs/DEVELOPMENT_GUIDE.md)** - 개발 시작

### 개발 중 참조할 문서

- API 구현 시: **[docs/API_SPECIFICATION.md](./docs/API_SPECIFICATION.md)**
- DB 작업 시: **[docs/DATABASE_SCHEMA.md](./docs/DATABASE_SCHEMA.md)**
- 코딩 중: **[docs/DEVELOPMENT_GUIDE.md](./docs/DEVELOPMENT_GUIDE.md)**
- 진행 상황 체크: **[project-management/PROGRESS.md](./project-management/PROGRESS.md)**

---

## 📊 프로젝트 현황

- **시작일**: 2025-11-05
- **현재 Phase**: Phase 1 (Backend Core)
- **전체 진행률**: 약 10%
- **다음 마일스톤**: Phase 1 완료 (2025-11-10 예정)

자세한 내용은 **[project-management/MILESTONES.md](./project-management/MILESTONES.md)** 참조

---

## 🎯 대상 ETF

1. **KODEX AI전력핵심설비** (480450) - AI & 전력 인프라
2. **SOL 조선TOP3플러스** (456600) - 조선업
3. **KOACT 글로벌양자컴퓨팅액티브** (497450) - 양자컴퓨팅
4. **KBSTAR 글로벌원자력 iSelect** (481330) - 원자력

---

## 💡 문서 구조 개선 (2025-11-06)

### 이전 구조
- 단일 CLAUDE.md 파일 (630줄)
- 정적 정보와 동적 정보가 혼재
- 매번 전체 파일을 읽어야 함 → 토큰 낭비

### 현재 구조
- **docs/** : 정적 문서 (6개 파일, 자주 수정 안 함)
- **project-management/** : 동적 문서 (3개 파일, 자주 업데이트)
- 필요한 문서만 선택적으로 읽을 수 있음
- 각 문서는 100~300줄로 관리 용이

### 장점
✅ 토큰 사용 효율성 향상 (630줄 → 필요한 부분만 50~200줄)  
✅ 변경 이력 추적 용이  
✅ 협업 시 충돌 최소화  
✅ 유지보수 편리

---

## 📞 문의

프로젝트 관련 질문이나 제안 사항이 있으면 이슈를 생성해주세요.

---

**Last Updated**: 2025-11-06
