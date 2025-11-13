#!/bin/bash

# ETF Weekly Report Web Application - Project Structure Setup Script
# This script creates the complete project directory structure and initial files

set -e  # Exit on error

echo "🚀 ETF 주간 리포트 웹 애플리케이션 구조 생성 중..."

# 현재 디렉토리가 프로젝트 루트인지 확인
if [ ! -f "CLAUDE.md" ]; then
    echo "❌ 오류: 프로젝트 루트 디렉토리에서 이 스크립트를 실행해주세요"
    exit 1
fi

echo "✅ 프로젝트 루트 확인 완료"
echo "📁 디렉토리 구조 확인 중..."

# Backend directories (이미 존재하는지 확인)
if [ ! -d "backend" ]; then
    echo "📁 백엔드 디렉토리 생성 중..."
    mkdir -p backend/app/{routers,services,models}
    mkdir -p backend/tests
    mkdir -p backend/data
else
    echo "✅ backend/ 디렉토리 존재 확인"
fi

# Frontend directories (이미 존재하는지 확인)
if [ ! -d "frontend" ]; then
    echo "📁 프론트엔드 디렉토리 생성 중..."
    mkdir -p frontend/src/{pages,components/{common,charts,etf,layout},hooks,utils,styles,services}
    mkdir -p frontend/public
else
    echo "✅ frontend/ 디렉토리 존재 확인"
fi

echo "📝 백엔드 파일 확인/생성 중..."

# Backend: main.py (파일이 없는 경우만 생성)
if [ ! -f "backend/app/main.py" ]; then
cat > backend/app/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import etfs, reports, news
from app.database import init_db
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ETF Weekly Report API",
    description="API for Korean ETF analysis and reporting",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")

# Include routers
app.include_router(etfs.router, prefix="/api/etfs", tags=["ETFs"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(news.router, prefix="/api/news", tags=["News"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "ETF Report API is running"}

@app.get("/")
async def root():
    return {
        "message": "ETF Weekly Report API",
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF
else
    echo "  ✅ backend/app/main.py 존재"
fi

# Backend: database.py (파일이 없는 경우만 생성)
if [ ! -f "backend/app/database.py" ]; then
cat > backend/app/database.py << 'EOF'
import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "etf_data.db"

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with schema"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS etfs (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            theme TEXT,
            launch_date DATE,
            expense_ratio REAL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            close_price REAL,
            volume INTEGER,
            daily_change_pct REAL,
            FOREIGN KEY (ticker) REFERENCES etfs(ticker),
            UNIQUE(ticker, date)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trading_flow (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            individual_net INTEGER,
            institutional_net INTEGER,
            foreign_net INTEGER,
            FOREIGN KEY (ticker) REFERENCES etfs(ticker),
            UNIQUE(ticker, date)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            title TEXT,
            url TEXT,
            source TEXT,
            relevance_score REAL,
            FOREIGN KEY (ticker) REFERENCES etfs(ticker)
        )
    """)
    
    # Insert initial ETF data
    etfs_data = [
        ("480450", "KODEX AI전력핵심설비", "AI/전력", "2024-03-15", 0.0045),
        ("456600", "SOL 조선TOP3플러스", "조선", "2023-08-10", 0.0050),
        ("497450", "KOACT 글로벌양자컴퓨팅액티브", "양자컴퓨팅", "2024-05-20", 0.0070),
        ("481330", "KBSTAR 글로벌원자력 iSelect", "원자력", "2024-01-25", 0.0055)
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO etfs (ticker, name, theme, launch_date, expense_ratio)
        VALUES (?, ?, ?, ?, ?)
    """, etfs_data)
    
    conn.commit()
    conn.close()
    
    logger.info("Database initialized successfully")

if __name__ == "__main__":
    init_db()
EOF
else
    echo "  ✅ backend/app/database.py 존재"
fi

# Backend: config.py (파일이 없는 경우만 생성)
if [ ! -f "backend/app/config.py" ]; then
cat > backend/app/config.py << 'EOF'
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Database
    database_url: str = "sqlite:///./data/etf_data.db"
    
    # Data Collection
    cache_ttl_minutes: int = 10
    news_max_results: int = 5
    
    class Config:
        env_file = ".env"

settings = Settings()
EOF
else
    echo "  ✅ backend/app/config.py 존재"
fi

# Backend: models.py (파일이 없는 경우만 생성)
if [ ! -f "backend/app/models.py" ]; then
cat > backend/app/models.py << 'EOF'
from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class ETF(BaseModel):
    ticker: str
    name: str
    theme: Optional[str] = None
    launch_date: Optional[date] = None
    expense_ratio: Optional[float] = None

class PriceData(BaseModel):
    date: date
    close_price: float
    volume: int
    daily_change_pct: float

class TradingFlow(BaseModel):
    date: date
    individual_net: int
    institutional_net: int
    foreign_net: int

class News(BaseModel):
    date: date
    title: str
    url: str
    source: str
    relevance_score: Optional[float] = None

class ETFMetrics(BaseModel):
    ticker: str
    aum: Optional[float] = None  # in billions KRW
    returns: dict  # {"1w": 0.023, "1m": 0.085, "ytd": 0.153}
    volatility: Optional[float] = None

class ETFDetailResponse(BaseModel):
    etf: ETF
    prices: List[PriceData]
    trading_flow: List[TradingFlow]
    news: List[News]
    metrics: ETFMetrics
EOF
else
    echo "  ✅ backend/app/models.py 존재"
fi

# Backend routers
if [ ! -f "backend/app/routers/etfs.py" ]; then
cat > backend/app/routers/etfs.py << 'EOF'
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date, timedelta
from app.models import ETF, PriceData, TradingFlow, ETFDetailResponse, ETFMetrics
from app.services.data_collector import ETFDataCollector
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
collector = ETFDataCollector()

@router.get("/", response_model=List[ETF])
async def get_etfs():
    """Get list of all ETFs"""
    try:
        return collector.get_all_etfs()
    except Exception as e:
        logger.error(f"Error fetching ETFs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}", response_model=ETF)
async def get_etf(ticker: str):
    """Get basic info for specific ETF"""
    try:
        etf = collector.get_etf_info(ticker)
        if not etf:
            raise HTTPException(status_code=404, detail="ETF not found")
        return etf
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ETF {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/prices", response_model=List[PriceData])
async def get_prices(
    ticker: str,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None)
):
    """Get price data for ETF within date range"""
    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()
    
    try:
        return collector.get_price_data(ticker, start_date, end_date)
    except Exception as e:
        logger.error(f"Error fetching prices for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/trading-flow", response_model=List[TradingFlow])
async def get_trading_flow(
    ticker: str,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None)
):
    """Get investor trading flow data"""
    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()
    
    try:
        return collector.get_trading_flow(ticker, start_date, end_date)
    except Exception as e:
        logger.error(f"Error fetching trading flow for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/metrics", response_model=ETFMetrics)
async def get_metrics(ticker: str):
    """Get key metrics for ETF"""
    try:
        return collector.get_etf_metrics(ticker)
    except Exception as e:
        logger.error(f"Error fetching metrics for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
EOF
else
    echo "  ✅ backend/app/routers/etfs.py 존재"
fi

if [ ! -f "backend/app/routers/reports.py" ]; then
cat > backend/app/routers/reports.py << 'EOF'
from fastapi import APIRouter, HTTPException
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/generate")
async def generate_report(tickers: List[str], format: str = "markdown"):
    """Generate report for selected ETFs"""
    # TODO: Implement report generation
    return {
        "message": "Report generation not yet implemented",
        "tickers": tickers,
        "format": format
    }
EOF
else
    echo "  ✅ backend/app/routers/reports.py 존재"
fi

if [ ! -f "backend/app/routers/news.py" ]; then
cat > backend/app/routers/news.py << 'EOF'
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date, timedelta
from app.models import News
from app.services.news_scraper import NewsScraper
import logging

router = APIRouter()
logger = logging.getLogger(__name__)
scraper = NewsScraper()

@router.get("/{ticker}", response_model=List[News])
async def get_news(
    ticker: str,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None)
):
    """Get news related to ETF theme"""
    if not start_date:
        start_date = date.today() - timedelta(days=7)
    if not end_date:
        end_date = date.today()
    
    try:
        return scraper.get_news_for_ticker(ticker, start_date, end_date)
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
EOF
else
    echo "  ✅ backend/app/routers/news.py 존재"
fi

# Backend services
if [ ! -f "backend/app/services/data_collector.py" ]; then
cat > backend/app/services/data_collector.py << 'EOF'
from typing import List, Optional
from datetime import date
from app.models import ETF, PriceData, TradingFlow, ETFMetrics
from app.database import get_db_connection
import logging

logger = logging.getLogger(__name__)

class ETFDataCollector:
    """Service for collecting ETF data from various sources"""
    
    def get_all_etfs(self) -> List[ETF]:
        """Get list of all ETFs from database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM etfs")
        rows = cursor.fetchall()
        conn.close()
        
        return [ETF(**dict(row)) for row in rows]
    
    def get_etf_info(self, ticker: str) -> Optional[ETF]:
        """Get basic info for specific ETF"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM etfs WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ETF(**dict(row))
        return None
    
    def get_price_data(self, ticker: str, start_date: date, end_date: date) -> List[PriceData]:
        """Get price data for date range"""
        # TODO: Implement actual data collection from Naver Finance or other sources
        # For now, return empty list
        logger.info(f"Fetching prices for {ticker} from {start_date} to {end_date}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, close_price, volume, daily_change_pct
            FROM prices
            WHERE ticker = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (ticker, start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        
        return [PriceData(**dict(row)) for row in rows]
    
    def get_trading_flow(self, ticker: str, start_date: date, end_date: date) -> List[TradingFlow]:
        """Get trading flow data"""
        logger.info(f"Fetching trading flow for {ticker} from {start_date} to {end_date}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, individual_net, institutional_net, foreign_net
            FROM trading_flow
            WHERE ticker = ? AND date BETWEEN ? AND ?
            ORDER BY date DESC
        """, (ticker, start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        
        return [TradingFlow(**dict(row)) for row in rows]
    
    def get_etf_metrics(self, ticker: str) -> ETFMetrics:
        """Calculate key metrics for ETF"""
        # TODO: Implement metrics calculation
        logger.info(f"Calculating metrics for {ticker}")
        
        return ETFMetrics(
            ticker=ticker,
            aum=None,
            returns={"1w": 0.0, "1m": 0.0, "ytd": 0.0},
            volatility=None
        )
EOF
else
    echo "  ✅ backend/app/services/data_collector.py 존재"
fi

if [ ! -f "backend/app/services/news_scraper.py" ]; then
cat > backend/app/services/news_scraper.py << 'EOF'
from typing import List
from datetime import date
from app.models import News
import logging

logger = logging.getLogger(__name__)

class NewsScraper:
    """Service for scraping news from various sources"""
    
    THEME_KEYWORDS = {
        "480450": ["AI", "전력", "인공지능", "데이터센터"],
        "456600": ["조선", "선박", "해운", "HD현대", "한화오션", "삼성중공업"],
        "497450": ["양자컴퓨팅", "양자", "퀀텀", "quantum"],
        "481330": ["원자력", "원전", "핵발전", "SMR"]
    }
    
    def get_news_for_ticker(self, ticker: str, start_date: date, end_date: date) -> List[News]:
        """Get news related to ETF theme"""
        # TODO: Implement actual news scraping
        logger.info(f"Fetching news for {ticker} from {start_date} to {end_date}")
        
        keywords = self.THEME_KEYWORDS.get(ticker, [])
        logger.info(f"Using keywords: {keywords}")
        
        # Return empty list for now
        return []
EOF
else
    echo "  ✅ backend/app/services/news_scraper.py 존재"
fi

# Backend: requirements.txt (파일이 없는 경우만 생성)
if [ ! -f "backend/requirements.txt" ]; then
cat > backend/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
pandas==2.1.3
numpy==1.26.2
requests==2.31.0
beautifulsoup4==4.12.2
python-multipart==0.0.6
python-dateutil==2.8.2
FinanceDataReader==0.9.50
lxml==4.9.3
aiofiles==23.2.1
EOF
else
    echo "  ✅ backend/requirements.txt 존재"
fi

# Backend: .env.example (파일이 없는 경우만 생성)
if [ ! -f "backend/.env.example" ]; then
cat > backend/.env.example << 'EOF'
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Database
DATABASE_URL=sqlite:///./data/etf_data.db

# Data Collection
CACHE_TTL_MINUTES=10
NEWS_MAX_RESULTS=5

# Optional: External APIs
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
EOF
else
    echo "  ✅ backend/.env.example 존재"
fi

echo "📝 프론트엔드 파일 확인/생성 중..."

# Frontend: package.json (파일이 없는 경우만 생성)
if [ ! -f "frontend/package.json" ]; then
cat > frontend/package.json << 'EOF'
{
  "name": "etf-report-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint . --ext js,jsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.8.4",
    "axios": "^1.6.2",
    "recharts": "^2.10.3",
    "date-fns": "^2.30.0",
    "clsx": "^2.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.53.0",
    "eslint-plugin-react": "^7.33.2",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.4",
    "postcss": "^8.4.31",
    "tailwindcss": "^3.3.5",
    "vite": "^5.0.0"
  }
}
EOF
else
    echo "  ✅ frontend/package.json 존재"
fi

# Frontend: vite.config.js (파일이 없는 경우만 생성)
if [ ! -f "frontend/vite.config.js" ]; then
cat > frontend/vite.config.js << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
EOF
else
    echo "  ✅ frontend/vite.config.js 존재"
fi

# Frontend: tailwind.config.js (파일이 없는 경우만 생성)
if [ ! -f "frontend/tailwind.config.js" ]; then
cat > frontend/tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#2563eb',
        success: '#10b981',
        danger: '#ef4444',
      },
    },
  },
  plugins: [],
}
EOF
else
    echo "  ✅ frontend/tailwind.config.js 존재"
fi

# Frontend: index.html (파일이 없는 경우만 생성)
if [ ! -f "frontend/index.html" ]; then
cat > frontend/index.html << 'EOF'
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>ETF Weekly Report</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
EOF
else
    echo "  ✅ frontend/index.html 존재"
fi

# Frontend: src/main.jsx (파일이 없는 경우만 생성)
if [ ! -f "frontend/src/main.jsx" ]; then
cat > frontend/src/main.jsx << 'EOF'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
EOF
else
    echo "  ✅ frontend/src/main.jsx 존재"
fi

# Frontend: src/App.jsx (파일이 없는 경우만 생성)
if [ ! -f "frontend/src/App.jsx" ]; then
cat > frontend/src/App.jsx << 'EOF'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Header from './components/layout/Header'
import Footer from './components/layout/Footer'
import Dashboard from './pages/Dashboard'
import ETFDetail from './pages/ETFDetail'
import Comparison from './pages/Comparison'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="flex flex-col min-h-screen bg-gray-50">
          <Header />
          <main className="flex-grow container mx-auto px-4 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/etf/:ticker" element={<ETFDetail />} />
              <Route path="/compare" element={<Comparison />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </Router>
    </QueryClientProvider>
  )
}

export default App
EOF
else
    echo "  ✅ frontend/src/App.jsx 존재"
fi

# Frontend: src/styles/index.css (파일이 없는 경우만 생성)
if [ ! -f "frontend/src/styles/index.css" ]; then
cat > frontend/src/styles/index.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply text-gray-900;
  }
}

@layer components {
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-colors;
  }
  
  .btn-primary {
    @apply bg-primary text-white hover:bg-blue-700;
  }
  
  .card {
    @apply bg-white rounded-lg shadow-md p-6;
  }
}
EOF
else
    echo "  ✅ frontend/src/styles/index.css 존재"
fi

# Frontend: src/services/api.js (파일이 없는 경우만 생성)
if [ ! -f "frontend/src/services/api.js" ]; then
cat > frontend/src/services/api.js << 'EOF'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const etfApi = {
  getAll: () => api.get('/etfs'),
  getDetail: (ticker) => api.get(`/etfs/${ticker}`),
  getPrices: (ticker, startDate, endDate) => 
    api.get(`/etfs/${ticker}/prices`, { params: { start_date: startDate, end_date: endDate } }),
  getTradingFlow: (ticker, startDate, endDate) => 
    api.get(`/etfs/${ticker}/trading-flow`, { params: { start_date: startDate, end_date: endDate } }),
  getMetrics: (ticker) => api.get(`/etfs/${ticker}/metrics`),
  getNews: (ticker, startDate, endDate) => 
    api.get(`/news/${ticker}`, { params: { start_date: startDate, end_date: endDate } }),
}

export default api
EOF
else
    echo "  ✅ frontend/src/services/api.js 존재"
fi

# Frontend: src/pages/Dashboard.jsx (파일이 없는 경우만 생성)
if [ ! -f "frontend/src/pages/Dashboard.jsx" ]; then
cat > frontend/src/pages/Dashboard.jsx << 'EOF'
import { useQuery } from '@tanstack/react-query'
import { etfApi } from '../services/api'
import ETFCard from '../components/etf/ETFCard'

export default function Dashboard() {
  const { data: etfs, isLoading, error } = useQuery({
    queryKey: ['etfs'],
    queryFn: async () => {
      const response = await etfApi.getAll()
      return response.data
    },
  })

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-red-600 text-center">
        Error loading ETFs: {error.message}
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">ETF Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {etfs?.map((etf) => (
          <ETFCard key={etf.ticker} etf={etf} />
        ))}
      </div>
    </div>
  )
}
EOF
else
    echo "  ✅ frontend/src/pages/Dashboard.jsx 존재"
fi

# Frontend: src/pages/ETFDetail.jsx (파일이 없는 경우만 생성)
if [ ! -f "frontend/src/pages/ETFDetail.jsx" ]; then
cat > frontend/src/pages/ETFDetail.jsx << 'EOF'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { etfApi } from '../services/api'

export default function ETFDetail() {
  const { ticker } = useParams()
  
  const { data: etf, isLoading } = useQuery({
    queryKey: ['etf', ticker],
    queryFn: async () => {
      const response = await etfApi.getDetail(ticker)
      return response.data
    },
  })

  if (isLoading) return <div>Loading...</div>

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">{etf?.name}</h1>
      <div className="card">
        <p>Ticker: {etf?.ticker}</p>
        <p>Theme: {etf?.theme}</p>
        <p>Expense Ratio: {etf?.expense_ratio}%</p>
      </div>
    </div>
  )
}
EOF
else
    echo "  ✅ frontend/src/pages/ETFDetail.jsx 존재"
fi

# Frontend: src/pages/Comparison.jsx (파일이 없는 경우만 생성)
if [ ! -f "frontend/src/pages/Comparison.jsx" ]; then
cat > frontend/src/pages/Comparison.jsx << 'EOF'
export default function Comparison() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">ETF Comparison</h1>
      <div className="card">
        <p>Comparison page coming soon...</p>
      </div>
    </div>
  )
}
EOF
else
    echo "  ✅ frontend/src/pages/Comparison.jsx 존재"
fi

# Frontend components
if [ ! -f "frontend/src/components/layout/Header.jsx" ]; then
cat > frontend/src/components/layout/Header.jsx << 'EOF'
import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="bg-white shadow-sm">
      <nav className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-2xl font-bold text-primary">
            ETF Weekly Report
          </Link>
          <div className="flex gap-6">
            <Link to="/" className="hover:text-primary">Dashboard</Link>
            <Link to="/compare" className="hover:text-primary">Compare</Link>
          </div>
        </div>
      </nav>
    </header>
  )
}
EOF
else
    echo "  ✅ frontend/src/components/layout/Header.jsx 존재"
fi

if [ ! -f "frontend/src/components/layout/Footer.jsx" ]; then
cat > frontend/src/components/layout/Footer.jsx << 'EOF'
export default function Footer() {
  return (
    <footer className="bg-gray-800 text-white py-6 mt-12">
      <div className="container mx-auto px-4 text-center">
        <p>&copy; 2025 ETF Weekly Report. For informational purposes only.</p>
      </div>
    </footer>
  )
}
EOF
else
    echo "  ✅ frontend/src/components/layout/Footer.jsx 존재"
fi

if [ ! -f "frontend/src/components/etf/ETFCard.jsx" ]; then
cat > frontend/src/components/etf/ETFCard.jsx << 'EOF'
import { Link } from 'react-router-dom'

export default function ETFCard({ etf }) {
  return (
    <Link to={`/etf/${etf.ticker}`}>
      <div className="card hover:shadow-lg transition-shadow cursor-pointer">
        <h3 className="text-lg font-bold mb-2">{etf.name}</h3>
        <p className="text-sm text-gray-600 mb-4">{etf.theme}</p>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-500">Ticker: {etf.ticker}</span>
          <span className="text-xs text-gray-500">Fee: {etf.expense_ratio}%</span>
        </div>
      </div>
    </Link>
  )
}
EOF
else
    echo "  ✅ frontend/src/components/etf/ETFCard.jsx 존재"
fi

if [ ! -f "frontend/src/components/common/Spinner.jsx" ]; then
cat > frontend/src/components/common/Spinner.jsx << 'EOF'
export default function Spinner() {
  return (
    <div className="flex justify-center items-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
    </div>
  )
}
EOF
else
    echo "  ✅ frontend/src/components/common/Spinner.jsx 존재"
fi

# Frontend: .env.example (파일이 없는 경우만 생성)
if [ ! -f "frontend/.env.example" ]; then
cat > frontend/.env.example << 'EOF'
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_TITLE=ETF Weekly Report
EOF
else
    echo "  ✅ frontend/.env.example 존재"
fi

# Docker 파일들 (파일이 없는 경우만 생성)
if [ ! -f "docker-compose.yml" ]; then
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./backend/data:/app/data
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_BASE_URL=http://localhost:8000/api
    command: npm run dev -- --host
    depends_on:
      - backend
EOF
else
    echo "  ✅ docker-compose.yml 존재"
fi

if [ ! -f "backend/Dockerfile" ]; then
cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
else
    echo "  ✅ backend/Dockerfile 존재"
fi

if [ ! -f "frontend/Dockerfile" ]; then
cat > frontend/Dockerfile << 'EOF'
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
EOF
else
    echo "  ✅ frontend/Dockerfile 존재"
fi

# 루트 README.md (파일이 없는 경우만 생성)
if [ ! -f "README.md" ]; then
cat > README.md << 'EOF'
# ETF Weekly Report Web Application

A comprehensive web application for analyzing and reporting on Korean ETF performance.

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.database  # Initialize database
uvicorn app.main:app --reload
```

Backend will be available at http://localhost:8000
API docs at http://localhost:8000/docs

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:5173

### Docker Setup (Alternative)
```bash
docker-compose up --build
```

## Project Structure
See CLAUDE.md for detailed documentation.

## Features
- Real-time ETF price tracking
- Investor flow analysis
- News aggregation
- Comparative analysis
- Report generation

## Tech Stack
- Backend: FastAPI, Python
- Frontend: React, TailwindCSS
- Database: SQLite/PostgreSQL
- Charts: Recharts

## License
MIT
EOF
else
    echo "  ✅ README.md 존재"
fi

# .gitignore (파일이 없는 경우만 생성)
if [ ! -f ".gitignore" ]; then
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
*.egg-info/
.pytest_cache/

# Node
node_modules/
dist/
build/
.DS_Store
*.log

# Environment
.env
.env.local

# Database
*.db
*.sqlite

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
EOF
else
    echo "  ✅ .gitignore 존재"
fi

echo ""
echo "✅ 프로젝트 구조 확인/생성이 성공적으로 완료되었습니다!"
echo ""
echo "📦 다음 단계:"
echo ""
echo "1. 백엔드 설정:"
echo "   cd backend"
echo "   python -m venv venv"
echo "   source venv/bin/activate  # Windows: venv\\Scripts\\activate"
echo "   pip install -r requirements.txt"
echo "   python -m app.database  # 데이터베이스 초기화"
echo "   uvicorn app.main:app --reload"
echo ""
echo "2. 프론트엔드 설정 (새 터미널에서):"
echo "   cd frontend"
echo "   npm install"
echo "   npm run dev"
echo ""
echo "3. 또는 Docker 사용:"
echo "   docker-compose up --build"
echo ""
echo "📖 주요 문서:"
echo "   - CLAUDE.md : 프로젝트 문서 인덱스"
echo "   - README.md : 프로젝트 개요"
echo "   - docs/DEFINITION_OF_DONE.md : 완료 기준 및 테스트 정책"
echo "   - project-management/TODO.md : 현재 작업 목록"
echo ""
echo "🧪 테스트 정책:"
echo "   ⚠️  모든 기능은 테스트 100% 완료 후 다음 단계로 진행"
echo "   → docs/DEFINITION_OF_DONE.md 참조"
echo ""
echo "🎉 즐거운 코딩 되세요!"
