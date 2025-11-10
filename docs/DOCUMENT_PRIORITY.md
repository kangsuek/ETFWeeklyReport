# 문서 우선순위 및 필요성 분석

## 📋 문서 분류 기준

### 필수 문서 (Essential)
새 에이전트가 작업을 시작하기 위해 반드시 읽어야 하는 문서

### 선택 문서 (Optional)
참조용이거나 특정 상황에서만 필요한 문서

### 불필요 문서 (Unnecessary)
개발 작업에 직접적으로 필요하지 않은 문서

---

## ✅ 필수 문서 (Essential) - 11개

### 시작 문서
1. **CLAUDE.md** ⭐
   - 목적: 문서 인덱스 및 프로젝트 개요
   - 필요성: 새 에이전트의 시작점

2. **README.md** ⭐
   - 목적: 프로젝트 개요 및 빠른 시작
   - 필요성: 프로젝트 이해 및 환경 설정

### 핵심 설계 문서
3. **docs/ARCHITECTURE.md** ⭐
   - 목적: 시스템 구조 및 아키텍처
   - 필요성: 전체 시스템 이해

4. **docs/TECH_STACK.md** ⭐
   - 목적: 사용 기술 및 버전 정보
   - 필요성: 기술 스택 확인

5. **docs/API_SPECIFICATION.md** ⭐
   - 목적: REST API 엔드포인트 명세
   - 필요성: API 구현 및 사용

6. **docs/DATABASE_SCHEMA.md** ⭐
   - 목적: 데이터베이스 스키마 및 ERD
   - 필요성: DB 작업 시 필수

### 개발 가이드
7. **docs/SETUP_GUIDE.md** ⭐
   - 목적: 개발 환경 설정 방법
   - 필요성: 초기 환경 설정

8. **docs/DEVELOPMENT_GUIDE.md** ⭐
   - 목적: 코딩 컨벤션 및 개발 가이드
   - 필요성: 코드 작성 표준

9. **docs/DEFINITION_OF_DONE.md** ⭐
   - 목적: 작업 완료 기준 및 테스트 정책
   - 필요성: 작업 완료 여부 판단

10. **docs/RUNNING_GUIDE.md** ⭐
    - 목적: 서버 실행 및 테스트 방법
    - 필요성: 개발 중 서버 실행

### 프로젝트 관리
11. **project-management/TODO.md** ⭐
    - 목적: 현재 할 일 및 Phase별 작업 목록
    - 필요성: 현재 작업 확인

---

## 📚 선택 문서 (Optional) - 8개

### 참조용 문서
1. **project-management/PROGRESS.md**
   - 목적: 날짜별 작업 기록 및 완료 내역
   - 필요성: 과거 작업 확인 (필요 시만)
   - 읽기 시점: 특정 작업의 과거 이력 확인 시

2. **project-management/MILESTONES.md**
   - 목적: 프로젝트 일정 및 마일스톤
   - 필요성: 전체 일정 파악 (필요 시만)
   - 읽기 시점: 일정 확인 필요 시

3. **docs/DATA_COLLECTION_DESIGN.md**
   - 목적: 데이터 수집 설계 문서
   - 필요성: 데이터 수집 로직 이해 (필요 시만)
   - 읽기 시점: 데이터 수집 기능 수정 시

4. **frontend/DEPLOYMENT.md**
   - 목적: 프론트엔드 배포 가이드
   - 필요성: 배포 시에만 필요
   - 읽기 시점: 배포 작업 시

5. **backend/README.md**
   - 목적: 백엔드 가이드
   - 필요성: 백엔드 전용 정보 (중복 가능)
   - 읽기 시점: 백엔드 작업 시

6. **frontend/README.md**
   - 목적: 프론트엔드 가이드
   - 필요성: 프론트엔드 전용 정보 (중복 가능)
   - 읽기 시점: 프론트엔드 작업 시

### 프로토타입 문서 (완료된 작업)
7. **backend/prototypes/news_scraper_poc/** (전체 디렉토리)
   - 목적: 뉴스 스크래핑 POC 프로젝트 문서
   - 필요성: 이미 완료된 프로토타입 (참조용)
   - 읽기 시점: 뉴스 스크래핑 로직 이해 필요 시
   - 포함 파일:
     - README.md
     - WORK_INSTRUCTION.md
     - STEP1_PLAN.md, STEP1_RESULT.md
     - STEP2_RESULT.md, STEP3_RESULT.md
     - QUICK_START.md
     - 새_세션_시작_방법.md

8. **backend/data/data_quality_report.md**
   - 목적: 데이터 품질 리포트
   - 필요성: 데이터 품질 확인 (필요 시만)
   - 읽기 시점: 데이터 품질 검증 시

---

## ✅ 제거 완료 문서 (Removed) - 5개

### 최적화 관련 문서 (제거 완료)
1. ✅ **docs/DOCUMENT_OPTIMIZATION_PLAN.md** - 제거 완료 (2025-11-09)
2. ✅ **docs/PHASE2_OPTIMIZATION_DETAILS.md** - 제거 완료 (2025-11-09)
3. ✅ **docs/CODE_EXAMPLE_ANALYSIS.md** - 제거 완료 (2025-11-09)

### 개선 제안 문서 (제거 완료)
4. ✅ **docs/CODE_IMPROVEMENTS.md** - 제거 완료 (2025-11-09)

### Phase별 계획 문서 (제거 완료)
5. ✅ **project-management/PHASE4_PLAN.md** - 제거 완료 (2025-11-09)

---

## 📊 문서 읽기 우선순위 (새 에이전트 실행 시)

### 1단계: 필수 문서 (반드시 읽기)
```
1. CLAUDE.md
2. README.md
3. docs/ARCHITECTURE.md
4. docs/TECH_STACK.md
5. docs/SETUP_GUIDE.md
6. docs/DEVELOPMENT_GUIDE.md
7. docs/DEFINITION_OF_DONE.md
8. project-management/TODO.md
```

### 2단계: 작업별 선택 문서 (필요 시만)
- **API 작업**: `docs/API_SPECIFICATION.md`
- **DB 작업**: `docs/DATABASE_SCHEMA.md`
- **서버 실행**: `docs/RUNNING_GUIDE.md`
- **배포 작업**: `frontend/DEPLOYMENT.md`

### 3단계: 참조 문서 (필요 시만)
- 과거 작업 확인: `project-management/PROGRESS.md`
- 일정 확인: `project-management/MILESTONES.md`
- 데이터 수집 로직: `docs/DATA_COLLECTION_DESIGN.md`

---

## ✅ 제거 완료 문서 목록

### 제거 완료 (2025-11-09)
1. ✅ `docs/DOCUMENT_OPTIMIZATION_PLAN.md` - 제거 완료
2. ✅ `docs/PHASE2_OPTIMIZATION_DETAILS.md` - 제거 완료
3. ✅ `docs/CODE_EXAMPLE_ANALYSIS.md` - 제거 완료
4. ✅ `project-management/PHASE4_PLAN.md` - 제거 완료
5. ✅ `docs/CODE_IMPROVEMENTS.md` - 제거 완료

**제거된 줄 수**: 약 2,148줄  
**절감된 토큰**: 약 8,592 토큰

### 보관 문서 (참고용, 개발 작업에는 불필요)
- `backend/prototypes/news_scraper_poc/` - 완료된 POC 문서 (참고용)
- `backend/data/data_quality_report.md` - 데이터 품질 리포트 (참고용)

---

## ✅ 최적화 완료

### 제거 완료 효과

**제거된 문서**:
- 최적화 관련 문서 3개: 약 1,000줄 (약 4,000 토큰)
- PHASE4_PLAN.md: 약 700줄 (약 2,800 토큰)
- CODE_IMPROVEMENTS.md: 약 618줄 (약 2,472 토큰)
- **총 제거**: 약 2,148줄 (약 8,592 토큰)

**최적화 전후 비교**:
- Phase 1+2 최적화 후: 약 8,564 토큰
- 불필요 문서 제거 후: 약 0 토큰 (제거된 문서)
- **필수 문서 8개**: 약 2,448줄 (약 9,792 토큰)

**총 절감 효과**:
- 원본 문서: 약 10,400 토큰
- 최종 필수 문서: 약 9,792 토큰
- **총 절감**: 약 608 토큰 (5.8% 감소)
- **제거된 문서**: 약 2,148줄 (약 8,592 토큰)

---

## 📝 권장 사항

### 새 에이전트 실행 시 읽을 문서 (최소)
1. CLAUDE.md
2. README.md
3. docs/ARCHITECTURE.md
4. docs/TECH_STACK.md
5. docs/SETUP_GUIDE.md
6. docs/DEVELOPMENT_GUIDE.md
7. docs/DEFINITION_OF_DONE.md
8. project-management/TODO.md

**총 8개 문서** (약 2,448줄, 약 9,792 토큰)

### 작업별 추가 문서
- API 작업: + API_SPECIFICATION.md
- DB 작업: + DATABASE_SCHEMA.md
- 서버 실행: + RUNNING_GUIDE.md

---

**작성일**: 2025-11-09
**목적**: 문서 우선순위 명확화 및 토큰 수 추가 절감 방안 제시

