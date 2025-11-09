# 🚀 Quick Start 가이드

## 새로운 세션에서 바로 시작하기

### 1️⃣ 현재 상황 파악 (1분)

#### 프로젝트 배경
- 메인 프로젝트에서 뉴스 스크래핑이 **Mock 데이터**로 구현됨
- 실시간 뉴스 수집을 위해 **서브프로젝트**로 별도 개발
- **네이버 검색 API** 사용으로 결정 (Selenium/Playwright 제외)

#### 작업 위치
```bash
cd /Users/kangsuek/pythonProject/ETFWeeklyReport/backend/prototypes/news_scraper_poc/
```

---

### 2️⃣ 문서 읽기 (3분)

**필수 문서 (순서대로 읽기):**
1. `README.md` - 프로젝트 개요 및 API 스펙
2. `WORK_INSTRUCTION.md` - 상세 작업 지시서 ⭐ **가장 중요**
3. `STEP1_PLAN.md` - 1단계 세부 계획

---

### 3️⃣ 작업 시작 (1시간)

#### Task 1.1: 환경 설정 (10분)

**1. `.env` 파일 생성**
```bash
cat > .env << 'EOF'
NAVER_CLIENT_ID=your_client_id_here
NAVER_CLIENT_SECRET=your_client_secret_here
EOF
```
**⚠️ 주의**: 실제 API 키는 네이버 개발자 센터에서 발급받아 `.env` 파일에 입력하세요. `.env` 파일은 Git에 커밋하지 마세요!

**2. `requirements.txt` 생성**
```bash
cat > requirements.txt << 'EOF'
requests==2.31.0
python-dotenv==1.0.0
EOF
```

**3. 패키지 설치**
```bash
# 백엔드 가상환경 활성화
cd ../../
source venv/bin/activate
cd prototypes/news_scraper_poc/

# 패키지 설치
pip install -r requirements.txt
```

---

#### Task 1.2: API 호출 스크립트 작성 (20분)

**`naver_news_api.py` 파일 생성:**

```python
import os
import requests
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

def search_news(query, display=10, start=1, sort="date"):
    """
    네이버 뉴스 검색 API 호출
    
    Args:
        query: 검색 키워드
        display: 검색 결과 개수 (1-100)
        start: 검색 시작 위치 (1-1000)
        sort: 정렬 방식 (sim: 정확도, date: 날짜)
    
    Returns:
        dict: API 응답 JSON
    """
    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET
    }
    
    params = {
        "query": query,
        "display": display,
        "start": start,
        "sort": sort
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print("❌ 인증 실패: Client ID/Secret 확인")
        elif response.status_code == 403:
            print("❌ API 권한 없음")
        elif response.status_code == 429:
            print("❌ Rate Limit 초과")
        else:
            print(f"❌ HTTP 에러: {e}")
        raise
    except Exception as e:
        print(f"❌ 오류: {e}")
        raise

if __name__ == "__main__":
    # 테스트
    result = search_news("AI", display=5)
    print(f"검색 결과: {result['total']}건")
    print(f"수집된 뉴스: {len(result['items'])}건")
```

---

#### Task 1.3: 테스트 스크립트 작성 (15분)

**`test_basic.py` 파일 생성:**

```python
from naver_news_api import search_news
import time

def test_search_news():
    print("=" * 50)
    print("네이버 뉴스 API 테스트")
    print("=" * 50)
    
    keyword = "AI"
    start_time = time.time()
    
    try:
        result = search_news(keyword, display=10, sort="date")
        elapsed_time = time.time() - start_time
        
        print(f"검색 키워드: {keyword}")
        print(f"검색 결과: {len(result['items'])}건 / 전체 {result['total']:,}건")
        print(f"응답 시간: {elapsed_time:.2f}초")
        print("=" * 50)
        print()
        
        for i, item in enumerate(result['items'], 1):
            print(f"[{i}] 제목: {item['title']}")
            print(f"    URL: {item['link']}")
            print(f"    날짜: {item['pubDate']}")
            print(f"    요약: {item['description'][:100]}...")
            print()
        
        # 검증
        assert len(result['items']) == 10, "결과 개수 불일치"
        assert 'title' in result['items'][0], "title 필드 없음"
        assert 'link' in result['items'][0], "link 필드 없음"
        assert 'pubDate' in result['items'][0], "pubDate 필드 없음"
        assert elapsed_time < 2.0, "응답 시간 초과"
        
        print("✅ 모든 테스트 통과!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        raise

if __name__ == "__main__":
    test_search_news()
```

**실행:**
```bash
python test_basic.py
```

---

#### Task 1.4: HTML 태그 제거 및 날짜 파싱 (10분)

**`naver_news_api.py`에 유틸리티 함수 추가:**

```python
import re
from datetime import datetime

def clean_html_tags(text):
    """HTML 태그 제거"""
    return re.sub(r'<[^>]+>', '', text)

def parse_pubdate(pubdate_str):
    """pubDate를 YYYY-MM-DD 형식으로 변환"""
    dt = datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")
    return dt.strftime("%Y-%m-%d")
```

**`test_basic.py`에 적용:**

```python
from naver_news_api import search_news, clean_html_tags, parse_pubdate

# ... (이전 코드)

for i, item in enumerate(result['items'], 1):
    title_clean = clean_html_tags(item['title'])
    desc_clean = clean_html_tags(item['description'])
    date_formatted = parse_pubdate(item['pubDate'])
    
    print(f"[{i}] 제목: {title_clean}")
    print(f"    URL: {item['link']}")
    print(f"    날짜: {date_formatted}")
    print(f"    요약: {desc_clean[:100]}...")
    print()
```

---

#### Task 1.5: 결과 문서화 (5분)

**`STEP1_RESULT.md` 작성:**

실제 실행 결과를 복사해서 붙여넣고 아래 템플릿 작성:

```markdown
# 1단계 결과 보고서

## ✅ 성공 여부
- [x] API 호출 성공
- [x] 10개 뉴스 수집 성공
- [x] 응답 필드 완전성 확인
- [x] HTML 태그 제거 성공
- [x] 날짜 파싱 성공

## 📊 성능 지표
- API 호출 성공률: 100%
- 평균 응답 시간: X.XX초
- 수집된 뉴스 개수: 10건

## 📝 수집된 데이터 샘플
(실제 출력 결과 붙여넣기)

## 🎯 다음 단계
2단계: 다중 키워드 및 필터링
```

---

### 4️⃣ 완료 확인 (1분)

#### 체크리스트
- [ ] `.env` 파일 생성
- [ ] `requirements.txt` 생성 및 설치
- [ ] `naver_news_api.py` 작성
- [ ] `test_basic.py` 작성 및 실행 성공
- [ ] 10개 뉴스 수집 성공
- [ ] HTML 태그 제거 확인
- [ ] 날짜 파싱 확인
- [ ] `STEP1_RESULT.md` 작성

#### 예상 결과
```
========================================
네이버 뉴스 API 테스트
========================================
검색 키워드: AI
검색 결과: 10건 / 전체 1,234,567건
응답 시간: 0.5초
========================================

[1] 제목: AI 기술 발전...
    URL: https://...
    날짜: 2025-11-08
    요약: ...

✅ 모든 테스트 통과!
```

---

### 5️⃣ 다음 단계

1단계 완료 후:
- `STEP1_RESULT.md` 내용을 메인 세션에 공유
- 2단계 진행 (다중 키워드 및 필터링)

---

## 💡 문제 해결

### 401 에러 발생 시
```bash
# .env 파일 확인
cat .env

# Client ID/Secret 재확인
```

### 패키지 설치 오류
```bash
# 가상환경 확인
which python
# /Users/kangsuek/pythonProject/ETFWeeklyReport/backend/venv/bin/python

# 재설치
pip install --upgrade requests python-dotenv
```

---

## 📞 도움말

- **상세 지침**: `WORK_INSTRUCTION.md`
- **API 문서**: https://developers.naver.com/docs/serviceapi/search/news/news.md
- **에러 코드**: `WORK_INSTRUCTION.md`의 "에러 코드" 섹션 참조

---

**🎉 준비 완료! 바로 시작하세요!**

