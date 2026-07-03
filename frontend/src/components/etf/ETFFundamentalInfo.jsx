import { useMemo } from 'react'
import PropTypes from 'prop-types'
import { formatNumber, formatPercent, getPriceChangeColor } from '../../utils/format'

/**
 * ETFFundamentalInfo 컴포넌트
 * ETFDetail 섹션 3.6 — ETF 정보 (NAV·총보수·구성종목, ETF 타입 전용)
 * 펀더멘털 원본(fundamentalsData)에서 파생값·자동 해석 문장까지 이 컴포넌트가 계산·표시한다.
 */

// ETF 섹터 배분 코드 → 한글 라벨
const SECTOR_KO = {
  INDUSTRIALS: '산업재', IT: '정보기술', UTILITIES: '유틸리티', FINANCIALS: '금융',
  HEALTHCARE: '헬스케어', HEALTH_CARE: '헬스케어', CONSUMER_DISCRETIONARY: '경기소비재',
  CONSUMER_STAPLES: '필수소비재', ENERGY: '에너지', MATERIALS: '소재',
  COMMUNICATION_SERVICES: '커뮤니케이션', COMMUNICATION: '커뮤니케이션',
  REAL_ESTATE: '부동산', EQUITY: '주식', BOND: '채권', CASH: '현금', ETC: '기타',
  UNCLASSIFIED: '미분류',
}

/**
 * AUM(억원)을 조·억 단위로 포맷
 */
function formatAum(eok) {
  if (eok == null) return '-'
  if (eok >= 10000) {
    const jo = Math.floor(eok / 10000)
    const rem = Math.round(eok % 10000)
    return rem > 0 ? `${jo}조 ${rem.toLocaleString('ko-KR')}억` : `${jo}조`
  }
  return `${eok.toLocaleString('ko-KR')}억`
}

/**
 * ETF 펀더멘털을 읽어 평이한 해석 문장 배열 생성
 * tone: good(긍정)·neutral(중립)·warn(주의)·bad(위험)
 */
function buildEtfInsights(f, deviation, topSector) {
  const items = []
  const pct = (v) => `${v > 0 ? '+' : ''}${Number(v).toFixed(2)}%`

  if (deviation != null) {
    const a = Math.abs(deviation)
    if (a <= 0.5) {
      items.push({ tone: 'good', text: `괴리율 ${pct(deviation)} — 시장가가 NAV와 거의 일치해 정상적으로 거래되고 있어요.` })
    } else if (a <= 1.5) {
      const dir = deviation > 0 ? '다소 비싸게(프리미엄)' : '다소 싸게(할인)'
      items.push({ tone: 'warn', text: `괴리율 ${pct(deviation)} — 시장가가 NAV보다 ${dir} 거래 중이에요.` })
    } else {
      items.push({ tone: 'bad', text: `괴리율 ${pct(deviation)} — 괴리가 큽니다. 매매 시 불리한 체결·유동성에 유의하세요.` })
    }
  }

  if (f.expense_ratio != null) {
    if (f.expense_ratio <= 0.2) items.push({ tone: 'good', text: `총보수 ${f.expense_ratio}% — 낮은 편이라 장기 보유에 유리해요.` })
    else if (f.expense_ratio <= 0.5) items.push({ tone: 'neutral', text: `총보수 ${f.expense_ratio}% — 보통 수준이에요.` })
    else items.push({ tone: 'warn', text: `총보수 ${f.expense_ratio}% — 다소 높아 장기 비용 부담이 있어요.` })
  }

  if (f.tracking_error != null) {
    if (f.tracking_error <= 1) items.push({ tone: 'good', text: `추적오차 ${f.tracking_error}% — 기초지수를 잘 따라가고 있어요.` })
    else if (f.tracking_error <= 3) items.push({ tone: 'neutral', text: `추적오차 ${f.tracking_error}% — 추종이 다소 벌어져요.` })
    else items.push({ tone: 'warn', text: `추적오차 ${f.tracking_error}% — 지수 추종이 부실한 편이라 주의가 필요해요.` })
  }

  if (f.aum != null) {
    if (f.aum >= 10000) items.push({ tone: 'good', text: `순자산 ${formatAum(f.aum)} — 대형 ETF로 유동성과 안정성이 좋아요.` })
    else if (f.aum >= 500) items.push({ tone: 'neutral', text: `순자산 ${formatAum(f.aum)} — 중형 규모예요.` })
    else if (f.aum >= 50) items.push({ tone: 'warn', text: `순자산 ${formatAum(f.aum)} — 소형이라 거래량이 적을 수 있어요.` })
    else items.push({ tone: 'bad', text: `순자산 ${formatAum(f.aum)} — 매우 작아 상장폐지(청산) 위험에 유의하세요.` })
  }

  if (f.dividend_yield != null) {
    if (f.dividend_yield <= 0) items.push({ tone: 'neutral', text: '분배(배당)가 거의 없는 성장형 ETF예요.' })
    else items.push({ tone: 'neutral', text: `분배율 ${f.dividend_yield}% — 배당 수익도 일부 기대할 수 있어요.` })
  }

  if (topSector && topSector.weight > 50) {
    const name = SECTOR_KO[topSector.code] || topSector.code
    items.push({ tone: 'warn', text: `${name} 비중 ${topSector.weight.toFixed(0)}% — 특정 섹터 집중도가 높아 해당 업황에 크게 좌우돼요.` })
  }

  return items
}

const TONE_STYLE = {
  good: { color: 'text-green-700 dark:text-green-400', icon: '✓' },
  neutral: { color: 'text-gray-700 dark:text-gray-300', icon: '·' },
  warn: { color: 'text-yellow-700 dark:text-yellow-400', icon: '!' },
  bad: { color: 'text-red-700 dark:text-red-300', icon: '▼' },
}

export default function ETFFundamentalInfo({ etf, fundamentalsData, latestPrice }) {
  const etfFundamental = fundamentalsData?.fundamentals?.[0] || null
  const etfHoldings = fundamentalsData?.holdings || []

  // 괴리율 = (시장가 - NAV) / NAV × 100 (양수: 고평가 거래, 음수: 저평가 거래)
  const navDisparity = useMemo(() => {
    const nav = etfFundamental?.nav
    const price = latestPrice?.close_price
    if (!nav || !price) return null
    return ((price - nav) / nav) * 100
  }, [etfFundamental?.nav, latestPrice?.close_price])

  // 섹터 배분 (JSON 파싱 → 비중 내림차순)
  const sectorPortfolio = useMemo(() => {
    if (!etfFundamental?.sector_portfolio) return []
    try {
      const arr = JSON.parse(etfFundamental.sector_portfolio)
      return arr.filter((s) => s.weight > 0).sort((a, b) => b.weight - a.weight)
    } catch {
      return []
    }
  }, [etfFundamental?.sector_portfolio])

  // 괴리율: 네이버 동시점 값(정확) 우선, 없으면 계산값 폴백
  const etfDeviation = etfFundamental?.deviation_rate != null
    ? etfFundamental.deviation_rate
    : navDisparity

  // 펀더멘털 자동 해석 문장
  const etfInsights = useMemo(
    () => (etfFundamental ? buildEtfInsights(etfFundamental, etfDeviation, sectorPortfolio[0]) : []),
    [etfFundamental, etfDeviation, sectorPortfolio],
  )

  if (etf?.type !== 'ETF' || !etfFundamental) return null

  return (
    <div className="card mb-4">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">ETF 정보</h3>
        {etfFundamental.base_index && (
          <span className="text-xs px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
            기초지수: {etfFundamental.base_index}
          </span>
        )}
        {etfFundamental.date && (
          <span className="text-xs text-gray-400 dark:text-gray-500">기준일 {etfFundamental.date}</span>
        )}
      </div>

      {/* 자동 해석: 이 ETF 한눈에 보기 */}
      {etfInsights.length > 0 && (
        <div className="rounded-lg border border-blue-100 dark:border-blue-900/50 bg-blue-50/50 dark:bg-blue-950/20 p-3 mb-4">
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">📊 이 ETF 한눈에 보기</p>
          <ul className="space-y-1">
            {etfInsights.map((it, i) => (
              <li key={i} className={`text-sm flex gap-2 ${TONE_STYLE[it.tone].color}`}>
                <span className="shrink-0 font-bold">{TONE_STYLE[it.tone].icon}</span>
                <span>{it.text}</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
            * 자동 계산된 참고용 해석이며 투자 판단의 근거가 아닙니다.
          </p>
        </div>
      )}

      {/* NAV·괴리율·총보수·AUM·분배 등 지표 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mb-4">
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
          <span className="text-xs text-gray-500 dark:text-gray-400 block">NAV (순자산가치)</span>
          <p className="text-lg font-bold mt-0.5 text-gray-900 dark:text-gray-100">
            {etfFundamental.nav != null ? formatNumber(etfFundamental.nav) : '-'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
          <span className="text-xs text-gray-500 dark:text-gray-400 block">NAV 등락률</span>
          <p className={`text-lg font-bold mt-0.5 ${getPriceChangeColor(etfFundamental.nav_change_pct)}`}>
            {etfFundamental.nav_change_pct != null ? formatPercent(etfFundamental.nav_change_pct) : '-'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
          <span className="text-xs text-gray-500 dark:text-gray-400 block">괴리율 (시장가 vs NAV)</span>
          <p className={`text-lg font-bold mt-0.5 ${getPriceChangeColor(etfDeviation)}`}>
            {etfDeviation != null ? formatPercent(etfDeviation) : '-'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
          <span className="text-xs text-gray-500 dark:text-gray-400 block">순자산총액 (AUM)</span>
          <p className="text-lg font-bold mt-0.5 text-gray-900 dark:text-gray-100">
            {formatAum(etfFundamental.aum)}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
          <span className="text-xs text-gray-500 dark:text-gray-400 block">총보수 (연)</span>
          <p className="text-lg font-bold mt-0.5 text-gray-900 dark:text-gray-100">
            {etfFundamental.expense_ratio != null ? `${etfFundamental.expense_ratio}%` : '-'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
          <span className="text-xs text-gray-500 dark:text-gray-400 block">추적오차</span>
          <p className="text-lg font-bold mt-0.5 text-gray-900 dark:text-gray-100">
            {etfFundamental.tracking_error != null ? `${etfFundamental.tracking_error}%` : '-'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
          <span className="text-xs text-gray-500 dark:text-gray-400 block">분배율 (TTM)</span>
          <p className="text-lg font-bold mt-0.5 text-gray-900 dark:text-gray-100">
            {etfFundamental.dividend_yield != null ? `${etfFundamental.dividend_yield}%` : '-'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
          <span className="text-xs text-gray-500 dark:text-gray-400 block">주당 분배금 (TTM)</span>
          <p className="text-lg font-bold mt-0.5 text-gray-900 dark:text-gray-100">
            {etfFundamental.dividend_per_share != null ? formatNumber(etfFundamental.dividend_per_share) : '-'}
          </p>
        </div>
      </div>

      {/* 섹터 배분 */}
      {sectorPortfolio.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">섹터 배분</h4>
          <div className="space-y-1.5">
            {sectorPortfolio.slice(0, 6).map((s) => (
              <div key={s.code} className="flex items-center gap-2 text-sm">
                <span className="w-24 shrink-0 text-gray-700 dark:text-gray-300">
                  {SECTOR_KO[s.code] || s.code}
                </span>
                <div className="flex-1 h-2 rounded bg-gray-100 dark:bg-gray-700 overflow-hidden">
                  <div
                    className="h-full bg-blue-500 dark:bg-blue-400"
                    style={{ width: `${Math.min(100, s.weight)}%` }}
                  />
                </div>
                <span className="w-14 shrink-0 text-right font-semibold text-gray-900 dark:text-gray-100">
                  {s.weight.toFixed(2)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 구성종목 (PDF) */}
      {etfHoldings.length > 0 ? (
        <div>
          <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
            구성종목 상위 {etfHoldings.length}
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                  <th className="py-1.5 pr-2 font-medium">#</th>
                  <th className="py-1.5 pr-2 font-medium">종목명</th>
                  <th className="py-1.5 pr-2 font-medium text-right">비중</th>
                  <th className="py-1.5 font-medium">섹터</th>
                </tr>
              </thead>
              <tbody>
                {etfHoldings.map((h, i) => (
                  <tr key={`${h.stock_code}-${i}`} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-1.5 pr-2 text-gray-400 dark:text-gray-500">{i + 1}</td>
                    <td className="py-1.5 pr-2 text-gray-900 dark:text-gray-100">{h.stock_name || h.stock_code}</td>
                    <td className="py-1.5 pr-2 text-right font-semibold text-gray-900 dark:text-gray-100">
                      {h.weight != null ? `${h.weight.toFixed(2)}%` : '-'}
                    </td>
                    <td className="py-1.5 text-gray-500 dark:text-gray-400">{h.sector || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">구성종목 데이터가 없습니다</p>
      )}
    </div>
  )
}

ETFFundamentalInfo.propTypes = {
  etf: PropTypes.object,
  fundamentalsData: PropTypes.shape({
    fundamentals: PropTypes.array,
    holdings: PropTypes.array,
  }),
  latestPrice: PropTypes.object,
}
