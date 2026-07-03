import PropTypes from 'prop-types'
import { formatPercent, getPriceChangeColor } from '../../utils/format'

/**
 * ETFKeyMetrics 컴포넌트
 * ETFDetail 섹션 3.5 — 핵심 지표 (수익률·변동성·리스크, ETF/STOCK 공통)
 * 값은 백엔드 GET /api/etfs/{ticker}/metrics 응답을 표시만 한다.
 */
export default function ETFKeyMetrics({ metricsData, ytdLabel }) {
  if (!metricsData) return null

  return (
    <div className="card mb-4">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">핵심 지표</h3>
        <span className="text-xs text-gray-400 dark:text-gray-500">가격 기반 계산 (ETF·종목 공통)</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { label: '1주 수익률', value: metricsData.returns?.['1w'], mode: 'signed' },
          { label: '1개월 수익률', value: metricsData.returns?.['1m'], mode: 'signed' },
          { label: ytdLabel, value: metricsData.returns?.ytd, mode: 'signed' },
          { label: '연환산 변동성', value: metricsData.volatility, mode: 'neutralpct' },
          { label: '최대낙폭(MDD)', value: metricsData.max_drawdown, mode: 'signed' },
          { label: '샤프지수', value: metricsData.sharpe_ratio, mode: 'ratio' },
        ].map(({ label, value, mode }) => {
          let display = '-'
          let colorClass = 'text-gray-900 dark:text-gray-100'
          if (value != null && !isNaN(value)) {
            if (mode === 'neutralpct') {
              display = `${value.toFixed(2)}%`
            } else if (mode === 'ratio') {
              display = value.toFixed(2)
              colorClass = getPriceChangeColor(value)
            } else {
              display = formatPercent(value)
              colorClass = getPriceChangeColor(value)
            }
          }
          return (
            <div key={label} className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
              <span className="text-xs text-gray-500 dark:text-gray-400 block">{label}</span>
              <p className={`text-lg font-bold mt-0.5 ${colorClass}`}>{display}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

ETFKeyMetrics.propTypes = {
  metricsData: PropTypes.shape({
    returns: PropTypes.object,
    volatility: PropTypes.number,
    max_drawdown: PropTypes.number,
    sharpe_ratio: PropTypes.number,
  }),
  ytdLabel: PropTypes.string.isRequired,
}
