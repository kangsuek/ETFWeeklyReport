/**
 * 기술지표 계산 유틸리티
 *
 * 입력: { date, close_price }[] (날짜 오름차순)
 */

/**
 * 지수이동평균(EMA) 계산
 * @param {number[]} data - 가격 배열
 * @param {number} period - 기간
 * @returns {number[]} EMA 배열 (입력과 동일 길이, 앞부분은 null)
 */
export function calculateEMA(data, period) {
  const ema = new Array(data.length).fill(null)
  if (data.length < period) return ema

  // 첫 EMA = SMA
  let sum = 0
  for (let i = 0; i < period; i++) {
    sum += data[i]
  }
  ema[period - 1] = sum / period

  const multiplier = 2 / (period + 1)
  for (let i = period; i < data.length; i++) {
    ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1]
  }

  return ema
}

/**
 * RSI 계산 (Wilder's smoothing)
 * @param {Array<{date: string, close_price: number}>} priceData - 오름차순
 * @param {number} period - 기간 (기본 14)
 * @returns {Array<{date: string, rsi: number|null}>}
 */
export function calculateRSI(priceData, period = 14) {
  if (!priceData || priceData.length < period + 1) return []

  const result = []
  const gains = []
  const losses = []

  // 일간 변화량 계산
  for (let i = 1; i < priceData.length; i++) {
    const change = priceData[i].close_price - priceData[i - 1].close_price
    gains.push(change > 0 ? change : 0)
    losses.push(change < 0 ? Math.abs(change) : 0)
  }

  // 첫 평균 이득/손실 (SMA)
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period

  // period까지는 null
  for (let i = 0; i < period; i++) {
    result.push({ date: priceData[i].date, rsi: null })
  }

  // 첫 RSI
  const firstRS = avgLoss === 0 ? 100 : avgGain / avgLoss
  result.push({
    date: priceData[period].date,
    rsi: 100 - 100 / (1 + firstRS),
  })

  // Wilder's smoothing으로 이후 RSI 계산
  for (let i = period; i < gains.length; i++) {
    avgGain = (avgGain * (period - 1) + gains[i]) / period
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period

    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
    result.push({
      date: priceData[i + 1].date,
      rsi: 100 - 100 / (1 + rs),
    })
  }

  return result
}

/**
 * MACD 계산
 * @param {Array<{date: string, close_price: number}>} priceData - 오름차순
 * @param {number} fastPeriod - 단기 EMA (기본 12)
 * @param {number} slowPeriod - 장기 EMA (기본 26)
 * @param {number} signalPeriod - 시그널 EMA (기본 9)
 * @returns {Array<{date: string, macd: number|null, signal: number|null, histogram: number|null}>}
 */
export function calculateMACD(priceData, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) {
  if (!priceData || priceData.length < slowPeriod + signalPeriod) return []

  const prices = priceData.map(d => d.close_price)
  const fastEMA = calculateEMA(prices, fastPeriod)
  const slowEMA = calculateEMA(prices, slowPeriod)

  // MACD line = fast EMA - slow EMA
  const macdLine = prices.map((_, i) => {
    if (fastEMA[i] === null || slowEMA[i] === null) return null
    return fastEMA[i] - slowEMA[i]
  })

  // Signal line = EMA of MACD line
  const validMacd = macdLine.filter(v => v !== null)
  const signalEMA = calculateEMA(validMacd, signalPeriod)

  // 결과 매핑
  const result = []
  let validIndex = 0

  for (let i = 0; i < priceData.length; i++) {
    if (macdLine[i] === null) {
      result.push({ date: priceData[i].date, macd: null, signal: null, histogram: null })
    } else {
      const signal = signalEMA[validIndex]
      const histogram = signal !== null ? macdLine[i] - signal : null
      result.push({
        date: priceData[i].date,
        macd: macdLine[i],
        signal,
        histogram,
      })
      validIndex++
    }
  }

  return result
}

/**
 * RSI 기반 인사이트 텍스트 생성
 * @param {number} currentRSI
 * @returns {{type: string, text: string}|null}
 */
export function generateRSIInsight(currentRSI) {
  if (currentRSI == null) return null

  if (currentRSI >= 70) {
    return {
      type: 'warning',
      category: 'technical',
      priority: 1,
      text: `RSI ${currentRSI.toFixed(1)} - 과매수 구간 (매도 시그널)`,
    }
  }
  if (currentRSI <= 30) {
    return {
      type: 'positive',
      category: 'technical',
      priority: 1,
      text: `RSI ${currentRSI.toFixed(1)} - 과매도 구간 (매수 시그널)`,
    }
  }
  return null
}

/**
 * MACD 기반 인사이트 텍스트 생성
 * @param {Array} macdData - MACD 데이터 배열
 * @returns {{type: string, text: string}|null}
 */
export function generateMACDInsight(macdData) {
  if (!macdData || macdData.length < 2) return null

  const validData = macdData.filter(d => d.macd !== null && d.signal !== null)
  if (validData.length < 2) return null

  const last = validData[validData.length - 1]
  const prev = validData[validData.length - 2]

  // 골든크로스: MACD가 Signal을 상향 돌파
  if (prev.macd <= prev.signal && last.macd > last.signal) {
    return {
      type: 'positive',
      category: 'technical',
      priority: 1,
      text: 'MACD 골든크로스 발생 (상승 전환 시그널)',
    }
  }

  // 데드크로스: MACD가 Signal을 하향 돌파
  if (prev.macd >= prev.signal && last.macd < last.signal) {
    return {
      type: 'warning',
      category: 'technical',
      priority: 1,
      text: 'MACD 데드크로스 발생 (하락 전환 시그널)',
    }
  }

  return null
}
