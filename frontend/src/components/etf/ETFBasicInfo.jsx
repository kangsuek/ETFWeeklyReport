import PropTypes from 'prop-types'
import { format } from 'date-fns'
import { formatPrice, formatNumber, formatPercent, getPriceChangeColor } from '../../utils/format'

/**
 * ETFBasicInfo 컴포넌트
 * ETFDetail 섹션 3 — 종목 기본 정보 + 최근 가격/내 투자 현황 카드
 */
export default function ETFBasicInfo({
  etf,
  latestPrice,
  purchaseReturn,
  totalInvestment,
  evaluationAmount,
  currentProfitLoss,
}) {
  return (
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
            {/* 일자 */}
            <div className="pb-3 border-b border-gray-200 dark:border-gray-700">
              <span className="text-sm text-gray-500 dark:text-gray-400">기준일</span>
              <p className="text-lg font-bold mt-0.5 text-gray-900 dark:text-gray-100">
                {format(new Date(latestPrice.date), 'yyyy-MM-dd')}
              </p>
            </div>
            {/* 핵심 가격 정보 */}
            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">종가</span>
                <p className="text-xl font-bold mt-0.5 text-gray-900 dark:text-gray-100">{formatPrice(latestPrice.close_price)}</p>
              </div>
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">전일 대비</span>
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
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">보유 수량</span>
                <p className="text-xl font-bold mt-0.5 text-gray-900 dark:text-gray-100">
                  {etf?.quantity != null && etf.quantity !== undefined ? formatNumber(etf.quantity) : '-'}
                </p>
              </div>
              <div>
                <span className="text-sm text-gray-500 dark:text-gray-400">총 투자 금액</span>
                <p className="text-xl font-bold mt-0.5 text-gray-900 dark:text-gray-100">
                  {totalInvestment != null && totalInvestment !== undefined ? formatPrice(totalInvestment) : '-'}
                </p>
              </div>
            </div>

            {/* 평가 금액 / 손익 */}
            {(evaluationAmount != null || currentProfitLoss != null) && (
              <div className="grid grid-cols-2 gap-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-3">
                  <span className="text-xs text-blue-600 dark:text-blue-400">평가 금액</span>
                  <p className="text-lg font-bold text-blue-700 dark:text-blue-300 mt-0.5">
                    {evaluationAmount != null ? formatPrice(evaluationAmount) : '-'}
                  </p>
                </div>
                <div className={`rounded-lg p-3 ${
                  currentProfitLoss != null && currentProfitLoss >= 0
                    ? 'bg-red-50 dark:bg-red-900/30'
                    : 'bg-blue-50 dark:bg-blue-900/30'
                }`}>
                  <span className={`text-xs ${
                    currentProfitLoss != null && currentProfitLoss >= 0
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-blue-600 dark:text-blue-400'
                  }`}>현재 손익</span>
                  <p className={`text-lg font-bold mt-0.5 ${getPriceChangeColor(currentProfitLoss)}`}>
                    {currentProfitLoss != null
                      ? `${currentProfitLoss >= 0 ? '+' : ''}${formatPrice(currentProfitLoss)}`
                      : '-'
                    }
                  </p>
                  {purchaseReturn !== null && (
                    <span className={`text-xs ${getPriceChangeColor(purchaseReturn)}`}>
                      ({formatPercent(purchaseReturn)})
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">가격 데이터가 없습니다</p>
        )}
      </div>
    </div>
  )
}

ETFBasicInfo.propTypes = {
  etf: PropTypes.object,
  latestPrice: PropTypes.object,
  purchaseReturn: PropTypes.number,
  totalInvestment: PropTypes.number,
  evaluationAmount: PropTypes.number,
  currentProfitLoss: PropTypes.number,
}
