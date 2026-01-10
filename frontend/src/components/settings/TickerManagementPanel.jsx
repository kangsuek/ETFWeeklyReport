import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { etfApi, settingsApi } from '../../services/api'
import TickerForm from './TickerForm'
import TickerDeleteConfirm from './TickerDeleteConfirm'

export default function TickerManagementPanel() {
  const queryClient = useQueryClient()
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false)
  const [selectedTicker, setSelectedTicker] = useState(null)
  const [formMode, setFormMode] = useState('create') // 'create' or 'edit'

  // 현재 종목 목록 조회 (stocks.json 기반)
  const { data: stocks, isLoading, error } = useQuery({
    queryKey: ['settings-stocks'],
    queryFn: async () => {
      const response = await settingsApi.getStocks()
      return response.data
    },
  })

  // 종목 추가 Mutation
  const createMutation = useMutation({
    mutationFn: (data) => settingsApi.createStock(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings-stocks'] })
      queryClient.invalidateQueries({ queryKey: ['etfs'] }) // 대시보드 캐시도 무효화
      setIsFormOpen(false)
      alert('종목이 성공적으로 추가되었습니다.')
    },
    onError: (error) => {
      alert(`종목 추가 실패: ${error.message}`)
    },
  })

  // 종목 수정 Mutation
  const updateMutation = useMutation({
    mutationFn: ({ ticker, data }) => settingsApi.updateStock(ticker, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings-stocks'] })
      queryClient.invalidateQueries({ queryKey: ['etfs'] }) // 대시보드 캐시도 무효화
      setIsFormOpen(false)
      setSelectedTicker(null)
      alert('종목이 성공적으로 수정되었습니다.')
    },
    onError: (error) => {
      alert(`종목 수정 실패: ${error.message}`)
    },
  })

  // 종목 삭제 Mutation
  const deleteMutation = useMutation({
    mutationFn: (ticker) => settingsApi.deleteStock(ticker),
    onSuccess: (response, deletedTicker) => {
      // 삭제 직후 목록에서 제거되도록 React Query 캐시 즉시 업데이트
      queryClient.setQueryData(['settings-stocks'], (oldStocks) => {
        if (!Array.isArray(oldStocks)) return oldStocks
        return oldStocks.filter((stock) => stock.ticker !== deletedTicker)
      })

      queryClient.invalidateQueries({ queryKey: ['settings-stocks'] })
      queryClient.invalidateQueries({ queryKey: ['etfs'] }) // 대시보드 캐시도 무효화
      setIsDeleteConfirmOpen(false)
      setSelectedTicker(null)
      const deleted = response.data.deleted
      alert(
        `종목이 삭제되었습니다.\n` +
        `- 가격 데이터: ${deleted.prices}개\n` +
        `- 뉴스: ${deleted.news}개\n` +
        `- 매매 동향: ${deleted.trading_flow}개`
      )
    },
    onError: (error) => {
      alert(`종목 삭제 실패: ${error.message}`)
    },
  })

  const handleAddClick = () => {
    setFormMode('create')
    setSelectedTicker(null)
    setIsFormOpen(true)
  }

  const handleEditClick = (stock) => {
    setFormMode('edit')
    setSelectedTicker(stock)
    setIsFormOpen(true)
  }

  const handleDeleteClick = (stock) => {
    setSelectedTicker(stock)
    setIsDeleteConfirmOpen(true)
  }

  const handleFormSubmit = (data) => {
    if (formMode === 'create') {
      createMutation.mutate(data)
    } else {
      updateMutation.mutate({ ticker: selectedTicker.ticker, data })
    }
  }

  const handleDeleteConfirm = () => {
    if (selectedTicker) {
      deleteMutation.mutate(selectedTicker.ticker)
    }
  }

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 transition-colors">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 transition-colors">
        <div className="text-red-600 dark:text-red-400">
          <p className="font-semibold">오류 발생</p>
          <p className="text-sm mt-2">{error.message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow transition-colors">
      {/* 헤더 */}
      <div className="px-4 sm:px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-gray-100">종목 관리</h2>
            <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
              stocks.json 기반 종목 추가/수정/삭제
            </p>
          </div>
          <button
            onClick={handleAddClick}
            className="w-full sm:w-auto px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors flex items-center justify-center gap-2 text-sm sm:text-base"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            새 종목 추가
          </button>
        </div>
      </div>

      {/* 데스크톱 테이블 (md 이상) */}
      <div className="hidden md:block overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                티커
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                종목명
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                타입
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                테마
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                작업
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {stocks && stocks.length > 0 ? (
              stocks.map((stock) => (
                <tr key={stock.ticker} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                    {stock.ticker}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                    {stock.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      stock.type === 'ETF'
                        ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-300'
                        : 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300'
                    }`}>
                      {stock.type}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {stock.theme}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => handleEditClick(stock)}
                      className="text-primary-600 dark:text-primary-400 hover:text-primary-900 dark:hover:text-primary-300 mr-4 transition-colors"
                    >
                      수정
                    </button>
                    <button
                      onClick={() => handleDeleteClick(stock)}
                      className="text-red-600 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 transition-colors"
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="5" className="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                  등록된 종목이 없습니다.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 모바일 카드 뷰 (md 미만) */}
      <div className="md:hidden divide-y divide-gray-200 dark:divide-gray-700">
        {stocks && stocks.length > 0 ? (
          stocks.map((stock) => (
            <div key={stock.ticker} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 truncate">
                      {stock.name}
                    </h3>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${
                      stock.type === 'ETF'
                        ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-300'
                        : 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300'
                    }`}>
                      {stock.type}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{stock.ticker}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-500">{stock.theme}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleEditClick(stock)}
                  className="flex-1 px-3 py-2 bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded-lg hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors text-sm font-medium"
                >
                  수정
                </button>
                <button
                  onClick={() => handleDeleteClick(stock)}
                  className="flex-1 px-3 py-2 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors text-sm font-medium"
                >
                  삭제
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="p-6 text-center text-sm text-gray-500 dark:text-gray-400">
            등록된 종목이 없습니다.
          </div>
        )}
      </div>

      {/* 모달들 */}
      {isFormOpen && (
        <TickerForm
          mode={formMode}
          initialData={selectedTicker}
          onSubmit={handleFormSubmit}
          onClose={() => {
            setIsFormOpen(false)
            setSelectedTicker(null)
          }}
          isSubmitting={createMutation.isPending || updateMutation.isPending}
        />
      )}

      {isDeleteConfirmOpen && (
        <TickerDeleteConfirm
          ticker={selectedTicker}
          onConfirm={handleDeleteConfirm}
          onClose={() => {
            setIsDeleteConfirmOpen(false)
            setSelectedTicker(null)
          }}
          isDeleting={deleteMutation.isPending}
        />
      )}
    </div>
  )
}
