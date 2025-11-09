import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { etfApi, dataApi } from '../services/api'
import ETFCard from '../components/etf/ETFCard'
import ETFCardSkeleton from '../components/common/ETFCardSkeleton'
import PageHeader from '../components/common/PageHeader'

export default function Dashboard() {
  const queryClient = useQueryClient()
  const [sortBy, setSortBy] = useState('name') // 'name', 'type', 'ticker'
  const [lastUpdate, setLastUpdate] = useState(new Date())
  const [autoRefresh, setAutoRefresh] = useState(false)

  // 스케줄러 상태 조회 (마지막 수집 시각)
  const { data: schedulerStatus } = useQuery({
    queryKey: ['scheduler-status'],
    queryFn: async () => {
      const response = await dataApi.getSchedulerStatus()
      return response.data.scheduler
    },
    refetchInterval: 30000, // 30초마다 스케줄러 상태 갱신
    retry: 1,
  })

  // 전체 데이터 새로고침 함수
  const handleRefreshAll = async () => {
    // 모든 쿼리 무효화하여 재조회
    await queryClient.invalidateQueries({ queryKey: ['etfs'] })
    await queryClient.invalidateQueries({ queryKey: ['prices'] })
    await queryClient.invalidateQueries({ queryKey: ['trading-flow'] })
    await queryClient.invalidateQueries({ queryKey: ['news'] })
    await queryClient.invalidateQueries({ queryKey: ['scheduler-status'] })
    setLastUpdate(new Date())
  }

  const { data: etfs, isLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['etfs'],
    queryFn: async () => {
      const response = await etfApi.getAll()
      return response.data
    },
    retry: 2,
    staleTime: 300000, // 5분간 캐시
    refetchOnWindowFocus: true, // 윈도우 포커스 시 자동 갱신
  })

  // 자동 갱신 시 모든 데이터 갱신
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        handleRefreshAll()
      }, 30000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

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

  // 정렬 함수
  const sortedEtfs = etfs ? [...etfs].sort((a, b) => {
    switch (sortBy) {
      case 'name':
        return a.name.localeCompare(b.name, 'ko-KR')
      case 'type':
        // ETF가 먼저, STOCK이 나중
        if (a.type === b.type) return a.name.localeCompare(b.name, 'ko-KR')
        return a.type === 'ETF' ? -1 : 1
      case 'ticker':
        return a.ticker.localeCompare(b.ticker)
      default:
        return 0
    }
  }) : []

  // 로딩 상태
  if (isLoading) {
    return (
      <div className="animate-fadeIn">
        <PageHeader title="ETF Dashboard" subtitle="한국 고성장 섹터 종합 분석" />
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
        <PageHeader title="ETF Dashboard" subtitle="한국 고성장 섹터 종합 분석" />
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
        <PageHeader title="ETF Dashboard" subtitle="한국 고성장 섹터 종합 분석" />
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center max-w-2xl mx-auto">
          <svg
            className="w-16 h-16 mx-auto mb-4 text-gray-400"
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
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            등록된 종목이 없습니다
          </h2>
          <p className="text-gray-600">종목 데이터를 추가해주세요.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fadeIn">
      {/* 헤더 */}
      <PageHeader
        title="ETF Dashboard"
        subtitle={
          <span>
            총 <span className="font-semibold text-primary">{etfs.length}</span>개 종목
          </span>
        }
      >
        {/* 정렬 옵션 */}
        <label className="text-sm text-gray-600 hidden sm:inline">정렬:</label>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="input text-sm py-2"
          aria-label="종목 정렬 기준 선택"
        >
          <option value="name">이름순</option>
          <option value="type">타입별</option>
          <option value="ticker">코드순</option>
        </select>
      </PageHeader>

      {/* 날짜 및 업데이트 정보 */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white rounded-lg p-4 shadow-sm">
        <div className="flex flex-col gap-2">
          {/* 오늘 날짜 */}
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span className="text-sm font-medium text-gray-700">{formatDate(new Date())}</span>
          </div>

          {/* 수집/업데이트 시간 정보 */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
            {/* 마지막 수집일시 (스케줄러) */}
            {schedulerStatus?.last_collection_time && (
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm text-gray-600">
                  마지막 수집일시: <span className="font-medium text-success">{formatUpdateTime(new Date(schedulerStatus.last_collection_time))}</span>
                </span>
              </div>
            )}

            {/* 화면 업데이트 시간 */}
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm text-gray-600">
                마지막 업데이트: <span className="font-medium text-gray-700">{formatUpdateTime(lastUpdate)}</span>
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
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 text-primary-500 bg-gray-100 border-gray-300 rounded focus:ring-primary-500 focus:ring-2 transition-colors"
              aria-label="자동 갱신 토글"
            />
            <span className="text-sm text-gray-600 group-hover:text-gray-900 transition-colors">자동 갱신 (30초)</span>
          </label>

          {/* 수동 새로고침 버튼 */}
          <button
            onClick={handleRefreshAll}
            className="btn btn-outline btn-sm"
            aria-label="모든 데이터 새로고침"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span className="hidden sm:inline ml-1">새로고침</span>
          </button>
        </div>
      </div>

      {/* 종목 그리드 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">
        {sortedEtfs.map((etf) => (
          <ETFCard key={etf.ticker} etf={etf} />
        ))}
      </div>
    </div>
  )
}
