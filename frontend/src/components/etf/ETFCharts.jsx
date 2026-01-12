import PropTypes from 'prop-types'
import PriceChart from '../charts/PriceChart'
import TradingFlowChart from '../charts/TradingFlowChart'
import LoadingIndicator from '../common/LoadingIndicator'
import ErrorFallback from '../common/ErrorFallback'

/**
 * ETFCharts 컴포넌트
 * ETF 상세 페이지의 차트 섹션 (가격 차트, 매매 동향 차트)
 * 
 * @param {Object} props
 * @param {Array} props.pricesData - 가격 데이터 배열
 * @param {Array} props.tradingFlowData - 매매 동향 데이터 배열
 * @param {string} props.ticker - 종목 티커
 * @param {string} props.dateRange - 날짜 범위 ('7d', '1m', '3m', 'custom')
 * @param {boolean} props.showVolume - 거래량 표시 여부
 * @param {boolean} props.showTradingFlow - 매매 동향 표시 여부
 * @param {boolean} props.pricesLoading - 가격 데이터 로딩 상태
 * @param {boolean} props.pricesFetching - 가격 데이터 페칭 상태
 * @param {boolean} props.tradingFlowLoading - 매매 동향 데이터 로딩 상태
 * @param {boolean} props.tradingFlowFetching - 매매 동향 데이터 페칭 상태
 * @param {Object} props.pricesError - 가격 데이터 에러
 * @param {Object} props.tradingFlowError - 매매 동향 데이터 에러
 * @param {Function} props.refetchPrices - 가격 데이터 재조회 함수
 * @param {Function} props.refetchTradingFlow - 매매 동향 데이터 재조회 함수
 * @param {Object} props.priceChartScrollRef - 가격 차트 스크롤 ref
 * @param {Object} props.tradingFlowChartScrollRef - 매매 동향 차트 스크롤 ref
 * @param {Function} props.onPriceChartScroll - 가격 차트 스크롤 핸들러
 * @param {Function} props.onTradingFlowChartScroll - 매매 동향 차트 스크롤 핸들러
 */
export default function ETFCharts({
  pricesData,
  tradingFlowData,
  ticker,
  dateRange,
  showVolume,
  showTradingFlow,
  pricesLoading,
  pricesFetching,
  tradingFlowLoading,
  tradingFlowFetching,
  pricesError,
  tradingFlowError,
  refetchPrices,
  refetchTradingFlow,
  priceChartScrollRef,
  tradingFlowChartScrollRef,
  onPriceChartScroll,
  onTradingFlowChartScroll,
  purchasePrice,
}) {
  return (
    <div className="space-y-4 mb-4">
      {/* 가격 차트 (거래량 포함) */}
      {showVolume && (
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
              dateRange={dateRange}
              scrollRef={priceChartScrollRef}
              onScroll={onPriceChartScroll}
              purchasePrice={purchasePrice}
            />
          )}
        </div>
      )}

      {/* 매매 동향 차트 */}
      {showTradingFlow && (
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
              dateRange={dateRange}
              scrollRef={tradingFlowChartScrollRef}
              onScroll={onTradingFlowChartScroll}
            />
          )}
        </div>
      )}
    </div>
  )
}

ETFCharts.propTypes = {
  pricesData: PropTypes.array,
  tradingFlowData: PropTypes.array,
  ticker: PropTypes.string.isRequired,
  dateRange: PropTypes.string.isRequired,
  showVolume: PropTypes.bool,
  showTradingFlow: PropTypes.bool,
  pricesLoading: PropTypes.bool,
  pricesFetching: PropTypes.bool,
  tradingFlowLoading: PropTypes.bool,
  tradingFlowFetching: PropTypes.bool,
  pricesError: PropTypes.object,
  tradingFlowError: PropTypes.object,
  refetchPrices: PropTypes.func,
  refetchTradingFlow: PropTypes.func,
  priceChartScrollRef: PropTypes.object,
  tradingFlowChartScrollRef: PropTypes.object,
  onPriceChartScroll: PropTypes.func,
  onTradingFlowChartScroll: PropTypes.func,
  purchasePrice: PropTypes.number,
}

