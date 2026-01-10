# Perplexity AI 연동 개발 계획서

## 📋 프로젝트 개요

**목표**: ETF 종목 상세 페이지에서 Perplexity AI를 활용하여 종목 관련 실시간 인사이트 제공

**기대 효과**:
- 종목에 대한 심층 분석 및 시장 동향 파악
- 최신 뉴스 및 전문가 의견 요약
- 투자 판단에 필요한 추가 정보 제공

---

## 🎯 요구사항 분석

### 기능 요구사항

1. **종목별 AI 분석 조회**
   - 종목 상세 페이지에서 Perplexity AI 분석 요청
   - 종목명, 테마, 최근 데이터를 기반으로 자동 질의 생성
   - AI 응답을 마크다운 형식으로 표시

2. **질의 템플릿**
   
   **템플릿 파일**: `promptTemplet/Perplexity_prompt.md`
   
   상세한 12개 섹션으로 구성된 종합 투자분석 보고서 템플릿을 사용합니다:
   
   1. 주간 시장 데이터 분석 (최근 7거래일)
   2. 기술적 분석 (이동평균, RSI, MACD 등)
   3. 시장 환경 및 섹터 분석
   4. 일자별 주요 뉴스 및 이벤트
   5. 매매동향 및 수급 분석
   6. ETF 펀더멘털 지표
   7. 구성종목 세부분석 (상위 10대)
   8. 비교 분석표
   9. 향후 전망 및 거래 시그널
   10. 투자 포인트 및 리스크
   11. 투자자 유형별 추천
   12. 종합 의견 및 액션플랜
   
   **동적 치환**:
   - `{종목명}` → ETF 이름 (예: "HANARO Fn K-반도체")
   - `{티커}` → 종목 코드 (예: "395270")

3. **사용자 인터페이스**
   - 종목 상세 페이지에 "AI 분석" 탭 또는 섹션 추가
   - 로딩 상태 표시 (응답까지 5-10초 소요)
   - 에러 처리 및 재시도 기능
   - 마지막 업데이트 시간 표시

4. **캐싱 전략**
   - 동일 종목 질의 결과 24시간 캐싱
   - 비용 절감 및 응답 속도 개선

### 비기능 요구사항

1. **보안**
   - API Key 환경변수로 관리 (`.env`)
   - 백엔드에서만 API 호출 (프론트엔드 노출 방지)

2. **비용 관리**
   - Perplexity API 호출 횟수 제한
   - Rate limiting 적용
   - 캐싱으로 중복 요청 방지

3. **성능**
   - 비동기 처리로 페이지 로딩 차단 방지
   - 타임아웃 설정 (30초)

---

## 🏗️ 시스템 아키텍처

### 전체 흐름

```
[프론트엔드: ETFDetail.jsx]
         ↓ (1) AI 분석 요청
[백엔드: /api/etfs/{ticker}/ai-analysis]
         ↓ (2) 캐시 확인
[캐시: Redis/메모리]
         ↓ (3) 캐시 없으면
[Perplexity API]
         ↓ (4) 응답 저장
[캐시 + 데이터베이스]
         ↓ (5) 응답 반환
[프론트엔드: 마크다운 렌더링]
```

### 데이터 모델

**1. 데이터베이스 테이블 (ai_insights)**
```sql
CREATE TABLE ai_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    source TEXT DEFAULT 'perplexity',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    token_count INTEGER,
    FOREIGN KEY (ticker) REFERENCES etfs(ticker) ON DELETE CASCADE
);

CREATE INDEX idx_ai_insights_ticker ON ai_insights(ticker);
CREATE INDEX idx_ai_insights_expires ON ai_insights(expires_at);
```

**2. API 응답 형식**
```json
{
  "ticker": "395270",
  "name": "HANARO Fn K-반도체",
  "question": "HANARO Fn K-반도체 ETF의 최근 시장 동향과 전망은?",
  "answer": "### 시장 동향\n\n...",
  "sources": [
    {
      "title": "...",
      "url": "...",
      "snippet": "..."
    }
  ],
  "created_at": "2026-01-10T12:00:00",
  "cached": false
}
```

---

## 📦 구현 계획

### Phase 1: 백엔드 API 구현 (우선순위: 높음)

#### 1.1 Perplexity API 클라이언트 작성
**파일**: `backend/app/services/perplexity_client.py`

```python
import os
import httpx
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class PerplexityClient:
    """Perplexity AI API 클라이언트"""
    
    BASE_URL = "https://api.perplexity.ai"
    
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in environment")
    
    async def ask(
        self,
        query: str,
        model: str = "llama-3.1-sonar-large-128k-online",
        timeout: int = 30
    ) -> Dict:
        """
        Perplexity AI에 질의하고 응답 받기
        
        Args:
            query: 질문 내용
            model: 사용할 모델 (기본: sonar-large)
            timeout: 타임아웃 (초)
            
        Returns:
            Dict: {
                "answer": str,
                "sources": List[Dict],
                "usage": Dict
            }
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 한국 주식 및 ETF 시장 전문가입니다. 상세하고 객관적인 투자분석 보고서를 작성하세요."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.2,
            "max_tokens": 8000,  # 상세한 보고서용으로 증가
            "return_citations": True,
            "search_recency_filter": "month"  # 최근 1개월 정보 우선
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                return {
                    "answer": data["choices"][0]["message"]["content"],
                    "sources": data.get("citations", []),
                    "usage": data.get("usage", {})
                }
                
        except httpx.TimeoutException:
            logger.error("Perplexity API timeout")
            raise
        except httpx.HTTPError as e:
            logger.error(f"Perplexity API error: {e}")
            raise
```

#### 1.2 AI 분석 서비스 작성
**파일**: `backend/app/services/ai_analysis_service.py`

```python
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
from app.database import get_db_connection
from app.services.perplexity_client import PerplexityClient
from app.config import Config

logger = logging.getLogger(__name__)

class AIAnalysisService:
    """ETF AI 분석 서비스"""
    
    def __init__(self):
        self.perplexity = PerplexityClient()
        self.cache_duration = 24  # 24시간
        self.prompt_template_path = Path(__file__).parent.parent.parent / "promptTemplet" / "Perplexity_prompt.md"
    
    def _load_prompt_template(self) -> str:
        """프롬프트 템플릿 파일 로드"""
        try:
            with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt template not found: {self.prompt_template_path}")
            # 폴백: 간단한 기본 템플릿 사용
            return """
{종목명} ETF({티커})에 대한 종합 투자분석을 작성해주세요.

1. 최근 시장 동향
2. 기술적 분석
3. 투자 포인트 및 리스크
4. 향후 전망

답변은 한국어로 작성하고, 객관적인 데이터에 기반하여 작성해주세요.
            """.strip()
    
    def _generate_question(self, etf_info: Dict) -> str:
        """종목 정보 기반 질문 생성 (템플릿 사용)"""
        ticker = etf_info['ticker']
        name = etf_info['name']
        
        # 템플릿 로드
        template = self._load_prompt_template()
        
        # 동적 치환 (종목명, 티커만 사용)
        question = template.replace("{종목명}", name)
        question = question.replace("{티커}", ticker)
        
        logger.info(f"Generated question for {ticker} using template")
        return question
    
    async def get_analysis(self, ticker: str) -> Dict:
        """
        ETF AI 분석 조회 (캐시 우선)
        
        Args:
            ticker: 종목 코드
            
        Returns:
            Dict: AI 분석 결과
        """
        # 1. 캐시 확인
        cached = self._get_from_cache(ticker)
        if cached:
            logger.info(f"Cache hit for {ticker}")
            cached['cached'] = True
            return cached
        
        # 2. ETF 정보 조회
        etf_info = self._get_etf_info(ticker)
        if not etf_info:
            raise ValueError(f"ETF {ticker} not found")
        
        # 3. 질문 생성
        question = self._generate_question(etf_info)
        
        # 4. Perplexity AI 호출
        logger.info(f"Calling Perplexity API for {ticker}")
        result = await self.perplexity.ask(question)
        
        # 5. 결과 저장
        analysis = {
            "ticker": ticker,
            "name": etf_info['name'],
            "question": question,
            "answer": result['answer'],
            "sources": result['sources'],
            "created_at": datetime.now().isoformat(),
            "cached": False,
            "token_count": result['usage'].get('total_tokens', 0)
        }
        
        self._save_to_cache(ticker, analysis)
        
        return analysis
    
    def _get_from_cache(self, ticker: str) -> Optional[Dict]:
        """캐시에서 조회"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ticker, question, answer, created_at, token_count
                FROM ai_insights
                WHERE ticker = ?
                  AND expires_at > ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (ticker, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                return {
                    "ticker": row[0],
                    "question": row[1],
                    "answer": row[2],
                    "created_at": row[3],
                    "token_count": row[4],
                    "sources": []  # 소스는 캐시하지 않음
                }
        return None
    
    def _save_to_cache(self, ticker: str, analysis: Dict):
        """캐시에 저장"""
        expires_at = (datetime.now() + timedelta(hours=self.cache_duration)).isoformat()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_insights (
                    ticker, question, answer, created_at, expires_at, token_count
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                analysis['question'],
                analysis['answer'],
                analysis['created_at'],
                expires_at,
                analysis.get('token_count', 0)
            ))
            conn.commit()
    
    def _get_etf_info(self, ticker: str) -> Optional[Dict]:
        """ETF 정보 조회"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ticker, name, type, theme
                FROM etfs
                WHERE ticker = ?
            """, (ticker,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "ticker": row[0],
                    "name": row[1],
                    "type": row[2],
                    "theme": row[3]
                }
        return None
```

#### 1.3 API 라우터 추가
**파일**: `backend/app/routers/etfs.py` (기존 파일에 추가)

```python
from app.services.ai_analysis_service import AIAnalysisService

# 라우터에 추가
@router.get("/{ticker}/ai-analysis")
@limiter.limit(RateLimitConfig.ANALYSIS)  # 예: "10/hour"
async def get_ai_analysis(
    request: Request,
    etf: ETF = Depends(get_etf_or_404),
    api_key: str = Depends(verify_api_key_dependency)
) -> Dict:
    """
    ETF AI 분석 조회
    
    - Perplexity AI를 활용한 종목 심층 분석
    - 24시간 캐싱으로 비용 절감
    - Rate limiting: 시간당 10회
    """
    try:
        service = AIAnalysisService()
        analysis = await service.get_analysis(etf.ticker)
        
        return analysis
        
    except ValueError as e:
        logger.error(f"ETF not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"AI analysis error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="AI 분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )
```

#### 1.4 환경 변수 설정
**파일**: `backend/.env` (예시)

```bash
# Perplexity AI API
PERPLEXITY_API_KEY=pplx-your-api-key-here
```

#### 1.5 데이터베이스 마이그레이션
**파일**: `backend/app/database.py` (테이블 추가)

```python
# init_db() 함수에 추가
cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        source TEXT DEFAULT 'perplexity',
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        token_count INTEGER DEFAULT 0,
        FOREIGN KEY (ticker) REFERENCES etfs(ticker) ON DELETE CASCADE
    )
""")

cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_ticker ON ai_insights(ticker)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_expires ON ai_insights(expires_at)")
```

---

### Phase 2: 프론트엔드 구현 (우선순위: 높음)

#### 2.1 API 클라이언트 추가
**파일**: `frontend/src/services/api.js` (기존 파일에 추가)

```javascript
// ETF API에 추가
export const etfApi = {
  // ... 기존 함수들 ...
  
  /**
   * ETF AI 분석 조회
   */
  getAIAnalysis: async (ticker) => {
    return api.get(`/etfs/${ticker}/ai-analysis`)
  },
}
```

#### 2.2 AI 분석 컴포넌트 작성
**파일**: `frontend/src/components/etf/AIAnalysisPanel.jsx` (신규)

```javascript
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import { etfApi } from '../../services/api'

export default function AIAnalysisPanel({ ticker, etfName }) {
  const [expanded, setExpanded] = useState(false)
  
  // AI 분석 조회 (확장될 때만 로딩)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['ai-analysis', ticker],
    queryFn: async () => {
      const response = await etfApi.getAIAnalysis(ticker)
      return response.data
    },
    enabled: expanded, // 확장될 때만 실행
    staleTime: 24 * 60 * 60 * 1000, // 24시간
    cacheTime: 24 * 60 * 60 * 1000,
  })
  
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
  
  return (
    <section className="bg-white dark:bg-gray-800 rounded-lg shadow">
      {/* 헤더 */}
      <div
        className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                AI 심층 분석
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Perplexity AI 기반 종목 분석
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {data?.cached && (
              <span className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded">
                캐시됨
              </span>
            )}
            <svg
              className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>
      
      {/* 내용 */}
      {expanded && (
        <div className="px-6 py-6">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <svg className="animate-spin h-12 w-12 text-purple-500 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                AI가 분석 중입니다... (약 10초 소요)
              </p>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <svg className="w-12 h-12 text-red-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-red-600 dark:text-red-400 mb-4">
                AI 분석을 불러오는데 실패했습니다.
              </p>
              <button
                onClick={() => refetch()}
                className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors text-sm"
              >
                다시 시도
              </button>
            </div>
          ) : data ? (
            <>
              {/* 메타 정보 */}
              <div className="mb-6 pb-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>
                    마지막 업데이트: {formatDate(data.created_at)}
                  </span>
                  {data.token_count > 0 && (
                    <span>
                      토큰: {data.token_count.toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
              
              {/* AI 응답 */}
              <div className="prose dark:prose-invert max-w-none">
                <ReactMarkdown
                  components={{
                    h3: ({node, ...props}) => <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mt-6 mb-3" {...props} />,
                    h4: ({node, ...props}) => <h4 className="text-base font-semibold text-gray-800 dark:text-gray-200 mt-4 mb-2" {...props} />,
                    p: ({node, ...props}) => <p className="text-sm text-gray-700 dark:text-gray-300 mb-3 leading-relaxed" {...props} />,
                    ul: ({node, ...props}) => <ul className="text-sm text-gray-700 dark:text-gray-300 mb-3 space-y-1" {...props} />,
                    ol: ({node, ...props}) => <ol className="text-sm text-gray-700 dark:text-gray-300 mb-3 space-y-1" {...props} />,
                    li: ({node, ...props}) => <li className="ml-4" {...props} />,
                    strong: ({node, ...props}) => <strong className="font-semibold text-gray-900 dark:text-gray-100" {...props} />,
                    code: ({node, ...props}) => <code className="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs" {...props} />,
                  }}
                >
                  {data.answer}
                </ReactMarkdown>
              </div>
              
              {/* 소스 */}
              {data.sources && data.sources.length > 0 && (
                <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                    참고 자료
                  </h4>
                  <div className="space-y-2">
                    {data.sources.map((source, index) => (
                      <a
                        key={index}
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-xs text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        [{index + 1}] {source.title || source.url}
                      </a>
                    ))}
                  </div>
                </div>
              )}
              
              {/* 면책 조항 */}
              <div className="mt-6 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <p className="text-xs text-yellow-800 dark:text-yellow-300">
                  ⚠️ 이 분석은 AI가 생성한 정보로, 투자 권유가 아닙니다. 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.
                </p>
              </div>
            </>
          ) : null}
        </div>
      )}
    </section>
  )
}
```

#### 2.3 ETFDetail 페이지에 통합
**파일**: `frontend/src/pages/ETFDetail.jsx` (기존 파일 수정)

```javascript
// import 추가
import AIAnalysisPanel from '../components/etf/AIAnalysisPanel'

// 페이지 렌더링 부분에 추가 (뉴스 섹션 위 또는 아래)
<AIAnalysisPanel ticker={ticker} etfName={etfData.name} />
```

#### 2.4 React Markdown 라이브러리 설치
```bash
cd frontend
npm install react-markdown
```

---

### Phase 3: 테스트 및 최적화 (우선순위: 중간)

#### 3.1 백엔드 테스트
**파일**: `backend/tests/test_ai_analysis.py` (신규)

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.services.ai_analysis_service import AIAnalysisService

@pytest.mark.asyncio
async def test_get_analysis_from_cache():
    """캐시된 분석 조회 테스트"""
    service = AIAnalysisService()
    # 구현...

@pytest.mark.asyncio
async def test_get_analysis_new_request():
    """새 분석 요청 테스트"""
    service = AIAnalysisService()
    # 구현...

@pytest.mark.asyncio
async def test_perplexity_api_error():
    """API 에러 처리 테스트"""
    # 구현...
```

#### 3.2 프론트엔드 테스트
**파일**: `frontend/src/components/etf/AIAnalysisPanel.test.jsx` (신규)

```javascript
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AIAnalysisPanel from './AIAnalysisPanel'

test('확장 시 AI 분석 로딩', async () => {
  // 구현...
})

test('캐시된 분석 표시', async () => {
  // 구현...
})

test('에러 처리', async () => {
  // 구현...
})
```

#### 3.3 성능 최적화
- Rate limiting 세부 조정
- 캐시 만료 정책 검토
- 응답 시간 모니터링

---

## 📅 일정 계획

| 단계 | 작업 | 예상 시간 | 담당 |
|------|------|-----------|------|
| **Phase 1** | 백엔드 API 구현 | 2-3일 | Backend Dev |
| 1.1 | Perplexity 클라이언트 | 4시간 | |
| 1.2 | AI 분석 서비스 | 6시간 | |
| 1.3 | API 라우터 | 2시간 | |
| 1.4 | 환경 설정 | 1시간 | |
| 1.5 | DB 마이그레이션 | 2시간 | |
| **Phase 2** | 프론트엔드 구현 | 2-3일 | Frontend Dev |
| 2.1 | API 클라이언트 | 1시간 | |
| 2.2 | AI 분석 컴포넌트 | 8시간 | |
| 2.3 | ETFDetail 통합 | 2시간 | |
| 2.4 | 라이브러리 설치 | 0.5시간 | |
| **Phase 3** | 테스트 및 최적화 | 1-2일 | QA Team |
| 3.1 | 백엔드 테스트 | 4시간 | |
| 3.2 | 프론트엔드 테스트 | 4시간 | |
| 3.3 | 성능 최적화 | 4시간 | |
| **총계** | | **5-8일** | |

---

## 💰 비용 예측

### Perplexity API 가격 (2026년 1월 기준)

| 모델 | 가격 | 설명 |
|------|------|------|
| sonar-small | $0.20 / 1M tokens | 빠른 응답, 기본 분석 |
| sonar-medium | $0.60 / 1M tokens | 균형잡힌 성능 |
| **sonar-large** (권장) | **$1.00 / 1M tokens** | 고품질 분석 |

### 예상 사용량

**가정**:
- 등록 종목: 9개
- 평균 응답: **8,000 tokens/요청** (상세 보고서)
- 프롬프트: ~2,000 tokens (Perplexity_prompt.md)
- 캐시 적중률: 80% (24시간 캐싱)
- 일일 신규 요청: 5회

**월간 비용**:
```
5 요청/일 × 30일 × (2,000 입력 + 8,000 출력) = 1,500,000 tokens/월
1,500,000 / 1,000,000 × $1.00 = $1.50/월
```

**연간 비용**: 약 **$18/년**

**참고**:
- 캐시 적중률이 높을수록 비용 감소
- 실제 사용량은 사용자 패턴에 따라 달라질 수 있음
- 상세한 보고서 생성으로 기존 예상 대비 5배 증가

---

## ⚠️ 리스크 및 대응 방안

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|-----------|
| **Perplexity API 장애** | 높음 | - 에러 처리 및 사용자 안내<br>- 캐시된 데이터 활용<br>- 타임아웃 설정 |
| **API 비용 초과** | 중간 | - Rate limiting 강화<br>- 캐싱 기간 연장<br>- 사용량 모니터링 |
| **부정확한 정보 제공** | 높음 | - 면책 조항 명시<br>- "AI 생성 정보" 명확히 표시<br>- 소스 링크 제공 |
| **응답 시간 지연** | 중간 | - 비동기 처리<br>- 로딩 상태 표시<br>- 타임아웃 처리 |
| **API Key 노출** | 높음 | - 환경 변수 사용<br>- 백엔드에서만 호출<br>- .env를 .gitignore에 추가 |

---

## 🔒 보안 고려사항

1. **API Key 관리**
   - 환경 변수로 저장 (`.env`)
   - Git 커밋 제외 (`.gitignore`)
   - 프로덕션 환경 별도 관리

2. **Rate Limiting**
   - IP 기반 제한: 시간당 10회
   - 사용자별 제한 (향후)
   - 캐시 적중률 모니터링

3. **입력 검증**
   - Ticker 형식 검증
   - SQL Injection 방지
   - XSS 방지 (마크다운 렌더링)

4. **에러 처리**
   - 민감한 정보 노출 방지
   - 사용자 친화적 에러 메시지
   - 로그 기록 (디버깅용)

---

## 📊 성공 지표 (KPI)

1. **기능적 지표**
   - 캐시 적중률: 80% 이상
   - 평균 응답 시간: 15-20초 이하 (상세 보고서)
   - API 성공률: 95% 이상
   - 응답 완성도: 보고서 12개 섹션 중 10개 이상 포함

2. **사용자 지표**
   - AI 분석 조회 수/일
   - 평균 체류 시간 증가 (분석 페이지)
   - 사용자 피드백 점수 (만족도)
   - 보고서 활용률 (확장 → 완독 비율)

3. **비용 지표**
   - 월간 API 비용: $2 이하 목표
   - 요청당 비용: $0.005 이하
   - 캐시 절감 효과: 최소 70%

---

## 🚀 향후 개선 방향

### Short-term (1-3개월)
- 사용자 맞춤형 질문 입력 기능
- 분석 히스토리 조회
- 다국어 지원 (영어)

### Mid-term (3-6개월)
- AI 분석 비교 기능 (종목 간)
- 실시간 뉴스 기반 업데이트 알림
- PDF/이미지 내보내기

### Long-term (6개월+)
- 자체 AI 모델 파인튜닝
- 포트폴리오 전체 분석
- 투자 전략 추천

---

## 📝 체크리스트

### 개발 시작 전
- [ ] Perplexity API Key 발급
- [ ] `.env` 파일 설정
- [ ] 요구사항 최종 확인
- [ ] 질의 템플릿 확정

### Phase 1 완료 조건
- [ ] Perplexity API 연동 성공
- [ ] 캐싱 동작 확인
- [ ] API 엔드포인트 테스트
- [ ] DB 테이블 생성 확인

### Phase 2 완료 조건
- [ ] AI 분석 패널 렌더링 확인
- [ ] 로딩/에러 상태 표시
- [ ] 마크다운 렌더링 정상 동작
- [ ] ETFDetail 페이지 통합

### Phase 3 완료 조건
- [ ] 모든 테스트 통과
- [ ] 성능 지표 달성
- [ ] 보안 검토 완료
- [ ] 사용자 매뉴얼 작성

### 배포 전
- [ ] 프로덕션 API Key 설정
- [ ] Rate limiting 설정 확인
- [ ] 모니터링 설정
- [ ] 롤백 계획 수립

---

## 📚 참고 자료

### Perplexity AI
- [API 문서](https://docs.perplexity.ai/)
- [가격 정책](https://www.perplexity.ai/pricing)
- [모델 비교](https://docs.perplexity.ai/docs/model-cards)

### 기술 스택
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [React Query 가이드](https://tanstack.com/query/latest)
- [React Markdown](https://github.com/remarkjs/react-markdown)

### 유사 사례
- Bloomberg Terminal AI 분석
- Yahoo Finance AI Insights
- Seeking Alpha AI Stock Analysis

---

## 📞 문의 및 지원

**프로젝트 관련 문의**
- 개발팀: dev@etfweeklyreport.com
- 기술 지원: support@etfweeklyreport.com

**문서 작성일**: 2026-01-10  
**문서 버전**: 1.0  
**최종 수정일**: 2026-01-10
