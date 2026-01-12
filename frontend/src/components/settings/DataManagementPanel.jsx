import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '../../contexts/ToastContext'
import { dataApi, settingsApi } from '../../services/api'

/**
 * 데이터 관리 패널 컴포넌트
 * 데이터 통계, 수집, 초기화 기능을 제공합니다.
 */
export default function DataManagementPanel() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [isResetModalOpen, setIsResetModalOpen] = useState(false)
  const [collectionDays, setCollectionDays] = useState(10)

  // 데이터 통계 조회
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['data-stats'],
    queryFn: async () => {
      const response = await dataApi.getStats()
      // 디버깅: API 응답 확인
      console.log('Data Stats Response:', response.data)
      return response.data
    },
    refetchInterval: 30000, // 30초마다 자동 갱신
  })

  // 전체 데이터 수집 Mutation
  const collectMutation = useMutation({
    mutationFn: async (days) => {
      const response = await dataApi.collectAll(days)
      return response.data
    },
    onSuccess: (data) => {
      // 성공 메시지 표시
      toast.success(
        `데이터 수집 완료! 가격: ${data.result.total_price_records}건, 매매 동향: ${data.result.total_trading_flow_records}건, 뉴스: ${data.result.total_news_records}건`,
        5000
      )

      // 모든 캐시 무효화하여 최신 데이터 반영
      queryClient.invalidateQueries()
    },
    onError: (error) => {
      toast.error(`데이터 수집 실패: ${error.message}`)
    },
  })

  // 종목 목록 수집 Mutation
  const collectTickerCatalogMutation = useMutation({
    mutationFn: async () => {
      const response = await settingsApi.collectTickerCatalog()
      return response.data
    },
    onSuccess: (data) => {
      // 성공 메시지 표시
      toast.success(
        `종목 목록 수집 완료! 총 ${data.total_collected}개 (코스피: ${data.kospi_count}, 코스닥: ${data.kosdaq_count}, ETF: ${data.etf_count})`,
        5000
      )

      // 캐시 무효화
      queryClient.invalidateQueries({ queryKey: ['data-stats'] })
    },
    onError: (error) => {
      toast.error(`종목 목록 수집 실패: ${error.message}`)
    },
  })

  // 데이터베이스 초기화 Mutation
  const resetMutation = useMutation({
    mutationFn: async () => {
      const response = await dataApi.reset()
      return response.data
    },
    onSuccess: (data) => {
      setIsResetModalOpen(false)

      // 성공 메시지 표시
      toast.success(
        `데이터베이스 초기화 완료. 가격: ${data.deleted.prices}건, 뉴스: ${data.deleted.news}건, 매매 동향: ${data.deleted.trading_flow}건 삭제됨`,
        5000
      )

      // 모든 React Query 캐시 삭제
      queryClient.clear()

      // 페이지 새로고침하여 모든 캐시 완전히 제거
      setTimeout(() => window.location.reload(), 1000)
    },
    onError: (error) => {
      toast.error(`데이터베이스 초기화 실패: ${error.message}`)
      setIsResetModalOpen(false)
    },
  })

  // 전체 데이터 수집 핸들러
  const handleCollectAll = () => {
    if (collectMutation.isPending) return

    if (window.confirm(`최근 ${collectionDays}일 데이터를 수집하시겠습니까?\n\n소요 시간: 약 ${collectionDays * 6}초`)) {
      collectMutation.mutate(collectionDays)
    }
  }

  // 종목 목록 수집 핸들러
  const handleCollectTickerCatalog = () => {
    if (collectTickerCatalogMutation.isPending) return

    if (window.confirm(`전체 종목 목록(코스피, 코스닥, ETF)을 수집하시겠습니까?\n\n소요 시간: 약 5-10분\n\n이 작업은 새 종목 추가 시 자동완성 기능을 위해 필요합니다.`)) {
      collectTickerCatalogMutation.mutate()
    }
  }

  // 데이터베이스 초기화 핸들러
  const handleReset = () => {
    if (resetMutation.isPending) return

    setIsResetModalOpen(true)
  }

  // 초기화 확인 모달 핸들러
  const handleConfirmReset = () => {
    resetMutation.mutate()
  }

  // 날짜 포맷팅
  const formatDate = (dateStr) => {
    // null, undefined, 빈 문자열인 경우 "-" 반환
    if (dateStr === null || dateStr === undefined || dateStr === '') {
      return '-'
    }
    const date = new Date(dateStr)
    // 유효하지 않은 날짜인 경우도 "-" 반환
    if (isNaN(date.getTime())) {
      return '-'
    }
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // 숫자 포맷팅 (천 단위 콤마)
  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-'
    return new Intl.NumberFormat('ko-KR').format(num)
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow dark:shadow-gray-900">
      {/* 헤더 */}
      <div className="px-4 sm:px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h2 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-gray-100">데이터 관리</h2>
          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
            데이터베이스 통계 및 수집 관리
          </p>
        </div>
      </div>

      {/* 내용 */}
      <div className="px-4 sm:px-6 py-6 space-y-8">
        {/* 데이터 통계 섹션 */}
        <section>
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">데이터 통계</h3>

          {statsLoading ? (
            <div className="space-y-2">
              <div className="skeleton-text h-16"></div>
              <div className="skeleton-text h-16"></div>
            </div>
          ) : statsError ? (
            <div className="text-center py-4 text-sm text-red-600 dark:text-red-400">
              통계 조회 실패: {statsError.message}
            </div>
          ) : stats ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* 종목 수 */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">종목 수</div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.etfs}</div>
              </div>

              {/* 가격 레코드 */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">가격 레코드</div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{formatNumber(stats.prices)}</div>
              </div>

              {/* 매매 동향 레코드 */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">매매 동향 레코드</div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{formatNumber(stats.trading_flow)}</div>
              </div>

              {/* 뉴스 수 */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">뉴스 수</div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{formatNumber(stats.news)}</div>
              </div>

              {/* 마지막 수집 시간 */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">마지막 수집</div>
                <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{formatDate(stats.last_collection)}</div>
              </div>

              {/* DB 크기 */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">데이터베이스 크기</div>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.database_size_mb} MB</div>
              </div>
            </div>
          ) : null}
        </section>

        {/* 데이터 수집 섹션 */}
        <section className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">데이터 수집</h3>

          <div className="space-y-6">
            {/* 종목 목록 수집 */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-100">종목 목록 수집</h4>
                {stats && 'stock_catalog' in stats && stats.stock_catalog != null ? (
                  <span className="text-xs text-blue-700 dark:text-blue-300 font-medium">
                    현재 {typeof stats.stock_catalog === 'number' ? stats.stock_catalog.toLocaleString('ko-KR') : stats.stock_catalog}개
                  </span>
                ) : statsLoading ? (
                  <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">로딩 중...</span>
                ) : (
                  <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                    수집 필요
                  </span>
                )}
              </div>
              <p className="text-xs text-blue-700 dark:text-blue-300 mb-3">
                네이버 금융에서 전체 종목 목록을 수집합니다. 새 종목 추가 시 자동완성 기능을 사용하려면 먼저 이 작업을 수행해야 합니다.
              </p>
              <button
                onClick={handleCollectTickerCatalog}
                disabled={collectTickerCatalogMutation.isPending}
                className="w-full sm:w-auto px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm sm:text-base font-medium"
              >
                {collectTickerCatalogMutation.isPending ? (
                  <>
                    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>종목 목록 수집 중... (5-10분 소요)</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                    </svg>
                    <span>종목 목록 수집</span>
                  </>
                )}
              </button>
              <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                💡 최초 1회 실행 권장. 이후에는 분기별 1회 정도 실행하면 충분합니다.
              </p>
            </div>

            {/* 가격/뉴스 데이터 수집 */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">가격/뉴스 데이터 수집</h4>
              
              {/* 수집 일수 선택 */}
              <div className="mb-3">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                수집 기간 (일)
              </label>
              <select
                value={collectionDays}
                onChange={(e) => setCollectionDays(Number(e.target.value))}
                className="w-full sm:w-auto px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                disabled={collectMutation.isPending}
              >
                <option value={1}>1일 (당일)</option>
                <option value={7}>7일 (1주)</option>
                <option value={10}>10일</option>
                <option value={30}>30일 (1개월)</option>
                <option value={90}>90일 (3개월)</option>
              </select>
            </div>

            {/* 전체 데이터 수집 버튼 */}
            <button
              onClick={handleCollectAll}
              disabled={collectMutation.isPending}
              className="w-full sm:w-auto px-6 py-3 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm sm:text-base font-medium"
            >
              {collectMutation.isPending ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>데이터 수집 중...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span>전체 데이터 수집</span>
                </>
              )}
            </button>

              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              모든 종목의 가격, 매매 동향 데이터를 수집합니다. 소요 시간: 약 {collectionDays * 6}초
            </p>
            </div>
          </div>
        </section>

        {/* 위험 작업 섹션 */}
        <section className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <div className="flex items-start gap-3 mb-4">
              <svg className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <h3 className="text-base font-semibold text-red-900 dark:text-red-100">위험 작업</h3>
                <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                  아래 작업은 되돌릴 수 없습니다. 신중하게 실행하세요.
                </p>
              </div>
            </div>

            <button
              onClick={handleReset}
              disabled={resetMutation.isPending}
              className="w-full sm:w-auto px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm sm:text-base font-medium"
            >
              {resetMutation.isPending ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>초기화 중...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span>데이터베이스 초기화</span>
                </>
              )}
            </button>

            <p className="text-xs text-red-700 dark:text-red-300 mt-2">
              종목 정보를 제외한 모든 데이터(가격, 뉴스, 매매 동향)가 삭제됩니다.
            </p>
          </div>
        </section>
      </div>

      {/* 초기화 확인 모달 */}
      {isResetModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 px-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-start gap-3 mb-4">
              <svg className="w-8 h-8 text-red-600 dark:text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">데이터베이스 초기화</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                  정말로 모든 데이터를 삭제하시겠습니까?
                </p>
                <ul className="text-sm text-gray-600 dark:text-gray-400 mt-2 list-disc list-inside space-y-1">
                  <li>모든 가격 데이터 삭제</li>
                  <li>모든 뉴스 데이터 삭제</li>
                  <li>모든 매매 동향 데이터 삭제</li>
                </ul>
                <p className="text-sm font-semibold text-red-600 dark:text-red-400 mt-3">
                  ⚠️ 이 작업은 되돌릴 수 없습니다!
                </p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setIsResetModalOpen(false)}
                className="flex-1 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors font-medium"
              >
                취소
              </button>
              <button
                onClick={handleConfirmReset}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
              >
                삭제하기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
