/**
 * 수익률 계산 유틸리티
 *
 * 백엔드 ComparisonService와 동일한 로직 사용
 * - 거래일 기준 계산 (데이터 포인트 개수)
 * - 복리 효과 반영
 */

/**
 * 기간 수익률 계산
 *
 * @param {Array} data - 가격 데이터 배열 (최신순 정렬)
 * @returns {number} 기간 수익률 (%)
 */
export function calculatePeriodReturn(data) {
  if (!data || data.length < 2) {
    return 0
  }

  // API는 데이터를 내림차순(최신 날짜가 먼저)으로 반환
  // data[0] = 최신 날짜, data[data.length - 1] = 가장 오래된 날짜
  const firstPrice = data[data.length - 1].close_price  // 시작 가격
  const lastPrice = data[0].close_price  // 종료 가격

  if (firstPrice === 0) {
    return 0
  }

  return ((lastPrice - firstPrice) / firstPrice) * 100
}

/**
 * 연환산 수익률 계산 (복리 효과 반영)
 *
 * 공식: ((1 + 기간수익률) ^ (365/거래일수) - 1) * 100
 *
 * 주의: 거래일 기준으로 계산 (달력 일수 아님)
 * - 거래일수 = 데이터 포인트 개수
 * - 주말, 공휴일 제외
 *
 * @param {Array} data - 가격 데이터 배열 (최신순 정렬)
 * @returns {number} 연환산 수익률 (%)
 */
export function calculateAnnualizedReturn(data) {
  if (!data || data.length < 2) {
    return 0
  }

  // 거래일수 = 데이터 포인트 개수
  // (백엔드 ComparisonService와 동일한 로직)
  const tradingDays = data.length

  if (tradingDays === 0) {
    return 0
  }

  // 기간 수익률 (소수)
  const firstPrice = data[data.length - 1].close_price
  const lastPrice = data[0].close_price

  if (firstPrice === 0) {
    return 0
  }

  const periodReturn = (lastPrice - firstPrice) / firstPrice

  // 연환산: (1 + 기간수익률) ^ (365/거래일수) - 1
  // 복리 효과를 반영한 정확한 연환산 계산
  const annualized = (Math.pow(1 + periodReturn, 365 / tradingDays) - 1) * 100

  return annualized
}

/**
 * 통계 계산
 *
 * @param {Array} data - 가격 데이터 배열 (최신순 정렬)
 * @returns {Object} 통계 객체
 */
export function calculateStats(data) {
  if (!data || data.length < 2) {
    return null
  }

  // 수익률 계산
  const periodReturn = calculatePeriodReturn(data)
  const annualizedReturn = calculateAnnualizedReturn(data)

  // 가격 범위 (날짜 포함)
  const prices = data.map((d) => d.close_price)
  const highPrice = Math.max(...prices)
  const lowPrice = Math.min(...prices)
  const avgPrice = prices.reduce((sum, p) => sum + p, 0) / prices.length

  // 최고가/최저가 날짜 찾기
  const highPriceData = data.find((d) => d.close_price === highPrice)
  const lowPriceData = data.find((d) => d.close_price === lowPrice)

  // 현재가 (가장 최신 종가)
  const currentPrice = data[0]?.close_price || 0
  const currentPriceDate = data[0]?.date

  return {
    periodReturn,
    annualizedReturn,
    highPrice,
    lowPrice,
    avgPrice,
    currentPrice,
    currentPriceDate,
    highPriceDate: highPriceData?.date,
    lowPriceDate: lowPriceData?.date,
    tradingDays: data.length,
  }
}
