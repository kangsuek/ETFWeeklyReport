import { useState, useMemo, useRef, useCallback, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { etfApi } from '../services/api'
import { useSettings } from '../contexts/SettingsContext'
import PageHeader from '../components/common/PageHeader'
import Spinner from '../components/common/Spinner'
import ErrorFallback from '../components/common/ErrorFallback'
import DateRangeSelector from '../components/charts/DateRangeSelector'
import StatsSummary from '../components/etf/StatsSummary'
import PriceTable from '../components/etf/PriceTable'
import NewsTimeline from '../components/news/NewsTimeline'
import ETFHeader from '../components/etf/ETFHeader'
import ETFCharts from '../components/etf/ETFCharts'
import { formatPrice, formatNumber, formatPercent, getPriceChangeColor } from '../utils/format'
import { CACHE_STALE_TIME_STATIC, CACHE_STALE_TIME_FAST } from '../constants'

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
    staleTime: CACHE_STALE_TIME_STATIC, // 5분 (정적 데이터)
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
    staleTime: CACHE_STALE_TIME_FAST, // 30초 (가격 데이터)
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
    staleTime: CACHE_STALE_TIME_FAST, // 30초 (매매동향 데이터)
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
  
  // 디버깅: etf 객체 확인
  useEffect(() => {
    if (etf) {
      console.log('ETF Detail Data:', {
        ticker: etf.ticker,
        purchase_price: etf.purchase_price,
        quantity: etf.quantity,
        quantityType: typeof etf.quantity,
        latestPrice: latestPrice?.close_price,
        evaluationAmount: evaluationAmount
      })
    }
  }, [etf, latestPrice, evaluationAmount])

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
            {etf?.purchase_date && (
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">구매일</span>
                <p className="text-base font-semibold mt-0.5 text-gray-900 dark:text-gray-100">
                  {format(new Date(etf.purchase_date), 'yyyy-MM-dd')}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* 최근 가격 정보 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">최근 가격 정보</h3>
          {latestPrice ? (
            <div className="space-y-3">
              {/* 일자 - 가장 먼저 표시 */}
              <div className="pb-3 border-b border-gray-200 dark:border-gray-700">
                <span className="text-sm text-gray-500 dark:text-gray-400">기준일</span>
                <p className="text-lg font-bold mt-0.5 text-gray-900 dark:text-gray-100">
                  {format(new Date(latestPrice.date), 'yyyy-MM-dd')}
                </p>
              </div>
              {/* 가격 정보 그리드 */}
            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">종가</span>
                <p className="text-xl font-bold mt-0.5 text-gray-900 dark:text-gray-100">{formatPrice(latestPrice.close_price)}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">전일 대비 등락률</span>
                <p className={`text-xl font-bold mt-0.5 ${getPriceChangeColor(latestPrice.daily_change_pct)}`}>
                  {formatPercent(latestPrice.daily_change_pct)}
                </p>
              </div>
              {etf?.purchase_price && (
                <>
                  <div>
                    <span className="text-sm text-gray-500 dark:text-gray-400">매입가</span>
                    <p className="text-xl font-bold mt-0.5 text-gray-900 dark:text-gray-100">{formatPrice(etf.purchase_price)}</p>
                  </div>
                  {purchaseReturn !== null && (
                    <div>
                      <span className="text-sm text-gray-500 dark:text-gray-400">매입 대비 수익률</span>
                      <p className={`text-xl font-bold mt-0.5 ${getPriceChangeColor(purchaseReturn)}`}>
                        {formatPercent(purchaseReturn)}
                      </p>
                    </div>
                  )}
                </>
              )}
              {/* 보유 수량 */}
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">보유 수량</span>
                <p className="text-xl font-bold mt-0.5 text-gray-900 dark:text-gray-100">
                  {etf?.quantity != null && etf.quantity !== undefined ? formatNumber(etf.quantity) : '-'}
                </p>
              </div>
              {/* 평가 금액 */}
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">평가 금액</span>
                <p className="text-xl font-bold mt-0.5 text-gray-900 dark:text-gray-100">
                  {evaluationAmount != null && evaluationAmount !== undefined ? formatPrice(evaluationAmount) : '-'}
                </p>
              </div>
              {/* 총 투자 금액 */}
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">총 투자 금액</span>
                <p className="text-xl font-bold mt-0.5 text-gray-900 dark:text-gray-100">
                  {totalInvestment != null && totalInvestment !== undefined ? formatPrice(totalInvestment) : '-'}
                </p>
              </div>
              {/* 현재 손익 */}
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">현재 손익</span>
                <p className={`text-xl font-bold mt-0.5 ${
                  currentProfitLoss != null && currentProfitLoss !== undefined
                    ? getPriceChangeColor(currentProfitLoss)
                    : 'text-gray-900 dark:text-gray-100'
                }`}>
                  {currentProfitLoss != null && currentProfitLoss !== undefined 
                    ? `${currentProfitLoss >= 0 ? '+' : ''}${formatPrice(currentProfitLoss)}`
                    : '-'
                  }
                </p>
              </div>
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

      {/* 통계 요약 섹션 */}
      {pricesData && pricesData.length > 0 && (
        <div className="card mb-4">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">통계 요약</h3>
          <StatsSummary 
            data={pricesData} 
            purchasePrice={etf?.purchase_price}
            purchaseDate={etf?.purchase_date}
          />
        </div>
      )}

      {/* 차트 섹션 */}
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
      />

      {/* 가격 데이터 테이블 섹션 */}
      {pricesData && pricesData.length > 0 && (
        <div className="card mb-4">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">가격 데이터</h3>
          <PriceTable data={pricesData} itemsPerPage={20} />
        </div>
      )}

      {/* 뉴스 타임라인 섹션 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-3">최근 뉴스</h3>
        <NewsTimeline ticker={ticker} />
      </div>
    </div>
  )
}
