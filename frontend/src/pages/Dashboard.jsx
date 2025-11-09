import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { etfApi } from '../services/api'
import ETFCard from '../components/etf/ETFCard'
import ETFCardSkeleton from '../components/common/ETFCardSkeleton'

export default function Dashboard() {
  const [sortBy, setSortBy] = useState('name') // 'name', 'type', 'ticker'

  const { data: etfs, isLoading, error, refetch } = useQuery({
    queryKey: ['etfs'],
    queryFn: async () => {
      const response = await etfApi.getAll()
      return response.data
    },
    retry: 2,
    staleTime: 300000, // 5분간 캐시
  })

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
      <div>
        <h1 className="text-3xl font-bold mb-8">ETF Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
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
      <div>
        <h1 className="text-3xl font-bold mb-8">ETF Dashboard</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center">
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
            className="btn btn-primary hover:opacity-90 transition-opacity"
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
      <div>
        <h1 className="text-3xl font-bold mb-8">ETF Dashboard</h1>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
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
    <div>
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4">ETF Dashboard</h1>
        <div className="flex items-center justify-between">
          <p className="text-gray-600">
            총 <span className="font-semibold text-primary">{etfs.length}</span>개 종목
          </p>

          {/* 정렬 옵션 */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">정렬:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="text-sm border border-gray-300 rounded px-3 py-1 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              <option value="name">이름순</option>
              <option value="type">타입별</option>
              <option value="ticker">코드순</option>
            </select>
          </div>
        </div>
      </div>

      {/* 종목 그리드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {sortedEtfs.map((etf) => (
          <ETFCard key={etf.ticker} etf={etf} />
        ))}
      </div>
    </div>
  )
}
