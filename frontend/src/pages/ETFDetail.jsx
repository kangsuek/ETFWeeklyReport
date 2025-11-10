import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { etfApi, newsApi } from '../services/api'
import PageHeader from '../components/common/PageHeader'
import Spinner from '../components/common/Spinner'
import PriceChart from '../components/charts/PriceChart'
import TradingFlowChart from '../components/charts/TradingFlowChart'
import DateRangeSelector from '../components/charts/DateRangeSelector'
import ChartSkeleton from '../components/charts/ChartSkeleton'
import { formatPrice, formatVolume, formatPercent, getPriceChangeColor } from '../utils/format'

/**
 * ErrorFallback 컴포넌트
 * 차트 에러 시 표시되는 폴백 UI
 */
const ErrorFallback = ({ error, onRetry }) => (
  <div className="flex flex-col items-center justify-center bg-red-50 rounded-lg p-8 min-h-[300px]">
    <p className="text-red-600 font-semibold mb-2">데이터를 불러오는데 실패했습니다</p>
    <p className="text-sm text-gray-600 mb-4">{error?.message || '알 수 없는 오류가 발생했습니다'}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
      >
        다시 시도
      </button>
    )}
  </div>
)

/**
 * NewsTimeline 컴포넌트
 * 종목 관련 뉴스를 타임라인 형태로 표시
 */
const NewsTimeline = ({ ticker }) => {
  const [limit, setLimit] = useState(10)

  const { data, isLoading, error } = useQuery({
    queryKey: ['news', ticker, limit],
    queryFn: async () => {
      const response = await newsApi.getByTicker(ticker, { days: 7, limit })
      return response.data
    },
    staleTime: 5 * 60 * 1000, // 5분
  })

  // 날짜별로 그룹핑 (hooks는 항상 먼저 호출되어야 함)
  const groupedNews = useMemo(() => {
    if (!data || data.length === 0) return {}

    const groups = {}
    data.forEach((news) => {
      // 날짜 유효성 검사 추가
      if (!news.published_at) return

      try {
        const date = new Date(news.published_at)
        // Invalid Date 체크
        if (isNaN(date.getTime())) return

        const dateKey = format(date, 'yyyy-MM-dd')
        if (!groups[dateKey]) {
          groups[dateKey] = []
        }
        groups[dateKey].push(news)
      } catch (error) {
        console.warn('Invalid date for news:', news.published_at, error)
      }
    })
    return groups
  }, [data])

  // 관련도 점수 색상 반환
  const getRelevanceColor = (score) => {
    if (score >= 0.8) return 'bg-green-500'
    if (score >= 0.5) return 'bg-yellow-500'
    return 'bg-gray-400'
  }

  const handleLoadMore = () => {
    setLimit((prev) => prev + 10)
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
            <div className="h-6 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>뉴스를 불러오는데 실패했습니다</p>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>최근 뉴스가 없습니다</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {Object.entries(groupedNews).map(([date, newsItems]) => (
        <div key={date}>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">
            {format(new Date(date), 'yyyy년 MM월 dd일')}
          </h4>
          <div className="space-y-3 ml-4 border-l-2 border-gray-200 pl-4">
            {newsItems.map((news) => (
              <div
                key={news.id}
                className="bg-white rounded-lg p-4 hover:shadow-md transition-shadow border border-gray-100"
              >
                <a
                  href={news.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-base font-medium text-gray-900 hover:text-blue-600 transition-colors"
                >
                  {news.title}
                </a>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                  <span>{news.source}</span>
                  <span>•</span>
                  <span>
                    {news.published_at ? (() => {
                      try {
                        const date = new Date(news.published_at)
                        return isNaN(date.getTime()) ? '-' : format(date, 'HH:mm')
                      } catch {
                        return '-'
                      }
                    })() : '-'}
                  </span>
                  {news.relevance_score && (
                    <>
                      <span>•</span>
                      <div className="flex items-center gap-1">
                        <span>관련도</span>
                        <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${getRelevanceColor(news.relevance_score)}`}
                            style={{ width: `${news.relevance_score * 100}%` }}
                          ></div>
                        </div>
                        <span>{(news.relevance_score * 100).toFixed(0)}%</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {data.length >= limit && (
        <div className="text-center pt-4">
          <button
            onClick={handleLoadMore}
            className="px-6 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
          >
            더 보기
          </button>
        </div>
      )}
    </div>
  )
}

/**
 * ETFDetail 페이지
 * ETF 상세 정보, 차트, 뉴스를 통합한 완전한 Detail 페이지
 */
export default function ETFDetail() {
  const { ticker } = useParams()
  const [dateRange, setDateRange] = useState({
    startDate: '',
    endDate: '',
    range: '7d'
  })

  // ETF 기본 정보 조회
  const { data: etf, isLoading: etfLoading, error: etfError } = useQuery({
    queryKey: ['etf', ticker],
    queryFn: async () => {
      const response = await etfApi.getDetail(ticker)
      return response.data
    },
  })

  // 가격 데이터 조회
  const {
    data: pricesData,
    isLoading: pricesLoading,
    error: pricesError,
    refetch: refetchPrices
  } = useQuery({
    queryKey: ['prices', ticker, dateRange.startDate, dateRange.endDate],
    queryFn: async () => {
      const response = await etfApi.getPrices(ticker, {
        startDate: dateRange.startDate,
        endDate: dateRange.endDate
      })
      return response.data
    },
    enabled: !!dateRange.startDate && !!dateRange.endDate,
    staleTime: 1 * 60 * 1000, // 1분
  })

  // 매매 동향 데이터 조회
  const {
    data: tradingFlowData,
    isLoading: tradingFlowLoading,
    error: tradingFlowError,
    refetch: refetchTradingFlow
  } = useQuery({
    queryKey: ['tradingFlow', ticker, dateRange.startDate, dateRange.endDate],
    queryFn: async () => {
      const response = await etfApi.getTradingFlow(ticker, {
        startDate: dateRange.startDate,
        endDate: dateRange.endDate
      })
      return response.data
    },
    enabled: !!dateRange.startDate && !!dateRange.endDate,
    staleTime: 1 * 60 * 1000, // 1분
  })

  // 날짜 범위 변경 핸들러
  const handleDateRangeChange = (newRange) => {
    setDateRange(newRange)
  }

  // 최근 가격 정보 계산
  const latestPrice = useMemo(() => {
    if (!pricesData || pricesData.length === 0) return null
    return pricesData[pricesData.length - 1]
  }, [pricesData])

  if (etfLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Spinner />
      </div>
    )
  }

  if (etfError) {
    return (
      <div className="animate-fadeIn">
        <PageHeader title="오류" subtitle="데이터를 불러올 수 없습니다" />
        <div className="card">
          <ErrorFallback error={etfError} />
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fadeIn">
      {/* Sticky 헤더 */}
      <div className="sticky top-0 z-50 mb-4">
        {/* 배경 레이어 (전체 너비) */}
        <div className="absolute inset-0 bg-white border-b border-gray-200 shadow-sm -mx-4 sm:-mx-6 lg:-mx-8"></div>
        {/* 내용 레이어 (카드와 동일한 패딩) */}
        <div className="relative py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">{etf?.name || 'ETF 상세'}</h1>
              <p className="text-gray-600">{`${etf?.ticker} · ${etf?.theme}`}</p>
            </div>
          </div>
        </div>
      </div>

      {/* 기본 정보 섹션 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        {/* 종목 정보 */}
        <div className="card lg:col-span-2">
          <h3 className="text-lg font-semibold mb-3">종목 정보</h3>
          <div className="grid grid-cols-3 gap-x-4 gap-y-2">
            <div>
              <span className="text-sm text-gray-500">티커</span>
              <p className="text-base font-semibold mt-0.5">{etf?.ticker}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500">타입</span>
              <p className="text-base font-semibold mt-0.5">
                <span className={`inline-block px-2 py-1 rounded text-xs ${
                  etf?.type === 'ETF' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
                }`}>
                  {etf?.type}
                </span>
              </p>
            </div>
            <div>
              <span className="text-sm text-gray-500">테마</span>
              <p className="text-base font-semibold mt-0.5 line-clamp-1">{etf?.theme}</p>
            </div>
            {etf?.expense_ratio && (
              <div>
                <span className="text-sm text-gray-500">운용보수</span>
                <p className="text-base font-semibold mt-0.5">{etf?.expense_ratio}%</p>
              </div>
            )}
            {etf?.launch_date && (
              <div>
                <span className="text-sm text-gray-500">상장일</span>
                <p className="text-base font-semibold mt-0.5">
                  {format(new Date(etf.launch_date), 'yyyy-MM-dd')}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* 최근 가격 정보 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-3">최근 가격 정보</h3>
          {latestPrice ? (
            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              <div>
                <span className="text-sm text-gray-500">종가</span>
                <p className="text-xl font-bold mt-0.5">{formatPrice(latestPrice.close_price)}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500">등락률</span>
                <p className={`text-xl font-bold mt-0.5 ${getPriceChangeColor(latestPrice.daily_change_pct)}`}>
                  {formatPercent(latestPrice.daily_change_pct)}
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-500">거래량</span>
                <p className="text-xl font-bold mt-0.5">{formatVolume(latestPrice.volume)}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500">일자</span>
                <p className="text-base font-semibold mt-0.5">
                  {format(new Date(latestPrice.date), 'yyyy-MM-dd')}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">가격 데이터가 없습니다</p>
          )}
        </div>
      </div>

      {/* 날짜 범위 선택기 */}
      <DateRangeSelector
        onDateRangeChange={handleDateRangeChange}
        defaultRange="7d"
      />

      {/* 차트 섹션 */}
      <div className="space-y-4 mb-4">
        {/* 가격 차트 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-3">가격 차트</h3>
          {pricesLoading ? (
            <ChartSkeleton height={400} />
          ) : pricesError ? (
            <ErrorFallback error={pricesError} onRetry={refetchPrices} />
          ) : (
            <PriceChart data={pricesData} ticker={ticker} height={400} />
          )}
        </div>

        {/* 매매 동향 차트 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-3">투자자별 매매 동향</h3>
          {tradingFlowLoading ? (
            <ChartSkeleton height={400} />
          ) : tradingFlowError ? (
            <ErrorFallback error={tradingFlowError} onRetry={refetchTradingFlow} />
          ) : (
            <TradingFlowChart data={tradingFlowData} ticker={ticker} height={400} />
          )}
        </div>
      </div>

      {/* 뉴스 타임라인 섹션 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-3">최근 뉴스</h3>
        <NewsTimeline ticker={ticker} />
      </div>
    </div>
  )
}
