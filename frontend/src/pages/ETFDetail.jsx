import { useState, useMemo, useRef, useCallback, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { etfApi, newsApi } from '../services/api'
import { useSettings } from '../contexts/SettingsContext'
import PageHeader from '../components/common/PageHeader'
import Spinner from '../components/common/Spinner'
import LoadingIndicator from '../components/common/LoadingIndicator'
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
  <div className="flex flex-col items-center justify-center bg-red-50 dark:bg-red-900/20 rounded-lg p-8 min-h-[300px] transition-colors">
    <p className="text-red-600 dark:text-red-400 font-semibold mb-2">데이터를 불러오는데 실패했습니다</p>
    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">{error?.message || '알 수 없는 오류가 발생했습니다'}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-red-600 dark:bg-red-700 text-white rounded-md hover:bg-red-700 dark:hover:bg-red-800 transition-colors"
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
      if (!news.date) return

      try {
        const date = new Date(news.date)
        // Invalid Date 체크
        if (isNaN(date.getTime())) return

        const dateKey = format(date, 'yyyy-MM-dd')
        if (!groups[dateKey]) {
          groups[dateKey] = []
        }
        groups[dateKey].push(news)
      } catch (error) {
        console.warn('Invalid date for news:', news.date, error)
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

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-2"></div>
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <p>뉴스를 불러오는데 실패했습니다</p>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <p>최근 뉴스가 없습니다</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {Object.entries(groupedNews).map(([date, newsItems]) => (
        <div key={date}>
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            {format(new Date(date), 'yyyy년 MM월 dd일')}
          </h4>
          <div className="space-y-3 ml-4 border-l-2 border-gray-200 dark:border-gray-700 pl-4">
            {newsItems.map((news, index) => (
              <div
                key={news.url || `${news.date}-${index}`}
                className="bg-white dark:bg-gray-800 rounded-lg p-4 hover:shadow-md transition-shadow border border-gray-100 dark:border-gray-700"
              >
                <a
                  href={news.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-base font-medium text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                >
                  {news.title}
                </a>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>{news.source}</span>
                  <span>•</span>
                  <span>
                    {news.date ? (() => {
                      try {
                        const date = new Date(news.date)
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
                        <div className="w-20 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
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
    </div>
  )
}

/**
 * 설정값의 날짜 범위 형식을 DateRangeSelector 형식으로 변환
 * '7D' -> '7d', '1M' -> '1m', '3M' -> '3m'
 */
function convertDateRangeFormat(settingRange) {
  const mapping = {
    '7D': '7d',
    '1M': '1m',
    '3M': '3m',
  }
  return mapping[settingRange] || '7d'
}

/**
 * ETFDetail 페이지
 * ETF 상세 정보, 차트, 뉴스를 통합한 완전한 Detail 페이지
 */
export default function ETFDetail() {
  const { ticker } = useParams()
  const { settings } = useSettings()
  
  // 설정에서 기본 날짜 범위 가져오기 (변환 필요: '7D' -> '7d')
  const defaultRangeFromSettings = useMemo(
    () => convertDateRangeFormat(settings.defaultDateRange),
    [settings.defaultDateRange]
  )

  // 사용자가 수동으로 날짜 범위를 변경했는지 추적
  const userModifiedRef = useRef(false)

  const [dateRange, setDateRange] = useState({
    startDate: '',
    endDate: '',
    range: defaultRangeFromSettings
  })

  // 설정 변경 시 날짜 범위 반영 (사용자가 수동으로 변경하지 않은 경우)
  useEffect(() => {
    const newRange = convertDateRangeFormat(settings.defaultDateRange)
    // 사용자가 수동으로 변경하지 않은 경우에만 설정값으로 업데이트
    if (!userModifiedRef.current && dateRange.range !== newRange) {
      setDateRange({
        startDate: '',
        endDate: '',
        range: newRange
      })
    }
  }, [settings.defaultDateRange])

  // 차트 스크롤 동기화를 위한 refs
  const priceChartScrollRef = useRef(null)
  const tradingFlowChartScrollRef = useRef(null)
  const isScrollingSyncRef = useRef(false) // 무한 루프 방지 플래그

  // ETF 기본 정보 조회
  const { data: etf, isLoading: etfLoading, error: etfError } = useQuery({
    queryKey: ['etf', ticker],
    queryFn: async () => {
      const response = await etfApi.getDetail(ticker)
      return response.data
    },
  })

  // 가격 데이터 조회 (자동 수집 지원)
  const {
    data: pricesData,
    isLoading: pricesLoading,
    isFetching: pricesFetching,
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
    staleTime: 0, // 항상 최신 데이터 확인 (자동 수집을 위해)
    cacheTime: 5 * 60 * 1000, // 5분 캐시
    retry: 1, // 실패 시 1회 재시도
    retryDelay: 1000, // 1초 후 재시도
  })

  // 매매 동향 데이터 조회 (자동 수집 지원)
  const {
    data: tradingFlowData,
    isLoading: tradingFlowLoading,
    isFetching: tradingFlowFetching,
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
    staleTime: 0, // 항상 최신 데이터 확인 (자동 수집을 위해)
    cacheTime: 5 * 60 * 1000, // 5분 캐시
    retry: 1, // 실패 시 1회 재시도
    retryDelay: 1000, // 1초 후 재시도
  })

  // 날짜 범위 변경 핸들러
  const handleDateRangeChange = (newRange) => {
    // 사용자가 수동으로 변경했음을 표시
    userModifiedRef.current = true
    setDateRange(newRange)
  }

  // 가격 차트 스크롤 핸들러 (투자자별 매매 동향 차트와 동기화)
  const handlePriceChartScroll = useCallback(() => {
    if (isScrollingSyncRef.current) return
    if (!priceChartScrollRef.current || !tradingFlowChartScrollRef.current) return

    isScrollingSyncRef.current = true
    tradingFlowChartScrollRef.current.scrollLeft = priceChartScrollRef.current.scrollLeft

    // 다음 프레임에서 플래그 해제
    requestAnimationFrame(() => {
      isScrollingSyncRef.current = false
    })
  }, [])

  // 투자자별 매매 동향 차트 스크롤 핸들러 (가격 차트와 동기화)
  const handleTradingFlowChartScroll = useCallback(() => {
    if (isScrollingSyncRef.current) return
    if (!priceChartScrollRef.current || !tradingFlowChartScrollRef.current) return

    isScrollingSyncRef.current = true
    priceChartScrollRef.current.scrollLeft = tradingFlowChartScrollRef.current.scrollLeft

    // 다음 프레임에서 플래그 해제
    requestAnimationFrame(() => {
      isScrollingSyncRef.current = false
    })
  }, [])

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
        <div className="absolute inset-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm -mx-4 sm:-mx-6 lg:-mx-8 transition-colors"></div>
        {/* 내용 레이어 (카드와 동일한 패딩) */}
        <div className="relative py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">{etf?.name || 'ETF 상세'}</h1>
              <p className="text-gray-600 dark:text-gray-400">{`${etf?.ticker} · ${etf?.theme}`}</p>
            </div>
          </div>
        </div>
      </div>

      {/* 기본 정보 섹션 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        {/* 종목 정보 */}
        <div className="card lg:col-span-2">
          <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">종목 정보</h3>
          <div className="grid grid-cols-3 gap-x-4 gap-y-2">
            <div>
              <span className="text-sm text-gray-500 dark:text-gray-400">티커</span>
              <p className="text-base font-semibold mt-0.5 text-gray-900 dark:text-gray-100">{etf?.ticker}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500 dark:text-gray-400">타입</span>
              <p className="text-base font-semibold mt-0.5">
                <span className={`inline-block px-2 py-1 rounded text-xs ${
                  etf?.type === 'ETF' 
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300' 
                    : 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                }`}>
                  {etf?.type}
                </span>
              </p>
            </div>
            <div>
              <span className="text-sm text-gray-500 dark:text-gray-400">테마</span>
              <p className="text-base font-semibold mt-0.5 line-clamp-1 text-gray-900 dark:text-gray-100">{etf?.theme}</p>
            </div>
            {etf?.expense_ratio && (
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">운용보수</span>
                <p className="text-base font-semibold mt-0.5 text-gray-900 dark:text-gray-100">{etf?.expense_ratio}%</p>
              </div>
            )}
            {etf?.launch_date && (
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">상장일</span>
                <p className="text-base font-semibold mt-0.5 text-gray-900 dark:text-gray-100">
                  {format(new Date(etf.launch_date), 'yyyy-MM-dd')}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* 최근 가격 정보 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">최근 가격 정보</h3>
          {latestPrice ? (
            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">종가</span>
                <p className="text-xl font-bold mt-0.5 text-gray-900 dark:text-gray-100">{formatPrice(latestPrice.close_price)}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">등락률</span>
                <p className={`text-xl font-bold mt-0.5 ${getPriceChangeColor(latestPrice.daily_change_pct)}`}>
                  {formatPercent(latestPrice.daily_change_pct)}
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">거래량</span>
                <p className="text-xl font-bold mt-0.5 text-gray-900 dark:text-gray-100">{formatVolume(latestPrice.volume)}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">일자</span>
                <p className="text-base font-semibold mt-0.5 text-gray-900 dark:text-gray-100">
                  {format(new Date(latestPrice.date), 'yyyy-MM-dd')}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 dark:text-gray-400">가격 데이터가 없습니다</p>
          )}
        </div>
      </div>

      {/* 날짜 범위 선택기 */}
      <DateRangeSelector
        key={`${defaultRangeFromSettings}-${settings.defaultDateRange}`}
        onDateRangeChange={handleDateRangeChange}
        defaultRange={defaultRangeFromSettings}
      />

      {/* 차트 섹션 */}
      <div className="space-y-4 mb-4">
        {/* 가격 차트 (거래량 포함) */}
        {settings.display.showVolume && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 transition-all duration-300 ease-in-out hover:shadow-xl relative">
            <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">가격 차트</h3>
            {pricesLoading || pricesFetching ? (
              <LoadingIndicator
                isLoading={true}
                message="가격 데이터를 불러오는 중..."
                subMessage={pricesFetching && !pricesLoading ? "데이터를 수집하고 있습니다. 최대 30초가 소요될 수 있습니다." : ""}
              />
            ) : pricesError ? (
              <ErrorFallback error={pricesError} onRetry={refetchPrices} />
            ) : (
              <PriceChart
                data={pricesData}
                ticker={ticker}
                dateRange={dateRange.range}
                scrollRef={priceChartScrollRef}
                onScroll={handlePriceChartScroll}
              />
            )}
          </div>
        )}

        {/* 매매 동향 차트 */}
        {settings.display.showTradingFlow && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 transition-all duration-300 ease-in-out hover:shadow-xl relative">
            <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-gray-100">투자자별 매매 동향</h3>
            {tradingFlowLoading || tradingFlowFetching ? (
              <LoadingIndicator
                isLoading={true}
                message="매매 동향 데이터를 불러오는 중..."
                subMessage={tradingFlowFetching && !tradingFlowLoading ? "데이터를 수집하고 있습니다. 최대 30초가 소요될 수 있습니다." : ""}
              />
            ) : tradingFlowError ? (
              <ErrorFallback error={tradingFlowError} onRetry={refetchTradingFlow} />
            ) : (
              <TradingFlowChart
                data={tradingFlowData}
                ticker={ticker}
                dateRange={dateRange.range}
                scrollRef={tradingFlowChartScrollRef}
                onScroll={handleTradingFlowChartScroll}
              />
            )}
          </div>
        )}
      </div>

      {/* 뉴스 타임라인 섹션 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-3">최근 뉴스</h3>
        <NewsTimeline ticker={ticker} />
      </div>
    </div>
  )
}
