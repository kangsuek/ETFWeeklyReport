import { useMemo } from 'react'
import PropTypes from 'prop-types'
import { format } from 'date-fns'
import { formatPrice, formatVolume, formatPercent } from '../../utils/format'
import { calculateStats } from '../../utils/returns'

/**
 * StatCard 컴포넌트
 * 개별 통계 카드를 표시
 */
const StatCard = ({ title, children, icon }) => (
  <div className="bg-white dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600 shadow-sm hover:shadow-md transition-shadow">
    <div className="flex items-center gap-2 mb-3">
      {icon && <span className="text-2xl">{icon}</span>}
      <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{title}</h4>
    </div>
    <div className="space-y-2">{children}</div>
  </div>
)

StatCard.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
  icon: PropTypes.string,
}

/**
 * StatItem 컴포넌트
 * 통계 항목 표시
 */
const StatItem = ({ label, value, color = 'text-gray-900 dark:text-gray-100' }) => (
  <div className="flex items-center justify-between">
    <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
    <span className={`text-sm font-semibold ${color}`}>{value}</span>
  </div>
)

StatItem.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  color: PropTypes.string,
}

/**
 * ProgressBar 컴포넌트
 * 진행률 바 표시
 */
const ProgressBar = ({ value, min, max, label, formatValue }) => {
  const percentage = ((value - min) / (max - min)) * 100

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
        <span className="text-xs font-semibold text-gray-900 dark:text-gray-100">{formatValue(value)}</span>
      </div>
      <div className="w-full h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 dark:bg-blue-600 transition-all duration-300"
          style={{ width: `${Math.max(0, Math.min(100, percentage))}%` }}
        ></div>
      </div>
    </div>
  )
}

ProgressBar.propTypes = {
  value: PropTypes.number.isRequired,
  min: PropTypes.number.isRequired,
  max: PropTypes.number.isRequired,
  label: PropTypes.string.isRequired,
  formatValue: PropTypes.func.isRequired,
}

/**
 * PriceRangeBar 컴포넌트
 * 가격 범위를 막대 형태로 표시 (최저가 ---|현재가----- 최고가)
 */
const PriceRangeBar = ({ currentPrice, minPrice, maxPrice, formatPrice }) => {
  // 현재가가 범위를 벗어나는 경우 처리
  const clampedCurrentPrice = Math.max(minPrice, Math.min(maxPrice, currentPrice))
  const percentage = ((clampedCurrentPrice - minPrice) / (maxPrice - minPrice)) * 100

  // 현재가 레이블이 최저가/최고가와 겹치지 않도록 위치 조정
  const currentLabelLeft = Math.max(15, Math.min(85, percentage)) // 최소 15%, 최대 85%

  return (
    <div className="relative">
      {/* 막대 */}
      <div className="relative w-full h-3 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden mb-2">
        {/* 전체 막대 배경 */}
        <div className="absolute inset-0 bg-gradient-to-r from-blue-200 via-gray-200 to-red-200 dark:from-blue-800 dark:via-gray-600 dark:to-red-800"></div>
        
        {/* 현재가 마커 */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-gray-900 dark:bg-gray-100 z-10"
          style={{ left: `${percentage}%`, transform: 'translateX(-50%)' }}
        >
          {/* 마커 상단 화살표 */}
          <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-[4px] border-r-[4px] border-b-[4px] border-transparent border-b-gray-900 dark:border-b-gray-100"></div>
        </div>
      </div>

      {/* 가격 레이블 (아래쪽) */}
      <div className="relative flex items-start justify-between" style={{ minHeight: '3rem' }}>
        {/* 최저가 (왼쪽) */}
        <div className="flex flex-col items-start">
          <span className="text-xs text-gray-500 dark:text-gray-400">최저가</span>
          <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">
            {formatPrice(minPrice)}
          </span>
        </div>

        {/* 현재가 (중간 위치) */}
        <div 
          className="flex flex-col items-center absolute"
          style={{ left: `${currentLabelLeft}%`, transform: 'translateX(-50%)' }}
        >
          <span className="text-xs text-gray-500 dark:text-gray-400">현재가</span>
          <span className="text-xs font-semibold text-gray-900 dark:text-gray-100">
            {formatPrice(currentPrice)}
          </span>
        </div>

        {/* 최고가 (오른쪽) */}
        <div className="flex flex-col items-end">
          <span className="text-xs text-gray-500 dark:text-gray-400">최고가</span>
          <span className="text-xs font-semibold text-red-600 dark:text-red-400">
            {formatPrice(maxPrice)}
          </span>
        </div>
      </div>
    </div>
  )
}

PriceRangeBar.propTypes = {
  currentPrice: PropTypes.number.isRequired,
  minPrice: PropTypes.number.isRequired,
  maxPrice: PropTypes.number.isRequired,
  formatPrice: PropTypes.func.isRequired,
}

/**
 * StatsSummary 컴포넌트
 * 가격 데이터의 통계 요약을 카드 형태로 표시
 *
 * 기능:
 * - 기간 수익률 / 연환산 수익률
 * - 변동성 (표준편차) / Max Drawdown
 * - 가격 범위 (최고가, 최저가, 평균가)
 * - 거래량 통계 (평균, 최대)
 * - 카드 레이아웃 (2x2 그리드)
 * - 시각적 표시 (아이콘, 진행률 바)
 */
export default function StatsSummary({ data = [] }) {
  const stats = useMemo(() => calculateStats(data), [data])

  // 데이터가 없거나 통계 계산 실패
  if (!stats) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <p>통계를 계산할 데이터가 부족합니다</p>
        <p className="text-sm mt-1">최소 2개 이상의 데이터가 필요합니다</p>
      </div>
    )
  }

  // 수익률 색상
  const getReturnColor = (value) => {
    if (value > 0) return 'text-red-600 dark:text-red-400'
    if (value < 0) return 'text-blue-600 dark:text-blue-400'
    return 'text-gray-500 dark:text-gray-400'
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* 수익률 카드 */}
      <StatCard title="수익률" icon="📈">
        <StatItem
          label="기간 수익률"
          value={formatPercent(stats.periodReturn)}
          color={getReturnColor(stats.periodReturn)}
        />
        <StatItem
          label="연환산 수익률"
          value={formatPercent(stats.annualizedReturn)}
          color={getReturnColor(stats.annualizedReturn)}
        />
        <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-600">
          <div className="flex items-center gap-2">
            <div
              className={`flex-1 h-2 rounded-full ${
                stats.periodReturn >= 0
                  ? 'bg-gradient-to-r from-gray-200 to-red-500 dark:from-gray-600 dark:to-red-600'
                  : 'bg-gradient-to-r from-blue-500 to-gray-200 dark:from-blue-600 dark:to-gray-600'
              }`}
            ></div>
          </div>
        </div>
      </StatCard>

      {/* 가격 범위 카드 */}
      <StatCard title="가격 범위" icon="💰">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500 dark:text-gray-400">최고가</span>
          <span className="text-sm font-semibold text-red-600 dark:text-red-400">
            {formatPrice(stats.highPrice)}
            {stats.highPriceDate && (
              <span className="text-xs text-gray-400 dark:text-gray-500 ml-1">
                ({format(new Date(stats.highPriceDate), 'MM-dd')})
              </span>
            )}
          </span>
        </div>
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">최저가</span>
          <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
            {formatPrice(stats.lowPrice)}
            {stats.lowPriceDate && (
              <span className="text-xs text-gray-400 dark:text-gray-500 ml-1">
                ({format(new Date(stats.lowPriceDate), 'MM-dd')})
              </span>
            )}
          </span>
        </div>
        <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-600">
          <PriceRangeBar
            currentPrice={stats.currentPrice}
            minPrice={stats.lowPrice}
            maxPrice={stats.highPrice}
            formatPrice={formatPrice}
          />
        </div>
      </StatCard>
    </div>
  )
}

StatsSummary.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      date: PropTypes.string.isRequired,
      close_price: PropTypes.number.isRequired,
      volume: PropTypes.number.isRequired,
    })
  ),
}
