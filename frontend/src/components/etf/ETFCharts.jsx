import PropTypes from 'prop-types'
import PriceChart from '../charts/PriceChart'
import TradingFlowChart from '../charts/TradingFlowChart'
import RSIChart from '../charts/RSIChart'
import MACDChart from '../charts/MACDChart'
import LoadingIndicator from '../common/LoadingIndicator'
import ErrorFallback from '../common/ErrorFallback'

/**
 * ETFCharts 컴포넌트
 * ETF 상세 페이지의 차트 섹션 (가격 차트, 매매 동향 차트, RSI, MACD)
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
  rsiData,
  macdData,
  showRSI,
  showMACD,
  onToggleRSI,
  onToggleMACD,
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

      {/* 기술지표 토글 + 차트 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 transition-all duration-300 ease-in-out hover:shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">기술지표</h3>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={showRSI}
                onChange={onToggleRSI}
                className="w-4 h-4 text-purple-500 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-purple-500 focus:ring-2"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">RSI</span>
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={showMACD}
                onChange={onToggleMACD}
                className="w-4 h-4 text-blue-500 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">MACD</span>
            </label>
          </div>
        </div>

        {!showRSI && !showMACD && (
          <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-4">
            RSI 또는 MACD를 선택하면 기술지표 차트가 표시됩니다
          </p>
        )}

        {showRSI && rsiData && (
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              RSI (14)
              {rsiData.length > 0 && rsiData[rsiData.length - 1]?.rsi != null && (
                <span className={`ml-2 font-semibold ${
                  rsiData[rsiData.length - 1].rsi >= 70
                    ? 'text-red-500'
                    : rsiData[rsiData.length - 1].rsi <= 30
                      ? 'text-blue-500'
                      : 'text-gray-700 dark:text-gray-300'
                }`}>
                  {rsiData[rsiData.length - 1].rsi.toFixed(1)}
                </span>
              )}
            </h4>
            <RSIChart data={rsiData} />
          </div>
        )}

        {showMACD && macdData && (
          <div>
            <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              MACD (12, 26, 9)
            </h4>
            <MACDChart data={macdData} />
          </div>
        )}
      </div>
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
  rsiData: PropTypes.array,
  macdData: PropTypes.array,
  showRSI: PropTypes.bool,
  showMACD: PropTypes.bool,
  onToggleRSI: PropTypes.func,
  onToggleMACD: PropTypes.func,
}
