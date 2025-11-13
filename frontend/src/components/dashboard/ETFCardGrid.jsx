import PropTypes from 'prop-types'
import ETFCard from '../etf/ETFCard'

/**
 * ETFCardGrid 컴포넌트
 * 대시보드의 ETF 카드 그리드 레이아웃
 * 
 * @param {Object} props
 * @param {Array} props.etfs - ETF 배열
 * @param {boolean} props.compactMode - 컴팩트 모드 여부
 */
export default function ETFCardGrid({ etfs, compactMode = false }) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6 ${
      compactMode ? 'gap-3 sm:gap-4' : ''
    }`}>
      {etfs.map((etf) => (
        <ETFCard key={etf.ticker} etf={etf} compactMode={compactMode} />
      ))}
    </div>
  )
}

ETFCardGrid.propTypes = {
  etfs: PropTypes.arrayOf(
    PropTypes.shape({
      ticker: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['ETF', 'STOCK']).isRequired,
      theme: PropTypes.string,
      expense_ratio: PropTypes.number,
    })
  ).isRequired,
  compactMode: PropTypes.bool,
}

