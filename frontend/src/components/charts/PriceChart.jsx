import { useMemo, memo } from 'react'
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
} from 'recharts'
import { format } from 'date-fns'
import { formatPrice, formatVolume, getPriceChangeColorHex } from '../../utils/format'

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
    <div className="bg-white p-3 border border-gray-300 rounded-lg shadow-lg">
      <p className="text-sm font-semibold mb-2">
        {data.date ? format(new Date(data.date), 'yyyy-MM-dd') : '-'}
      </p>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-gray-600">시가:</span>
          <span className="font-semibold">{formatPrice(data.open_price)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-600">고가:</span>
          <span className="font-semibold">{formatPrice(data.high_price)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-600">저가:</span>
          <span className="font-semibold">{formatPrice(data.low_price)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-600">종가:</span>
          <span className="font-semibold text-primary-600">{formatPrice(data.close_price)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-600">거래량:</span>
          <span className="font-semibold">{formatVolume(data.volume)}</span>
        </div>
        {data.daily_change_pct !== undefined && data.daily_change_pct !== null && (
          <div className="flex justify-between gap-4">
            <span className="text-gray-600">등락률:</span>
            <span
              className="font-semibold"
              style={{ color: getPriceChangeColorHex(data.daily_change_pct) }}
            >
              {data.daily_change_pct > 0 ? '+' : ''}
              {data.daily_change_pct.toFixed(2)}%
            </span>
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
 * @param {number} height - 차트 높이 (기본값: 400)
 */
const PriceChart = memo(function PriceChart({ data = [], ticker, height = 400 }) {
  // 데이터 전처리 및 메모이제이션
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    return data.map((item) => ({
      ...item,
      // 거래량 색상 결정을 위한 필드
      volumeColor: getPriceChangeColorHex(item.daily_change_pct),
    }))
  }, [data])

  // 데이터 없음 상태 처리
  if (!chartData || chartData.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-gray-50 rounded-lg"
        style={{ height: `${height}px` }}
      >
        <p className="text-gray-500">표시할 가격 데이터가 없습니다.</p>
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

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tickFormatter={formatXAxis}
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
          />
          <YAxis
            yAxisId="left"
            orientation="left"
            tickFormatter={formatYAxisPrice}
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
            domain={priceDomain}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tickFormatter={formatYAxisVolume}
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
            domain={volumeDomain}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="line"
          />

          {/* 거래량 Bar */}
          <Bar
            yAxisId="right"
            dataKey="volume"
            fill="#9ca3af"
            opacity={0.3}
            name="거래량"
          />

          {/* 가격 Lines */}
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="close_price"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
            name="종가"
            activeDot={{ r: 4 }}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="open_price"
            stroke="#10b981"
            strokeWidth={1}
            strokeOpacity={0.5}
            dot={false}
            name="시가"
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="high_price"
            stroke="#f59e0b"
            strokeWidth={1}
            strokeOpacity={0.5}
            dot={false}
            name="고가"
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="low_price"
            stroke="#ef4444"
            strokeWidth={1}
            strokeOpacity={0.5}
            dot={false}
            name="저가"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
})

export default PriceChart
