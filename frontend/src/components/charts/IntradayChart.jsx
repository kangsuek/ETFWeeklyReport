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
  ReferenceLine,
} from 'recharts'
import { formatPrice, formatVolume, getPriceChangeColorHex } from '../../utils/format'
import { useContainerWidth } from '../../hooks/useContainerWidth'
import { COLORS } from '../../constants'

/**
 * CustomTooltip 컴포넌트 - 분봉 차트 전용 툴팁
 */
const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) {
    return null
  }

  const data = payload[0].payload

  // datetime에서 시간만 추출
  const time = data.datetime ? data.datetime.split('T')[1]?.substring(0, 5) : '-'

  return (
    <div className="bg-white dark:bg-gray-800 p-3 border border-gray-300 dark:border-gray-700 rounded-lg shadow-lg transition-colors">
      <p className="text-sm font-semibold mb-2 text-gray-900 dark:text-gray-100">
        {time}
      </p>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-gray-600 dark:text-gray-400">체결가:</span>
          <span className="font-bold text-black dark:text-gray-100">{formatPrice(data.price)}</span>
        </div>
        {data.change_amount !== null && data.change_amount !== undefined && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">전일비:</span>
            <span
              className="font-semibold"
              style={{ color: getPriceChangeColorHex(data.change_amount) }}
            >
              {data.change_amount > 0 ? '+' : ''}
              {formatPrice(data.change_amount)}
            </span>
          </div>
        )}
        {data.volume && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">거래량:</span>
            <span className="font-semibold text-gray-900 dark:text-gray-100">
              {formatVolume(data.volume)}
            </span>
          </div>
        )}
        {data.bid_volume && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">매수잔량:</span>
            <span className="font-semibold text-red-600 dark:text-red-400">
              {formatVolume(data.bid_volume)}
            </span>
          </div>
        )}
        {data.ask_volume && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-600 dark:text-gray-400">매도잔량:</span>
            <span className="font-semibold text-blue-600 dark:text-blue-400">
              {formatVolume(data.ask_volume)}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * IntradayChart 컴포넌트
 * 분봉(시간별 체결) 데이터를 시각화하는 차트
 *
 * @param {Array} data - 분봉 데이터 배열
 * @param {string} ticker - 종목 코드
 * @param {number} height - 차트 높이 (기본값: 300)
 * @param {boolean} showVolume - 거래량 표시 여부
 * @param {number} previousClose - 전일 종가 (기준선 표시용)
 */
const IntradayChart = memo(function IntradayChart({
  data = [],
  ticker,
  height = 300,
  showVolume = true,
  previousClose = null
}) {
  // 컨테이너 너비 측정
  const { containerRef, width: containerWidth } = useContainerWidth()

  // 데이터 전처리 및 메모이제이션
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    // 시간순 정렬 확인 (이미 정렬되어 있어야 함)
    const sortedData = [...data].sort((a, b) => {
      const timeA = new Date(a.datetime).getTime()
      const timeB = new Date(b.datetime).getTime()
      return timeA - timeB
    })

    return sortedData.map((item) => {
      // 상승/하락 색상 결정
      const isRising = item.change_amount > 0
      const volumeColor = isRising ? COLORS.VOLUME_UP : COLORS.VOLUME_DOWN

      // datetime에서 시간만 추출 (HH:MM 형식)
      const time = item.datetime.split('T')[1]?.substring(0, 5) || item.datetime

      return {
        ...item,
        time,
        volumeColor,
      }
    })
  }, [data])

  // 데이터 없음 상태 처리
  if (!chartData || chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-50 dark:bg-gray-800 rounded-lg transition-colors"
        style={{ height: `${height}px` }}
        role="img"
        aria-label="분봉 차트 - 데이터 없음"
      >
        <div className="text-center">
          <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-gray-500 dark:text-gray-400">분봉 데이터가 없습니다.</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            장중이 아니거나 휴장일입니다.
          </p>
        </div>
      </div>
    )
  }

  // Y축 도메인 계산 (가격)
  const prices = chartData.map((d) => d.price).filter((p) => p != null)
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const priceMargin = (maxPrice - minPrice) * 0.05 || maxPrice * 0.01
  const priceDomain = [
    Math.floor(minPrice - priceMargin),
    Math.ceil(maxPrice + priceMargin),
  ]

  // Y축 도메인 계산 (거래량)
  const volumes = chartData.map((d) => d.volume).filter((v) => v != null)
  const maxVolume = Math.max(...volumes) || 0
  const volumeDomain = [0, Math.ceil(maxVolume * 1.2)]

  // X축 틱 포맷팅 (시간만 표시)
  const formatXAxis = (tickItem) => {
    return tickItem
  }

  // X축 틱 간격 계산 (약 6-8개 틱)
  const tickInterval = Math.floor(chartData.length / 7)

  return (
    <div
      ref={containerRef}
      className="w-full"
      role="img"
      aria-label={`${ticker} 분봉 차트`}
    >
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={chartData}
          margin={{ top: 10, right: 15, left: 15, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.CHART_GRID} />
          <XAxis
            dataKey="time"
            tickFormatter={formatXAxis}
            tick={{ fontSize: 11 }}
            stroke={COLORS.CHART_AXIS}
            interval={tickInterval}
            angle={-45}
            textAnchor="end"
            height={50}
          />
          <YAxis
            yAxisId="left"
            orientation="left"
            tickFormatter={formatPrice}
            tick={{ fontSize: 11 }}
            stroke={COLORS.CHART_AXIS}
            domain={priceDomain}
            width={70}
          />
          {showVolume && (
            <YAxis
              yAxisId="right"
              orientation="right"
              tickFormatter={formatVolume}
              tick={false}
              axisLine={false}
              domain={volumeDomain}
            />
          )}
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
            wrapperStyle={{ paddingTop: '10px' }}
            iconType="line"
          />

          {/* 거래량 Bar */}
          {showVolume && (
            <Bar
              yAxisId="right"
              dataKey="volume"
              opacity={0.3}
              name="거래량"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.volumeColor} />
              ))}
            </Bar>
          )}

          {/* 가격 Line */}
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="price"
            stroke={COLORS.CHART_PRIMARY}
            strokeWidth={1.5}
            dot={false}
            name="체결가"
            activeDot={{ r: 3 }}
          />

          {/* 전일 종가 기준선 */}
          {previousClose && (
            <ReferenceLine
              yAxisId="left"
              y={previousClose}
              stroke="#9ca3af"
              strokeDasharray="5 5"
              strokeWidth={1}
              label={{
                value: `전일 ${formatPrice(previousClose)}`,
                position: 'insideTopRight',
                fill: '#9ca3af',
                fontSize: 10,
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
})

IntradayChart.propTypes = {
  data: PropTypes.arrayOf(
    PropTypes.shape({
      datetime: PropTypes.string.isRequired,
      price: PropTypes.number.isRequired,
      change_amount: PropTypes.number,
      volume: PropTypes.number,
      bid_volume: PropTypes.number,
      ask_volume: PropTypes.number,
    })
  ),
  ticker: PropTypes.string.isRequired,
  height: PropTypes.number,
  showVolume: PropTypes.bool,
  previousClose: PropTypes.number,
}

export default IntradayChart
