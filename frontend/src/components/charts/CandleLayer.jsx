import PropTypes from 'prop-types'
import { COLORS } from '../../constants'

/**
 * CandleLayer 컴포넌트 (공용)
 *
 * Recharts <Customized>로 캔들(봉)을 직접 그린다.
 * 거래량 Bar와 그룹핑되어 어긋나는 문제를 피하려고 축 스케일을 이용해 SVG로 직접 렌더링한다.
 * 한국식 색상: 상승(종가 >= 시가) 빨강, 하락 파랑.
 *
 * 일봉(PriceChart: date/close_price)과 분봉(IntradayChart: time/price) 모두에서
 * 쓸 수 있도록 x축·OHLC 필드 키를 파라미터로 받는다.
 */
function CandleLayer({
  xAxisMap,
  yAxisMap,
  candles,
  xKey = 'date',
  openKey = 'open_price',
  highKey = 'high_price',
  lowKey = 'low_price',
  closeKey = 'close_price',
}) {
  if (!xAxisMap || !yAxisMap || !candles || candles.length === 0) return null

  const xAxis = Object.values(xAxisMap)[0]
  // 가격 축(왼쪽) 선택 (거래량은 오른쪽 축이므로 제외)
  const yAxis =
    yAxisMap.left ||
    Object.values(yAxisMap).find((a) => a.orientation === 'left') ||
    Object.values(yAxisMap)[0]

  const xScale = xAxis?.scale
  const yScale = yAxis?.scale
  if (!xScale || !yScale) return null

  const band = typeof xScale.bandwidth === 'function' ? xScale.bandwidth() : 12
  const bodyW = Math.max(2, band * 0.6)

  return (
    <g>
      {candles.map((d, i) => {
        const o = d[openKey]
        const c = d[closeKey]
        const h = d[highKey]
        const l = d[lowKey]
        if (o == null || c == null || h == null || l == null) return null

        const baseX = xScale(d[xKey])
        if (baseX == null || Number.isNaN(baseX)) return null

        const cx = baseX + band / 2
        const yHigh = yScale(h)
        const yLow = yScale(l)
        const yOpen = yScale(o)
        const yClose = yScale(c)

        const rising = c >= o
        const color = rising ? COLORS.VOLUME_UP : COLORS.VOLUME_DOWN
        const bodyTop = Math.min(yOpen, yClose)
        const bodyHeight = Math.max(1, Math.abs(yClose - yOpen))

        return (
          <g key={`candle-${i}`}>
            {/* 꼬리(고가~저가) */}
            <line x1={cx} y1={yHigh} x2={cx} y2={yLow} stroke={color} strokeWidth={1} />
            {/* 몸통(시가~종가) */}
            <rect
              x={cx - bodyW / 2}
              y={bodyTop}
              width={bodyW}
              height={bodyHeight}
              fill={color}
              stroke={color}
            />
          </g>
        )
      })}
    </g>
  )
}

CandleLayer.propTypes = {
  xAxisMap: PropTypes.object,
  yAxisMap: PropTypes.object,
  candles: PropTypes.array,
  xKey: PropTypes.string,
  openKey: PropTypes.string,
  highKey: PropTypes.string,
  lowKey: PropTypes.string,
  closeKey: PropTypes.string,
}

export default CandleLayer
