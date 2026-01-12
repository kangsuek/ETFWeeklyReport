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
 * @param {number} purchasePrice - 매입 가격 (선택사항)
 * @param {string} purchaseDate - 매입 날짜 (선택사항, YYYY-MM-DD 형식)
 * @returns {Object} 통계 객체
 */
export function calculateStats(data, purchasePrice = null, purchaseDate = null) {
  if (!data || data.length < 2) {
    return null
  }

  // 현재가 (가장 최신 종가)
  const currentPrice = data[0]?.close_price || 0

  // 매입가가 있으면 매입가 기준으로 수익률 계산
  let periodReturn, annualizedReturn
  if (purchasePrice && purchasePrice > 0) {
    // 매입가 기준 수익률
    periodReturn = ((currentPrice - purchasePrice) / purchasePrice) * 100

    // 연환산 수익률 계산
    // 매입일이 있으면 매입일부터 현재까지의 거래일수 사용
    // 없으면 전체 데이터 기간 사용
    let tradingDays = data.length
    
    if (purchaseDate) {
      // 매입일 이후의 데이터만 사용 (data는 최신순 정렬)
      const purchaseDateObj = new Date(purchaseDate)
      purchaseDateObj.setHours(0, 0, 0, 0) // 시간 제거하여 날짜만 비교
      
      // 매입일 이후의 데이터 필터링
      const filteredData = data.filter(d => {
        const dataDate = new Date(d.date)
        dataDate.setHours(0, 0, 0, 0)
        return dataDate >= purchaseDateObj
      })
      
      // 필터링된 데이터가 2개 이상이면 사용, 아니면 전체 기간 사용
      if (filteredData.length >= 2) {
        tradingDays = filteredData.length
      }
    }

    if (tradingDays > 0) {
      const periodReturnDecimal = (currentPrice - purchasePrice) / purchasePrice
      annualizedReturn = (Math.pow(1 + periodReturnDecimal, 365 / tradingDays) - 1) * 100
    } else {
      annualizedReturn = 0
    }
  } else {
    // 기존 방식: 기간 수익률 및 연환산 수익률
    periodReturn = calculatePeriodReturn(data)
    annualizedReturn = calculateAnnualizedReturn(data)
  }

  // 가격 범위 (날짜 포함)
  const prices = data.map((d) => d.close_price)
  const highPrice = Math.max(...prices)
  const lowPrice = Math.min(...prices)
  const avgPrice = prices.reduce((sum, p) => sum + p, 0) / prices.length

  // 최고가/최저가 날짜 찾기
  const highPriceData = data.find((d) => d.close_price === highPrice)
  const lowPriceData = data.find((d) => d.close_price === lowPrice)

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
