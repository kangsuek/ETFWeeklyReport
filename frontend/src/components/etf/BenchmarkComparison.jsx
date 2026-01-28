import { useQuery } from '@tanstack/react-query'
import PropTypes from 'prop-types'
import { etfApi } from '../../services/api'
import { formatPercent } from '../../utils/format'
import Spinner from '../common/Spinner'
import ErrorFallback from '../common/ErrorFallback'

/**
 * BenchmarkComparison 컴포넌트
 * ETF와 벤치마크 지수의 성과를 비교하여 표시
 *
 * @param {string} ticker - 종목 코드
 * @param {string} benchmark - 벤치마크 지수 (KOSPI, KOSDAQ, KOSPI200)
 * @param {string} period - 분석 기간 (1w, 1m, 3m, 6m, 1y)
 */
export default function BenchmarkComparison({ ticker, benchmark = 'KOSPI', period = '1m' }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['benchmark', ticker, benchmark, period],
    queryFn: async () => {
      const response = await etfApi.getBenchmarkComparison(ticker, benchmark, period)
      return response.data
    },
    staleTime: 1 * 60 * 1000, // 1분
  })

  if (isLoading) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          벤치마크 대비 분석
        </h3>
        <div className="flex items-center justify-center py-8">
          <Spinner />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          벤치마크 대비 분석
        </h3>
        <ErrorFallback error={error} />
      </div>
    )
  }

  // 데이터가 없으면 에러 표시
  if (!data) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          벤치마크 대비 분석
        </h3>
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <p>데이터를 불러올 수 없습니다</p>
        </div>
      </div>
    )
  }

  const { etf_return, benchmark_return, alpha, correlation, data_points, error: dataError } = data

  // ETF 수익률도 없으면 에러 표시
  if (dataError && etf_return === null && etf_return === undefined) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">
          벤치마크 대비 분석
        </h3>
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <p>{dataError}</p>
        </div>
      </div>
    )
  }

  // 수익률 색상
  const getReturnColor = (value) => {
    if (value === null || value === undefined) return 'text-gray-500 dark:text-gray-400'
    if (value > 0) return 'text-red-600 dark:text-red-400'
    if (value < 0) return 'text-blue-600 dark:text-blue-400'
    return 'text-gray-500 dark:text-gray-400'
  }

  // Alpha 색상 (초과수익률)
  const getAlphaColor = (value) => {
    if (value === null || value === undefined) return 'text-gray-500 dark:text-gray-400'
    if (value > 0) return 'text-green-600 dark:text-green-400'
    if (value < 0) return 'text-orange-600 dark:text-orange-400'
    return 'text-gray-500 dark:text-gray-400'
  }

  // 상관계수 색상
  const getCorrelationColor = (value) => {
    if (value === null || value === undefined) return 'text-gray-500 dark:text-gray-400'
    if (value > 0.7) return 'text-blue-600 dark:text-blue-400'
    if (value > 0.3) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-gray-500 dark:text-gray-400'
  }

  // 벤치마크 이름 한글 변환
  const benchmarkNames = {
    KOSPI: '코스피',
    KOSDAQ: '코스닥',
    KOSPI200: '코스피200'
  }

  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          벤치마크 대비 분석
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {benchmarkNames[benchmark] || benchmark} 대비 성과 비교
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 수익률 비교 */}
        <div className="bg-white dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">수익률 비교</h4>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 dark:text-gray-400">종목 수익률</span>
              <span className={`text-sm font-semibold ${getReturnColor(etf_return)}`}>
                {etf_return !== null && etf_return !== undefined ? formatPercent(etf_return) : 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {benchmarkNames[benchmark] || benchmark} 수익률
              </span>
              <span className={`text-sm font-semibold ${getReturnColor(benchmark_return)}`}>
                {benchmark_return !== null && benchmark_return !== undefined ? formatPercent(benchmark_return) : 'N/A'}
              </span>
            </div>
            {dataError && (
              <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-600">
                <p className="text-xs text-yellow-600 dark:text-yellow-400">
                  ⚠️ {dataError}
                </p>
              </div>
            )}
            {!dataError && alpha !== null && alpha !== undefined && (
              <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-600">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400">초과수익률 (Alpha)</span>
                  <span className={`text-sm font-semibold ${getAlphaColor(alpha)}`}>
                    {alpha > 0 ? '+' : ''}{formatPercent(alpha)}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 상관계수 */}
        <div className="bg-white dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">상관관계</h4>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 dark:text-gray-400">상관계수</span>
              <span className={`text-sm font-semibold ${getCorrelationColor(correlation)}`}>
                {correlation !== null && correlation !== undefined ? correlation.toFixed(3) : 'N/A'}
              </span>
            </div>
            {correlation !== null && correlation !== undefined && (
              <div className="pt-2 mt-2">
                <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
                  {correlation > 0.7 && (
                    <p className="text-blue-600 dark:text-blue-400">✓ 높은 상관관계 (0.7 이상)</p>
                  )}
                  {correlation > 0.3 && correlation <= 0.7 && (
                    <p className="text-yellow-600 dark:text-yellow-400">중간 상관관계 (0.3 ~ 0.7)</p>
                  )}
                  {correlation <= 0.3 && (
                    <p className="text-gray-500 dark:text-gray-400">낮은 상관관계 (0.3 이하)</p>
                  )}
                </div>
              </div>
            )}
            {dataError && correlation === null && (
              <div className="pt-2 mt-2">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  벤치마크 데이터가 없어 상관계수를 계산할 수 없습니다.
                </p>
              </div>
            )}
            <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-600">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500 dark:text-gray-400">데이터 포인트</span>
                <span className="text-xs text-gray-600 dark:text-gray-400">{data_points || 0}건</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 설명 */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
          <p>
            <strong>초과수익률 (Alpha):</strong> 종목 수익률에서 벤치마크 수익률을 뺀 값입니다. 양수면 벤치마크보다 우수한 성과를 의미합니다.
          </p>
          <p>
            <strong>상관계수:</strong> 종목과 벤치마크의 움직임이 얼마나 유사한지를 나타냅니다. 1에 가까울수록 유사하게 움직입니다.
          </p>
        </div>
      </div>
    </div>
  )
}

BenchmarkComparison.propTypes = {
  ticker: PropTypes.string.isRequired,
  benchmark: PropTypes.oneOf(['KOSPI', 'KOSDAQ', 'KOSPI200']),
  period: PropTypes.oneOf(['1w', '1m', '3m', '6m', '1y']),
}
