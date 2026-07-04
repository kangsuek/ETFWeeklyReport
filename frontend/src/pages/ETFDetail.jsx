import { useState, useMemo, useRef, useCallback, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQueries, useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { etfApi, newsApi, alertApi } from '../services/api'
import { useSettings } from '../contexts/SettingsContext'
import PageHeader from '../components/common/PageHeader'
import Spinner from '../components/common/Spinner'
import ErrorFallback from '../components/common/ErrorFallback'
import DateRangeSelector from '../components/charts/DateRangeSelector'
import PriceTable from '../components/etf/PriceTable'
import NewsTimeline from '../components/news/NewsTimeline'
import ETFHeader from '../components/etf/ETFHeader'
import ETFCharts from '../components/etf/ETFCharts'
import InsightSummary from '../components/etf/InsightSummary'
import ETFBasicInfo from '../components/etf/ETFBasicInfo'
import ETFKeyMetrics from '../components/etf/ETFKeyMetrics'
import ETFFundamentalInfo from '../components/etf/ETFFundamentalInfo'
import StrategySummary from '../components/etf/StrategySummary'
import IntradayChart from '../components/charts/IntradayChart'
import PriceTargetPanel from '../components/etf/PriceTargetPanel'
import useAlertChecker from '../hooks/useAlertChecker'
import { CACHE_STALE_TIME_STATIC, CACHE_STALE_TIME_FAST, CACHE_STALE_TIME_SLOW } from '../constants'
import { calculateDateRange } from '../utils/dateRange'
import { calculateRSI, calculateMACD, calculateSupportResistance } from '../utils/technicalIndicators'

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

  // 초기 날짜 범위 즉시 계산 (API 호출 지연 방지)
  const initialDateRange = useMemo(
    () => calculateDateRange(defaultRangeFromSettings),
    [defaultRangeFromSettings]
  )

  const [dateRange, setDateRange] = useState(initialDateRange)

  // 가격 테이블 접힘 상태 (기본: 접힘)
  const [isTableExpanded, setIsTableExpanded] = useState(false)

  // 기술지표 토글 상태 (기본: 켜짐)
  const [showRSI, setShowRSI] = useState(true)
  const [showMACD, setShowMACD] = useState(true)

  // 설정 변경 시 날짜 범위 반영 (사용자가 수동으로 변경하지 않은 경우)
  useEffect(() => {
    const newRange = convertDateRangeFormat(settings.defaultDateRange)
    // 사용자가 수동으로 변경하지 않은 경우에만 설정값으로 업데이트
    if (!userModifiedRef.current && dateRange.range !== newRange) {
      const calculatedRange = calculateDateRange(newRange)
      setDateRange(calculatedRange)
    }
  }, [settings.defaultDateRange, dateRange.range])

  // 차트 스크롤 동기화를 위한 refs
  const priceChartScrollRef = useRef(null)
  const tradingFlowChartScrollRef = useRef(null)
  const isScrollingSyncRef = useRef(false) // 무한 루프 방지 플래그

  // 인사이트 period 계산
  const insightsPeriod = useMemo(() => {
    if (dateRange.range === '7d') return '1w'
    if (dateRange.range === '1m') return '1m'
    if (dateRange.range === '3m') return '3m'
    return '1m'
  }, [dateRange.range])

  // useQueries로 모든 API 병렬 호출 (성능 개선)
  const queries = useQueries({
    queries: [
      // 1순위: 기본 정보 (즉시 표시)
      {
        queryKey: ['etf', ticker],
        queryFn: async () => {
          const response = await etfApi.getDetail(ticker)
          return response.data
        },
        staleTime: CACHE_STALE_TIME_STATIC,
      },
      // 1순위: 가격 데이터 (차트 필수)
      {
        queryKey: ['prices', ticker, dateRange.startDate, dateRange.endDate],
        queryFn: async () => {
          const response = await etfApi.getPrices(ticker, {
            startDate: dateRange.startDate,
            endDate: dateRange.endDate
          })
          return response.data
        },
        staleTime: CACHE_STALE_TIME_FAST, // 30초
        refetchOnMount: true, // 컴포넌트 마운트 시 stale이면 갱신
        retry: 1,
        retryDelay: 1000,
      },
      // 1순위: 매매동향 데이터 (차트 필수)
      {
        queryKey: ['tradingFlow', ticker, dateRange.startDate, dateRange.endDate],
        queryFn: async () => {
          const response = await etfApi.getTradingFlow(ticker, {
            startDate: dateRange.startDate,
            endDate: dateRange.endDate
          })
          return response.data
        },
        staleTime: CACHE_STALE_TIME_FAST, // 30초
        refetchOnMount: true, // 컴포넌트 마운트 시 stale이면 갱신
        retry: 1,
        retryDelay: 1000,
      },
      // 2순위: 인사이트
      {
        queryKey: ['insights', ticker, insightsPeriod],
        queryFn: async () => {
          const response = await etfApi.getInsights(ticker, insightsPeriod)
          return response.data
        },
        staleTime: CACHE_STALE_TIME_SLOW,
        retry: 1,
      },
      // 3순위: 뉴스
      {
        queryKey: ['news', ticker, 10],
        queryFn: async () => {
          const response = await newsApi.getByTicker(ticker, { days: 7, limit: 10, analyze: true })
          return response.data
        },
        staleTime: 5 * 60 * 1000, // 5분
        retry: 1,
      },
    ],
  })

  // 쿼리 결과 분리 (분봉 제외 5개 - 분봉은 페이지 표시 후 별도 요청)
  const [
    { data: etf, isLoading: etfLoading, error: etfError },
    { data: pricesData, isLoading: pricesLoading, isFetching: pricesFetching, error: pricesError, refetch: refetchPrices },
    { data: tradingFlowData, isLoading: tradingFlowLoading, isFetching: tradingFlowFetching, error: tradingFlowError, refetch: refetchTradingFlow },
    { data: insightsData, isLoading: insightsLoading, error: insightsError },
    { data: newsData, isLoading: newsLoading, error: newsError },
  ] = queries

  // 장중 여부 판단 (09:00~15:30, 평일) - 분봉 자동 갱신 주기에 사용
  const [isMarketHours, setIsMarketHours] = useState(() => {
    const now = new Date()
    const day = now.getDay()
    const timeInMinutes = now.getHours() * 60 + now.getMinutes()
    return day >= 1 && day <= 5 && timeInMinutes >= 540 && timeInMinutes <= 930
  })

  useEffect(() => {
    const checkMarketHours = () => {
      const now = new Date()
      const day = now.getDay()
      const timeInMinutes = now.getHours() * 60 + now.getMinutes()
      setIsMarketHours(day >= 1 && day <= 5 && timeInMinutes >= 540 && timeInMinutes <= 930)
    }
    const interval = setInterval(checkMarketHours, 60_000) // 1분마다 재확인
    return () => clearInterval(interval)
  }, [])

  // 분봉 강제 새로고침 플래그 (useQuery queryFn 내부에서 참조)
  const forceRefreshRef = useRef(false)

  // 분봉: 상세 페이지가 보인 뒤에만 요청 (초기 로딩 지연 방지)
  const {
    data: intradayData,
    isLoading: intradayLoading,
    isFetching: intradayFetching,
    error: intradayError,
    refetch: refetchIntraday,
  } = useQuery({
    queryKey: ['intraday', ticker],
    queryFn: async () => {
      const isForce = forceRefreshRef.current
      forceRefreshRef.current = false
      const response = await etfApi.getIntraday(ticker, {
        autoCollect: true,
        forceRefresh: isForce,
      })
      return response.data
    },
    enabled: !!ticker && !!etf,
    staleTime: isMarketHours ? 10 * 1000 : CACHE_STALE_TIME_FAST, // 장중: 10초, 장외: 30초
    refetchInterval: (query) => {
      if (query.state.data?.background_collect_started) return 3000   // 수집 중: 3초 (장중/장외 무관)
      if (isMarketHours) return 20 * 1000                             // 장중: 20초
      return false                                                     // 장외: 자동 갱신 끔
    },
    refetchOnMount: true,
    retry: 1,
    retryDelay: 1000,
  })

  // 분봉 새로고침 버튼 핸들러 (캐시 무시 + 재수집 트리거)
  const handleIntradayRefresh = useCallback(() => {
    forceRefreshRef.current = true
    refetchIntraday()
  }, [refetchIntraday])

  // 알림 규칙 (목표가) 조회 - 분봉 차트에 표시
  const { data: alertRules = [] } = useQuery({
    queryKey: ['alertRules', ticker],
    queryFn: async () => {
      const res = await alertApi.getRules(ticker, false)
      return res.data
    },
    enabled: !!ticker,
    staleTime: 30_000,
  })

  // 상승흐름 신호 (확정 배지용)
  const { data: signalEvents = [] } = useQuery({
    queryKey: ['signalEvents', ticker],
    queryFn: async () => {
      const res = await alertApi.getSignals(ticker)
      return res.data
    },
    enabled: !!ticker,
    staleTime: CACHE_STALE_TIME_SLOW,
  })
  const confirmedSignal = useMemo(
    () => signalEvents.find(s => s.status === 'confirmed'),
    [signalEvents],
  )

  // 핵심 지표 (수익률·변동성·MDD·샤프) - ETF/STOCK 공통 (가격 기반 계산)
  const { data: metricsData } = useQuery({
    queryKey: ['metrics', ticker],
    queryFn: async () => {
      const res = await etfApi.getMetrics(ticker)
      return res.data
    },
    enabled: !!ticker && !!etf,
    staleTime: CACHE_STALE_TIME_SLOW,
    retry: 1,
  })

  // YTD 라벨 보정: 연중 상장/수집 시작 종목은 기준일이 1월 초가 아니므로
  // "YTD 수익률"이 오해를 부른다. 이 경우 실제 기간(M/D~)을 라벨에 명시한다.
  const ytdLabel = useMemo(() => {
    const start = metricsData?.ytd_start_date
    if (!start) return 'YTD 수익률'
    const [, m, d] = start.split('-').map(Number)
    // 연초 첫 거래일 근방(1월 초)이면 진짜 YTD로 간주
    if (m === 1 && d <= 10) return 'YTD 수익률'
    return `기간 수익률 (${m}/${d}~)`
  }, [metricsData?.ytd_start_date])

  // ETF 펀더멘털 (NAV·총보수·구성종목) - ETF 타입만 조회
  const { data: fundamentalsData } = useQuery({
    queryKey: ['fundamentals', ticker],
    queryFn: async () => {
      const res = await etfApi.getFundamentals(ticker)
      return res.data
    },
    enabled: !!ticker && !!etf && etf.type === 'ETF',
    staleTime: CACHE_STALE_TIME_SLOW,
    retry: 1,
  })

  // 전일 종가 (분봉 차트 + 알림 체크용)
  const previousClose = pricesData && pricesData.length >= 2 ? pricesData[1]?.close_price : null

  // 3종 알림 감지 훅
  useAlertChecker({
    ticker,
    tickerName: etf?.name || '',
    alertRules,
    intradayData,
    previousClose,
    tradingFlowData: tradingFlowData || [],
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


  // 기술지표용 확장 가격 데이터 (60일 앞선 시작일)
  const extendedDateRange = useMemo(() => {
    if (!showRSI && !showMACD) return null
    const today = new Date()
    const startDate = new Date(dateRange.startDate)
    startDate.setDate(startDate.getDate() - 60)
    return {
      startDate: format(startDate, 'yyyy-MM-dd'),
      endDate: format(today, 'yyyy-MM-dd'),
    }
  }, [showRSI, showMACD, dateRange.startDate])

  const { data: extendedPricesData } = useQuery({
    queryKey: ['prices-extended', ticker, extendedDateRange?.startDate, extendedDateRange?.endDate],
    queryFn: async () => {
      const response = await etfApi.getPrices(ticker, {
        startDate: extendedDateRange.startDate,
        endDate: extendedDateRange.endDate,
      })
      return response.data
    },
    enabled: !!ticker && !!extendedDateRange,
    staleTime: CACHE_STALE_TIME_FAST,
    retry: 1,
  })

  // RSI/MACD 계산 (확장 데이터 사용, 오름차순으로 변환)
  const rsiData = useMemo(() => {
    if (!showRSI || !extendedPricesData || extendedPricesData.length < 15) return []
    const ascending = [...extendedPricesData].reverse()
    return calculateRSI(ascending, 14)
  }, [showRSI, extendedPricesData])

  const macdData = useMemo(() => {
    if (!showMACD || !extendedPricesData || extendedPricesData.length < 35) return []
    const ascending = [...extendedPricesData].reverse()
    return calculateMACD(ascending, 12, 26, 9)
  }, [showMACD, extendedPricesData])

  // 지지선/저항선 계산 (pricesData는 내림차순)
  const supportResistanceData = useMemo(() => {
    return calculateSupportResistance(pricesData)
  }, [pricesData])

  // 최근 가격 정보 계산
  // API는 날짜 내림차순(최신이 첫 번째)으로 반환
  const latestPrice = useMemo(() => {
    if (!pricesData || pricesData.length === 0) return null
    return pricesData[0]
  }, [pricesData])

  // 매입가 대비 수익률 계산
  const purchaseReturn = useMemo(() => {
    if (!etf?.purchase_price || !latestPrice?.close_price) return null
    return ((latestPrice.close_price - etf.purchase_price) / etf.purchase_price) * 100
  }, [etf?.purchase_price, latestPrice?.close_price])

  // 평가 금액 계산 (종가 × 보유 수량)
  const evaluationAmount = useMemo(() => {
    // quantity가 0일 수도 있으므로 명시적으로 null/undefined 체크
    if (etf?.quantity == null || etf?.quantity === undefined || !latestPrice?.close_price) {
      return null
    }
    // 평가 금액 = 종가 × 보유 수량
    const amount = latestPrice.close_price * etf.quantity
    return amount
  }, [etf?.quantity, latestPrice?.close_price])

  // 총 투자 금액 계산 (매입가 × 보유 수량)
  const totalInvestment = useMemo(() => {
    if (etf?.purchase_price == null || etf?.quantity == null || etf?.quantity === undefined) {
      return null
    }
    // 총 투자 금액 = 매입가 × 보유 수량
    const amount = etf.purchase_price * etf.quantity
    return amount
  }, [etf?.purchase_price, etf?.quantity])

  // 현재 손익 계산 (평가 금액 - 총 투자 금액)
  const currentProfitLoss = useMemo(() => {
    if (evaluationAmount == null || totalInvestment == null) {
      return null
    }
    // 현재 손익 = 평가 금액 - 총 투자 금액
    const profitLoss = evaluationAmount - totalInvestment
    return profitLoss
  }, [evaluationAmount, totalInvestment])

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
      <ETFHeader etf={etf} />

      {/* 상승흐름 확정 배지 */}
      {confirmedSignal && (
        <div className="px-1 mt-2">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
            <span aria-hidden="true">▲</span>
            상승흐름 확정
            {confirmedSignal.confirmed_date && (
              <span className="font-normal">
                ({String(confirmedSignal.confirmed_date).slice(5, 10).replace('-', '/')})
              </span>
            )}
          </span>
        </div>
      )}

      {/* ========================================== */}
      {/* 기본 보기: 누구나 이해할 수 있는 핵심 정보   */}
      {/* ========================================== */}

      {/* 1. 투자 인사이트 요약 (한눈에 보는 핵심 포인트 — 계산은 백엔드 /insights) */}
      <InsightSummary insights={insightsData} />

      {/* 2. 투자 전략 (단기/중기/장기 방향) */}
      <div className="mb-6">
        <StrategySummary 
          ticker={ticker} 
          period={insightsPeriod}
          insights={insightsData}
          isLoading={insightsLoading}
          error={insightsError}
        />
      </div>

      {/* 3. 기본 정보 + 내 투자 현황 */}
      <ETFBasicInfo
        etf={etf}
        latestPrice={latestPrice}
        purchaseReturn={purchaseReturn}
        totalInvestment={totalInvestment}
        evaluationAmount={evaluationAmount}
        currentProfitLoss={currentProfitLoss}
      />

      {/* 3.5 핵심 지표 (수익률·변동성·리스크) - ETF/STOCK 공통 */}
      <ETFKeyMetrics metricsData={metricsData} ytdLabel={ytdLabel} />

      {/* 3.6 ETF 정보 (NAV·총보수·구성종목) - ETF 타입만 */}
      <ETFFundamentalInfo etf={etf} fundamentalsData={fundamentalsData} latestPrice={latestPrice} />

      {/* 4. 날짜 범위 선택 + 가격 차트 (가장 기본적인 차트) */}
      <DateRangeSelector
        key={`${defaultRangeFromSettings}-${settings.defaultDateRange}`}
        onDateRangeChange={handleDateRangeChange}
        defaultRange={defaultRangeFromSettings}
      />

      <ETFCharts
        pricesData={pricesData}
        tradingFlowData={tradingFlowData}
        ticker={ticker}
        dateRange={dateRange.range}
        showVolume={settings.display.showVolume}
        showTradingFlow={settings.display.showTradingFlow}
        pricesLoading={pricesLoading}
        pricesFetching={pricesFetching}
        tradingFlowLoading={tradingFlowLoading}
        tradingFlowFetching={tradingFlowFetching}
        pricesError={pricesError}
        tradingFlowError={tradingFlowError}
        refetchPrices={refetchPrices}
        refetchTradingFlow={refetchTradingFlow}
        priceChartScrollRef={priceChartScrollRef}
        tradingFlowChartScrollRef={tradingFlowChartScrollRef}
        onPriceChartScroll={handlePriceChartScroll}
        onTradingFlowChartScroll={handleTradingFlowChartScroll}
        purchasePrice={etf?.purchase_price}
        rsiData={rsiData}
        macdData={macdData}
        showRSI={showRSI}
        showMACD={showMACD}
        onToggleRSI={() => setShowRSI(v => !v)}
        onToggleMACD={() => setShowMACD(v => !v)}
        supportResistanceData={supportResistanceData}
        showTechnicalSection={true}
      />

      {/* 5. 오늘의 실시간 체결 (분봉 차트) */}
      <div className="card mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              오늘의 가격 흐름
            </h3>
            {intradayData?.date && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {intradayData.date}
              </span>
            )}
            {intradayFetching && (
              <span className="text-xs text-blue-500 animate-pulse">갱신 중...</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {intradayData?.first_time && intradayData?.last_time && (
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {intradayData.first_time} ~ {intradayData.last_time}
              </span>
            )}
            <button
              onClick={handleIntradayRefresh}
              className="btn btn-outline btn-sm"
              disabled={intradayFetching}
              title="새로고침"
            >
              <svg className={`w-4 h-4 ${intradayFetching ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>

        {intradayLoading ? (
          <div className="flex items-center justify-center h-[300px]">
            <Spinner />
          </div>
        ) : intradayError ? (
          <div className="flex flex-col items-center justify-center h-[300px] text-gray-500 dark:text-gray-400">
            <p>데이터를 불러올 수 없습니다</p>
            <button
              onClick={() => refetchIntraday()}
              className="mt-2 text-sm text-blue-500 hover:underline"
            >
              다시 시도
            </button>
          </div>
        ) : intradayData?.background_collect_started ? (
          <div className="flex flex-col items-center justify-center h-[300px] text-gray-500 dark:text-gray-400 gap-2">
            <Spinner />
            <p className="text-sm">데이터 수집 중입니다.</p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              잠시 후 자동으로 갱신됩니다.
            </p>
          </div>
        ) : (
          <IntradayChart
            data={intradayData?.data || []}
            ticker={ticker}
            height={300}
            showVolume={settings.display.showVolume}
            previousClose={previousClose}
            pivotLevels={supportResistanceData?.pivot}
            priceTargets={alertRules}
          />
        )}

        {intradayData?.count === 0 && !intradayLoading && !intradayData?.background_collect_started && (
          <p className="text-center text-sm text-gray-400 dark:text-gray-500 mt-2">
            장중이 아니거나 휴장일입니다. 장 시작 후 데이터가 수집됩니다.
          </p>
        )}

        {/* 목표가 설정 패널 */}
        <PriceTargetPanel
          ticker={ticker}
          currentPrice={
            intradayData?.data?.length > 0
              ? intradayData.data[intradayData.data.length - 1].price
              : pricesData?.[0]?.close_price ?? null
          }
        />
      </div>

      {/* 6. 최근 뉴스 */}
      <div className="card mb-4">
        <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">최근 뉴스</h3>
        <NewsTimeline ticker={ticker} newsData={newsData} isLoading={newsLoading} error={newsError} />
      </div>

      {/* ========================================== */}
      {/* 고급 분석: 전문 투자자를 위한 상세 지표      */}
      {/* ========================================== */}

      {/* 가격 데이터 테이블 */}
      <div className="space-y-4 animate-fadeIn">
          {pricesData && pricesData.length > 0 && (
            <div className="card">
              <button
                onClick={() => setIsTableExpanded(!isTableExpanded)}
                className="w-full flex items-center justify-between text-left"
              >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  가격 데이터 ({pricesData.length}건)
                </h3>
                <span className="text-sm text-gray-400 dark:text-gray-500 flex items-center gap-1">
                  {isTableExpanded ? (
                    <>접기 <span className="text-xs">▲</span></>
                  ) : (
                    <>펼치기 <span className="text-xs">▼</span></>
                  )}
                </span>
              </button>

              {isTableExpanded && (
                <div className="mt-4">
                  <PriceTable data={pricesData} itemsPerPage={20} />
                </div>
              )}
            </div>
          )}
        </div>
    </div>
  )
}
