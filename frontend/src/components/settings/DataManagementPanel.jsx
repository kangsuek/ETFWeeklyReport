import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '../../contexts/ToastContext'
import { dataApi } from '../../services/api'

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
      return response.data
    },
    refetchInterval: 30000, // 30초마다 자동 갱신
  })

  // 캐시 통계 조회
  const { data: cacheStats, isLoading: cacheStatsLoading } = useQuery({
    queryKey: ['cache-stats'],
    queryFn: async () => {
      const response = await dataApi.getCacheStats()
      return response.data
    },
    refetchInterval: 10000, // 10초마다 자동 갱신 (캐시는 자주 변경됨)
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

        {/* 캐시 통계 섹션 */}
        <section>
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">캐시 성능</h3>

          {cacheStatsLoading ? (
            <div className="space-y-2">
              <div className="skeleton-text h-16"></div>
            </div>
          ) : cacheStats ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* 캐시 적중률 */}
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900 dark:to-blue-800 rounded-lg p-4">
                  <div className="text-xs text-blue-700 dark:text-blue-300 mb-1">캐시 적중률</div>
                  <div className="text-2xl font-bold text-blue-900 dark:text-blue-100">
                    {cacheStats.hit_rate_pct.toFixed(1)}%
                  </div>
                  <div className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                    목표: 60% 이상
                  </div>
                </div>

                {/* 캐시 히트 */}
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">캐시 히트</div>
                  <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {formatNumber(cacheStats.hits)}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    총 {formatNumber(cacheStats.total_requests)}건 중
                  </div>
                </div>

                {/* 캐시 미스 */}
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">캐시 미스</div>
                  <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                    {formatNumber(cacheStats.misses)}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    제거: {formatNumber(cacheStats.evictions)}건
                  </div>
                </div>

                {/* 현재 캐시 크기 */}
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">현재 캐시 크기</div>
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {cacheStats.current_size}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    최대: {cacheStats.max_size}개
                  </div>
                </div>
              </div>

              {/* 캐시 설정 정보 */}
              <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="text-xs text-gray-600 dark:text-gray-300">
                  <span className="font-semibold">기본 TTL:</span> {cacheStats.default_ttl_seconds}초 |
                  <span className="font-semibold ml-2">저장된 항목:</span> {cacheStats.sets}건
                </div>
              </div>
            </>
          ) : null}
        </section>

        {/* 데이터 수집 섹션 */}
        <section className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4">데이터 수집</h3>

          <div className="space-y-4">
            {/* 수집 일수 선택 */}
            <div>
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

            <p className="text-xs text-gray-500 dark:text-gray-400">
              모든 종목의 가격, 매매 동향 데이터를 수집합니다. 소요 시간: 약 {collectionDays * 6}초
            </p>
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
