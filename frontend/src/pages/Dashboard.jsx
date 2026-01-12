import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { useState, useEffect, useCallback, useMemo } from 'react'
import { etfApi, dataApi, settingsApi } from '../services/api'
import ETFCardSkeleton from '../components/common/ETFCardSkeleton'
import PageHeader from '../components/common/PageHeader'
import DashboardFilters from '../components/dashboard/DashboardFilters'
import ETFCardGrid from '../components/dashboard/ETFCardGrid'
import { useSettings } from '../contexts/SettingsContext'
import { useToast } from '../contexts/ToastContext'
import { CACHE_STALE_TIME_STATIC, CACHE_STALE_TIME_FAST, CACHE_STALE_TIME_STATUS } from '../constants'

export default function Dashboard() {
  const queryClient = useQueryClient()
  const { settings, updateSettings } = useSettings()
  const toast = useToast()
  const [lastUpdate, setLastUpdate] = useState(new Date())
  // 기본 정렬은 'config' (stocks.json 순서)
  // 저장된 카드 순서가 있으면 'custom' 모드로 시작
  const [sortBy, setSortBy] = useState(() =>
    settings.cardOrder && settings.cardOrder.length > 0 ? 'custom' : 'config'
  )
  const [sortDirection, setSortDirection] = useState('asc') // 'asc', 'desc'

  // 스케줄러 상태 조회 (마지막 수집 시각)
  const { data: schedulerStatus } = useQuery({
    queryKey: ['scheduler-status'],
    queryFn: async () => {
      const response = await dataApi.getSchedulerStatus()
      return response.data.scheduler
    },
    refetchInterval: 30000, // 30초마다 스케줄러 상태 갱신
    retry: 1,
    staleTime: CACHE_STALE_TIME_STATUS, // 10초 (상태 정보)
  })

  // 전체 데이터 새로고침 함수
  const handleRefreshAll = useCallback(async () => {
    // 모든 쿼리 무효화하여 재조회
    await queryClient.invalidateQueries({ queryKey: ['etfs'] })
    await queryClient.invalidateQueries({ queryKey: ['batch-summary'] })
    await queryClient.invalidateQueries({ queryKey: ['scheduler-status'] })
    setLastUpdate(new Date())
  }, [queryClient])

  // 전체 종목 목록 조회
  const { data: etfs, isLoading: etfsLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['etfs'],
    queryFn: async () => {
      const response = await etfApi.getAll()
      return response.data
    },
    retry: 2,
    staleTime: CACHE_STALE_TIME_STATIC, // 5분 (정적 데이터)
    refetchOnWindowFocus: true, // 윈도우 포커스 시 자동 갱신
  })

  // 배치 요약 데이터 조회 (N+1 쿼리 최적화)
  const { data: batchSummary, isLoading: summaryLoading } = useQuery({
    queryKey: ['batch-summary', etfs?.map(e => e.ticker)],
    queryFn: async () => {
      if (!etfs || etfs.length === 0) return null
      const tickers = etfs.map(e => e.ticker)
      const response = await etfApi.getBatchSummary(tickers, 5, 5)
      return response.data.data  // response.data.data = {ticker: summary}
    },
    enabled: !!etfs && etfs.length > 0,  // etfs가 로드된 후에만 실행
    retry: 1,
    staleTime: CACHE_STALE_TIME_FAST, // 30초 (배치 요약)
  })

  const isLoading = etfsLoading || summaryLoading

  // 자동 갱신 시 모든 데이터 갱신 (설정 기반)
  useEffect(() => {
    if (settings.autoRefresh.enabled) {
      const interval = setInterval(() => {
        handleRefreshAll()
      }, settings.autoRefresh.interval)
      return () => clearInterval(interval)
    }
  }, [settings.autoRefresh.enabled, settings.autoRefresh.interval, handleRefreshAll])

  // 오늘 날짜 포맷팅
  const formatDate = (date) => {
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long'
    })
  }

  // 업데이트 시간 포맷팅
  const formatUpdateTime = (date) => {
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  }

  // 정렬 변경 핸들러
  const handleSortChange = (newSortBy) => {
    if (sortBy === newSortBy) {
      // 같은 컬럼을 클릭하면 방향 전환
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      // 다른 컬럼을 클릭하면 오름차순으로 시작
      setSortBy(newSortBy)
      setSortDirection('asc')
    }
  }

  // 종목 순서 변경 Mutation (백엔드 동기화)
  const reorderMutation = useMutation({
    mutationFn: (newOrder) => settingsApi.reorderStocks(newOrder),
    onMutate: async (newOrder) => {
      // Optimistic update
      await queryClient.cancelQueries({ queryKey: ['etfs'] })
      const previousETFs = queryClient.getQueryData(['etfs'])
      
      // ETF 데이터를 새 순서대로 정렬
      if (previousETFs) {
        const reordered = newOrder.map(ticker => previousETFs.find(etf => etf.ticker === ticker)).filter(Boolean)
        queryClient.setQueryData(['etfs'], reordered)
      }
      
      return { previousETFs }
    },
    onSuccess: (data, variables) => {
      // 백엔드와 프론트엔드 캐시 모두 무효화
      queryClient.invalidateQueries({ queryKey: ['etfs'] })
      queryClient.invalidateQueries({ queryKey: ['settings-stocks'] })
      toast.success('종목 순서가 성공적으로 변경되었습니다.', 2000)
    },
    onError: (error, newOrder, context) => {
      toast.error(`순서 변경 실패: ${error.message}`, 3000)
      // Rollback
      if (context?.previousETFs) {
        queryClient.setQueryData(['etfs'], context.previousETFs)
      }
    },
  })

  // 카드 순서 변경 핸들러 (대시보드 드래그 앤 드롭)
  const handleOrderChange = useCallback((newOrder) => {
    // 로컬 설정 업데이트 (custom 모드용)
    updateSettings('cardOrder', newOrder)
    
    // 백엔드 stocks.json 동기화
    reorderMutation.mutate(newOrder)
  }, [updateSettings]) // reorderMutation을 의존성에서 제거

  // 정렬된 데이터 가져오기 (메모이제이션)
  const sortedETFs = useMemo(() => {
    if (!etfs) return []

    // 커스텀 순서가 있고, sortBy가 'custom'이면 커스텀 순서 사용
    if (sortBy === 'custom' && settings.cardOrder && settings.cardOrder.length > 0) {
      const orderMap = new Map(settings.cardOrder.map((ticker, index) => [ticker, index]))
      return [...etfs].sort((a, b) => {
        const orderA = orderMap.get(a.ticker) ?? Infinity
        const orderB = orderMap.get(b.ticker) ?? Infinity
        return orderA - orderB
      })
    }

    // 'config' 모드: 백엔드에서 이미 stocks.json 순서대로 정렬됨
    if (sortBy === 'config') {
      return etfs
    }

    // 기본 정렬 로직
    const sorted = [...etfs].sort((a, b) => {
      let compareValue = 0

      switch (sortBy) {
        case 'type':
          // STOCK이 ETF보다 먼저 오도록 (STOCK = 0, ETF = 1)
          const typeOrder = { 'STOCK': 0, 'ETF': 1 }
          compareValue = typeOrder[a.type] - typeOrder[b.type]
          // 타입이 같으면 이름순으로 정렬
          if (compareValue === 0) {
            compareValue = a.name.localeCompare(b.name, 'ko-KR')
          }
          break

        case 'name':
          compareValue = a.name.localeCompare(b.name, 'ko-KR')
          break

        case 'theme':
          const themeA = a.theme || ''
          const themeB = b.theme || ''
          compareValue = themeA.localeCompare(themeB, 'ko-KR')
          // 테마가 같으면 이름순으로 정렬
          if (compareValue === 0) {
            compareValue = a.name.localeCompare(b.name, 'ko-KR')
          }
          break

        default:
          compareValue = 0
      }

      return sortDirection === 'asc' ? compareValue : -compareValue
    })

    return sorted
  }, [etfs, sortBy, sortDirection, settings.cardOrder])

  // 로딩 상태
  if (isLoading) {
    return (
      <div className="animate-fadeIn">
        <PageHeader title="Insights Dashboard" subtitle="한국 고성장 섹터 종합 분석" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
          {[...Array(6)].map((_, index) => (
            <ETFCardSkeleton key={index} />
          ))}
        </div>
      </div>
    )
  }

  // 에러 상태
  if (error) {
    return (
      <div className="animate-fadeIn">
        <PageHeader title="Insights Dashboard" subtitle="한국 고성장 섹터 종합 분석" />
        <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center max-w-2xl mx-auto">
          <svg
            className="w-16 h-16 mx-auto mb-4 text-red-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h2 className="text-xl font-semibold text-red-800 mb-2">
            데이터를 불러올 수 없습니다
          </h2>
          <p className="text-red-600 mb-6">{error.message}</p>
          <button
            onClick={() => refetch()}
            className="btn btn-primary"
            aria-label="다시 시도"
          >
            다시 시도
          </button>
        </div>
      </div>
    )
  }

  // 빈 데이터 상태
  if (!etfs || etfs.length === 0) {
    return (
      <div className="animate-fadeIn">
        <PageHeader title="Insights Dashboard" subtitle="한국 고성장 섹터 종합 분석" />
        <div className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-8 text-center max-w-2xl mx-auto transition-colors">
          <svg
            className="w-16 h-16 mx-auto mb-4 text-gray-400 dark:text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
            등록된 종목이 없습니다
          </h2>
          <p className="text-gray-600 dark:text-gray-400">종목 데이터를 추가해주세요.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fadeIn">
      {/* 헤더 */}
      <PageHeader
        title="Insights Dashboard"
        subtitle={
          <span>
            총 <span className="font-semibold text-primary">{etfs.length}</span>개 종목
          </span>
        }
      />

      {/* 정렬 컨트롤 */}
      <DashboardFilters
        sortBy={sortBy}
        sortDirection={sortDirection}
        onSortChange={handleSortChange}
      />

      {/* 날짜 및 업데이트 정보 */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm transition-colors">
        <div className="flex flex-col gap-2">
          {/* 오늘 날짜 */}
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{formatDate(new Date())}</span>
          </div>

          {/* 수집/업데이트 시간 정보 */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
            {/* 마지막 수집일시 (스케줄러) */}
            {schedulerStatus?.last_collection_time && (
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  마지막 수집일시: <span className="font-medium text-success">{formatUpdateTime(new Date(schedulerStatus.last_collection_time))}</span>
                </span>
              </div>
            )}

            {/* 화면 업데이트 시간 */}
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                마지막 업데이트: <span className="font-medium text-gray-700 dark:text-gray-300">{formatUpdateTime(lastUpdate)}</span>
              </span>
            </div>
          </div>
        </div>

        {/* 컨트롤 버튼 */}
        <div className="flex items-center gap-3">
          {/* 자동 새로고침 토글 */}
          <label className="flex items-center gap-2 cursor-pointer group">
            <input
              type="checkbox"
              checked={settings.autoRefresh.enabled}
              onChange={(e) => updateSettings('autoRefresh.enabled', e.target.checked)}
              className="w-4 h-4 text-primary-500 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-primary-500 focus:ring-2 transition-colors"
              aria-label="자동 갱신 토글"
            />
            <span className="text-sm text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-200 transition-colors">
              자동 갱신 ({settings.autoRefresh.interval / 1000}초)
            </span>
          </label>

          {/* 수동 새로고침 버튼 */}
          <button
            onClick={handleRefreshAll}
            className="btn btn-outline btn-sm"
            aria-label="모든 데이터 새로고침"
            title="모든 데이터 새로고침"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span className="hidden sm:inline ml-1">새로고침</span>
          </button>
        </div>
      </div>

      {/* 종목 그리드 */}
      <ETFCardGrid
        etfs={sortedETFs}
        batchSummary={batchSummary}
        onOrderChange={(newOrder) => {
          handleOrderChange(newOrder)
          // 드래그로 순서를 변경하면 자동으로 커스텀 정렬 모드로 전환
          if (sortBy !== 'custom') {
            setSortBy('custom')
          }
        }}
      />
    </div>
  )
}
