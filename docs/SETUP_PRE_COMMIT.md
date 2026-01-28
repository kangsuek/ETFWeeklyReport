# Pre-commit Hooks 설정 가이드

## 📋 개요

Pre-commit hooks를 설정하여 커밋 전 자동으로 코드 품질 검사 및 포매팅을 수행합니다.
**통합 설정**: 프로젝트 루트에 하나의 설정 파일로 백엔드와 프론트엔드를 모두 관리합니다.

---

## 🚀 빠른 시작 (권장)

### 통합 설정 (프로젝트 루트)

```bash
# 프로젝트 루트에서
cd /Users/kangsuek/pythonProject/ETFWeeklyReport

# 1. 백엔드 가상환경 생성 (아직 없다면)
cd backend
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements-dev.txt
cd ..

# 2. 통합 Pre-commit hooks 설정
./scripts/setup-pre-commit.sh
```

이제 백엔드와 프론트엔드 모두 자동으로 검사됩니다!

---

## 🔧 개별 설정 (선택사항)

### 백엔드만 설정

```bash
cd backend

# 1. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 2. 개발 의존성 설치
pip install -r requirements-dev.txt

# 3. Pre-commit hooks 설정
./scripts/setup-pre-commit.sh
```

**참고**: 프론트엔드는 별도로 설정할 필요가 없습니다. 통합 설정이 프론트엔드도 포함합니다.

---

## 🔧 수동 설정 방법

### 백엔드

```bash
cd backend

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux

# pre-commit 설치
pip install pre-commit

# hooks 설치
pre-commit install

# 모든 파일에 대해 한 번 실행 (선택사항)
pre-commit run --all-files
```

### 프론트엔드

```bash
cd frontend

# pre-commit 설치
npm install -g pre-commit
# 또는 로컬 설치
npm install --save-dev pre-commit

# hooks 설치
pre-commit install
```

---

## ⚠️ 문제 해결

### 문제 1: `command not found: pip`

**원인**: 가상환경이 활성화되지 않았거나 `pip3`를 사용해야 함

**해결**:
```bash
# 가상환경 생성 및 활성화
cd backend
python3 -m venv venv
source venv/bin/activate

# pip 확인
which pip
pip --version
```

### 문제 2: `command not found: pre-commit`

**원인**: pre-commit이 설치되지 않음

**해결**:
```bash
# 가상환경 활성화 후
pip install pre-commit

# 또는 시스템 전역 설치
pip3 install --user pre-commit
```

### 문제 3: `npm error could not determine executable to run`

**원인**: `pre-commit`은 Python 패키지이므로 npm/npx로 실행할 수 없습니다.

**해결**: 프로젝트 루트에서 Python pre-commit을 사용하세요:
```bash
# 프로젝트 루트에서
cd /Users/kangsuek/pythonProject/ETFWeeklyReport

# 백엔드 가상환경 활성화
cd backend
source venv/bin/activate
cd ..

# 통합 설정 스크립트 실행
./scripts/setup-pre-commit.sh
```

### 문제 4: 가상환경이 없는 경우

**해결**:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
./scripts/setup-pre-commit.sh
```

---

## 📝 Pre-commit Hooks 목록

### 백엔드

- **Black**: 코드 포매팅 (line-length: 100)
- **isort**: import 정렬 (black profile)
- **Flake8**: 스타일 검사 (max-line-length: 100)
- **일반 파일 검사**: trailing whitespace, end-of-file, YAML/JSON 검증 등

### 프론트엔드

- **ESLint**: JavaScript/React 코드 검사
- **일반 파일 검사**: trailing whitespace, end-of-file, JSON 검증 등

---

## 🎯 사용법

### 커밋 시 자동 실행

```bash
git add .
git commit -m "Your commit message"
# Pre-commit hooks가 자동으로 실행됨
```

### 수동 실행

```bash
# 모든 파일에 대해 실행
pre-commit run --all-files

# 특정 hook만 실행
pre-commit run black
pre-commit run flake8
pre-commit run eslint
```

### 특정 파일만 검사

```bash
pre-commit run --files app/main.py
pre-commit run --files frontend/src/components/App.jsx
```

---

## 🔍 설정 파일 위치

- **통합 설정** (권장): `.pre-commit-config.yaml` (프로젝트 루트)
- **백엔드 전용**: `backend/.pre-commit-config.yaml` (개별 설정 시)
- **프론트엔드 전용**: `frontend/.pre-commit-config.yaml` (개별 설정 시)

**참고**: 통합 설정을 사용하면 프로젝트 루트의 `.pre-commit-config.yaml`만 사용됩니다.

---

## 💡 팁

1. **첫 실행 시 시간 소요**: Pre-commit hooks는 첫 실행 시 필요한 도구들을 자동으로 설치합니다.

2. **Hook 건너뛰기** (비상시):
   ```bash
   git commit --no-verify -m "Emergency commit"
   ```

3. **특정 Hook 비활성화**: `.pre-commit-config.yaml`에서 해당 hook을 주석 처리

4. **업데이트**:
   ```bash
   pre-commit autoupdate
   ```

---

## ✅ 검증

설정이 올바르게 되었는지 확인:

```bash
# 백엔드
cd backend
pre-commit run --all-files

# 프론트엔드
cd frontend
pre-commit run --all-files
```

모든 hook이 통과하면 설정이 완료된 것입니다!
