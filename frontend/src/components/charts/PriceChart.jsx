import { useMemo, memo, useState } from 'react'
import PropTypes from 'prop-types'
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { format } from 'date-fns'
import { formatPrice, formatVolume, getPriceChangeColorHex } from '../../utils/format'
import { useContainerWidth } from '../../hooks/useContainerWidth'
import { useWindowSize } from '../../hooks/useWindowSize'
import { sampleData, validateChartData } from '../../utils/chartUtils'
import { COLORS, MAX_CHART_POINTS } from '../../constants'

/**
 * CustomLegend 컴포넌트
 * 체크박스가 포함된 커스텀 범례
 */
const CustomLegend = ({ payload, showMA5, setShowMA5, showMA10, setShowMA10, showMA20, setShowMA20 }) => {
  // 이동평균선 항목은 범례에서 제외
  const filteredPayload = payload.filter(entry =>
    !entry.value.includes('이동평균선')
  )

  return (
    <div className="flex justify-center gap-6 pt-4 pb-2 text-sm flex-wrap">
      {/* 기본 범례 항목 (종가, 거래량만) */}
      {filteredPayload.map((entry, index) => {
        const { value, color } = entry
        return (
          <div key={`legend-${index}`} className="flex items-center gap-2">
            {entry.type === 'line' ? (
              <span className="inline-block w-8 h-1" style={{ backgroundColor: color }}></span>
            ) : (
              <span className="inline-block w-4 h-4" style={{ backgroundColor: color }}></span>
            )}
            <span style={{ color }}>{value}</span>
          </div>
        )
      })}

      {/* 이동평균선 체크박스 (항상 표시) */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showMA5}
          onChange={(e) => setShowMA5(e.target.checked)}
          className="w-4 h-4 cursor-pointer"
        />
        <span className="inline-block w-8 h-1" style={{ backgroundColor: COLORS.MA_5 }}></span>
        <span className="text-gray-700 dark:text-gray-300" style={{ color: COLORS.MA_5 }}>5일 이동평균선</span>
      </label>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showMA10}
          onChange={(e) => setShowMA10(e.target.checked)}
          className="w-4 h-4 cursor-pointer"
        />
        <span className="inline-block w-8 h-1" style={{ backgroundColor: COLORS.MA_10 }}></span>
        <span className="text-gray-700 dark:text-gray-300" style={{ color: COLORS.MA_10 }}>10일 이동평균선</span>
      </label>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showMA20}
          onChange={(e) => setShowMA20(e.target.checked)}
          className="w-4 h-4 cursor-pointer"
        />
        <span className="inline-block w-8 h-1" style={{ backgroundColor: COLORS.MA_20 }}></span>
        <span className="text-gray-700 dark:text-gray-300" style={{ color: COLORS.MA_20 }}>20일 이동평균선</span>
      </label>
    </div>
  )
}

/**
 * CustomTooltip 컴포넌트
 * 가격 차트의 툴팁을 커스터마이징
 */
const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  const data = payload[0].payload

  return (
    <div className="bg-white dark:bg-gray-800 p-3 border border-gray-300 dark:border-gray-700 rounded-lg shadow-lg transition-colors">
      <p className="text-sm font-semibold mb-2 text-gray-900 dark:text-gray-100">
        {data.date ? format(new Date(data.date), 'yyyy-MM-dd') : '-'}
      </p>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-gray-600 dark:text-gray-400">종가:</span>
          <span className="font-bold text-black dark:text-gray-100">{formatPrice(data.close_price)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-600 dark:text-gray-400">시가:</span>
          <span className="font-semibold text-green-600 dark:text-green-400">{formatPrice(data.open_price)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-600 dark:text-gray-400">고가:</span>
          <span className="font-semibold text-red-600 dark:text-red-400">{formatPrice(data.high_price)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-600 dark:text-gray-400">저가:</span>
          <span className="font-semibold text-blue-600 dark:text-blue-400">{formatPrice(data.low_price)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-600 dark:text-gray-400">거래량:</span>
          <span className="font-semibold text-gray-900 dark:text-gray-100">{formatVolume(data.volume)}</span>
        </div>
        {data.daily_change_pct !== undefined && data.daily_change_pct !== null && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">등락률:</span>
            <span
              className="font-semibold"
              style={{ color: getPriceChangeColorHex(data.daily_change_pct) }}
            >
              {data.daily_change_pct > 0 ? '+' : ''}
              {data.daily_change_pct.toFixed(2)}%
            </span>
          </div>
        )}
        {/* 이동평균선 정보 */}
        {(data.ma5 || data.ma10 || data.ma20) && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-1 mt-1">
            {data.ma5 && (
              <div className="flex justify-between gap-4">
                <span className="text-purple-600 dark:text-purple-400">MA5:</span>
                <span className="font-semibold text-purple-600 dark:text-purple-400">{formatPrice(data.ma5)}</span>
              </div>
            )}
            {data.ma10 && (
              <div className="flex justify-between gap-4">
                <span className="text-green-600 dark:text-green-400">MA10:</span>
                <span className="font-semibold text-green-600 dark:text-green-400">{formatPrice(data.ma10)}</span>
              </div>
            )}
            {data.ma20 && (
              <div className="flex justify-between gap-4">
                <span className="text-red-600 dark:text-red-400">MA20:</span>
                <span className="font-semibold text-red-600 dark:text-red-400">{formatPrice(data.ma20)}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * PriceChart 컴포넌트
 * 종목의 가격 변동을 시각화하는 LineChart + BarChart 조합
 *
 * @param {Array} data - 가격 데이터 배열
 * @param {string} ticker - 종목 코드
 * @param {number} height - 차트 높이 (기본값: null, null이면 반응형)
 * @param {string} dateRange - 조회 기간 ('7d', '1m', '3m', 'custom')
 * @param {React.RefObject} scrollRef - 스크롤 컨테이너 ref (차트 동기화용)
 * @param {Function} onScroll - 스크롤 이벤트 핸들러 (차트 동기화용)
 */
const PriceChart = memo(function PriceChart({ data = [], ticker, height = null, dateRange = '7d', scrollRef, onScroll }) {
  // 이동평균선 표시 상태
  const [showMA5, setShowMA5] = useState(false)
  const [showMA10, setShowMA10] = useState(false)
  const [showMA20, setShowMA20] = useState(false)

  // 컨테이너 너비 측정
  const { containerRef, width: containerWidth } = useContainerWidth()

  // 반응형 차트 높이
  const { chartHeight: responsiveHeight } = useWindowSize()
  const finalHeight = height || responsiveHeight

  // 데이터 전처리 및 메모이제이션
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    // 데이터 검증
    const validation = validateChartData(data, ['date', 'close_price', 'volume'])
    if (!validation.isValid) {
      return []
    }

    // 주말 데이터 제외 (토요일=6, 일요일=0)
    const filteredData = data.filter(p => {
      const dayOfWeek = new Date(p.date).getDay()
      return dayOfWeek !== 0 && dayOfWeek !== 6
    })

    // 날짜 오름차순 정렬 (오래된 날짜 → 최신 날짜)
    const sortedData = filteredData.sort((a, b) => new Date(a.date) - new Date(b.date))

    // 대용량 데이터 샘플링 (MAX_CHART_POINTS개 이상일 경우)
    const sampledData = sampleData(sortedData, MAX_CHART_POINTS)

    // 이동평균선 계산 함수 (샘플링된 데이터 기준)
    const calculateMA = (period) => {
      return sampledData.map((item, index) => {
        if (index < period - 1) return null
        const sum = sampledData
          .slice(index - period + 1, index + 1)
          .reduce((acc, p) => acc + p.close_price, 0)
        return sum / period
      })
    }

    // 5일, 10일, 20일 이동평균선 계산
    const ma5 = calculateMA(5)
    const ma10 = calculateMA(10)
    const ma20 = calculateMA(20)

    return sampledData.map((item, index) => {
      // 상승(종가 > 시가): 빨간색, 하락(종가 <= 시가): 파란색
      const isRising = item.close_price > item.open_price
      const volumeColor = isRising ? COLORS.VOLUME_UP : COLORS.VOLUME_DOWN

      return {
        ...item,
        // 거래량 색상 결정을 위한 필드
        volumeColor,
        // 이동평균선 추가
        ma5: ma5[index],
        ma10: ma10[index],
        ma20: ma20[index],
      }
    })
  }, [data])

  // 데이터 없음 상태 처리
  if (!chartData || chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-50 dark:bg-gray-800 rounded-lg transition-colors"
        style={{ height: `${finalHeight}px` }}
        role="img"
        aria-label="가격 차트 - 데이터 없음"
      >
        <p className="text-gray-500 dark:text-gray-400">표시할 가격 데이터가 없습니다.</p>
      </div>
    )
  }

  // Y축 도메인 계산 (가격)
  const prices = chartData.flatMap((d) => [
    d.open_price,
    d.high_price,
    d.low_price,
    d.close_price,
  ])
  const minPrice = Math.min(...prices.filter((p) => p != null))
  const maxPrice = Math.max(...prices.filter((p) => p != null))
  const priceMargin = (maxPrice - minPrice) * 0.1
  const priceDomain = [
    Math.floor(minPrice - priceMargin),
    Math.ceil(maxPrice + priceMargin),
  ]

  // Y축 도메인 계산 (거래량)
  const volumes = chartData.map((d) => d.volume).filter((v) => v != null)
  const maxVolume = Math.max(...volumes)
  const volumeDomain = [0, Math.ceil(maxVolume * 1.2)]

  // X축 틱 포맷팅
  const formatXAxis = (tickItem) => {
    try {
      return format(new Date(tickItem), 'MM/dd')
    } catch {
      return tickItem
    }
  }

  // Y축 틱 포맷팅 (가격)
  const formatYAxisPrice = (value) => {
    return formatPrice(value)
  }

  // Y축 틱 포맷팅 (거래량)
  const formatYAxisVolume = (value) => {
    return formatVolume(value)
  }

  const is7Days = dateRange === '7d' && chartData.length <= 7
  const dataCount = chartData.length

  // 동적 막대 두께 및 차트 너비 계산
  const { barSize, chartPixelWidth, shouldShowScroll, barCategoryGap } = useMemo(() => {
    const minDataSpacing = 30
    
    if (is7Days && dataCount > 0) {
      const width = containerWidth > 0 ? containerWidth : (typeof window !== 'undefined' ? window.innerWidth - 200 : 800)
      
      const margin = 80
      const availableWidth = width - margin
      const calculatedBarSize = Math.max(30, Math.floor((availableWidth / dataCount) * 0.6))
      const calculatedGap = Math.max(2, Math.floor((availableWidth / dataCount) * 0.15))
      
      return {
        barSize: calculatedBarSize,
        chartPixelWidth: width,
        barCategoryGap: `${calculatedGap}px`,
        shouldShowScroll: false
      }
    } else {
      return {
        barSize: undefined, // Recharts 기본값 사용
        chartPixelWidth: Math.max(800, dataCount * minDataSpacing),
        barCategoryGap: dataCount > 30 ? "1%" : dataCount > 15 ? "2%" : "5%",
        shouldShowScroll: true
      }
    }
  }, [is7Days, containerWidth, dataCount])

  return (
    <div
      ref={(node) => {
        containerRef.current = node
        if (scrollRef) {
          scrollRef.current = node
        }
      }}
      className={`w-full ${shouldShowScroll ? 'overflow-x-auto' : ''}`}
      onScroll={onScroll}
      role="img"
      aria-label={`${ticker} 가격 차트`}
    >
      <div style={{ width: `${chartPixelWidth}px`, minWidth: '100%' }}>
        <ResponsiveContainer width="100%" height={finalHeight}>
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 15, left: 15, bottom: chartData.length > 15 ? 60 : 0 }}
            barCategoryGap={barCategoryGap}
          >
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.CHART_GRID} />
          <XAxis
            dataKey="date"
            tickFormatter={formatXAxis}
            tick={{ fontSize: 12 }}
            stroke={COLORS.CHART_AXIS}
          />
          <YAxis
            yAxisId="left"
            orientation="left"
            tickFormatter={formatYAxisPrice}
            tick={{ fontSize: 12 }}
            stroke={COLORS.CHART_AXIS}
            domain={priceDomain}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tickFormatter={formatYAxisVolume}
            tick={false}
            axisLine={false}
            domain={volumeDomain}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ stroke: COLORS.CHART_CURSOR, strokeWidth: 1, strokeDasharray: '5 5' }}
            isAnimationActive={false}
            wrapperStyle={{ outline: 'none' }}
            contentStyle={{ 
              backgroundColor: 'transparent', 
              border: 'none', 
              padding: 0,
              boxShadow: 'none'
            }}
          />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
            content={(props) => (
              <CustomLegend
                {...props}
                showMA5={showMA5}
                setShowMA5={setShowMA5}
                showMA10={showMA10}
                setShowMA10={setShowMA10}
                showMA20={showMA20}
                setShowMA20={setShowMA20}
              />
            )}
          />

          {/* 거래량 Bar - 상승은 빨간색, 하락은 파란색 */}
          <Bar
            yAxisId="right"
            dataKey="volume"
            opacity={0.4}
            name="거래량(막대)"
            barSize={is7Days ? barSize : undefined}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.volumeColor} />
            ))}
          </Bar>

          {/* 가격 Lines */}
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="close_price"
            stroke={COLORS.CHART_PRIMARY}
            strokeWidth={2}
            dot={false}
            name="종가"
            activeDot={{ r: 4 }}
          />

          {/* 이동평균선 - 체크박스 선택 시에만 표시 */}
          {showMA5 && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="ma5"
              stroke={COLORS.MA_5}
              strokeWidth={1.5}
              dot={false}
              name="5일 이동평균선"
              connectNulls={false}
            />
          )}
          {showMA10 && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="ma10"
              stroke={COLORS.MA_10}
              strokeWidth={1.5}
              dot={false}
              name="10일 이동평균선"
              connectNulls={false}
            />
          )}
          {showMA20 && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="ma20"
              stroke={COLORS.MA_20}
              strokeWidth={1.5}
              dot={false}
              name="20일 이동평균선"
              connectNulls={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      </div>
    </div>
  )
})

PriceChart.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      date: PropTypes.string.isRequired,
      open_price: PropTypes.number.isRequired,
      high_price: PropTypes.number.isRequired,
      low_price: PropTypes.number.isRequired,
      close_price: PropTypes.number.isRequired,
      volume: PropTypes.number.isRequired,
      daily_change_pct: PropTypes.number,
    })
  ),
  ticker: PropTypes.string.isRequired,
  height: PropTypes.number,
  dateRange: PropTypes.oneOf(['7d', '1m', '3m', 'custom']),
  scrollRef: PropTypes.object,
  onScroll: PropTypes.func,
}

export default PriceChart
