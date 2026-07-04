import { Link } from 'react-router-dom'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import { useUptrendAlerts } from '../../hooks/useUptrendAlerts'
import { alertApi } from '../../services/api'

const formatDate = (iso) => {
  if (!iso) return ''
  const d = new Date(String(iso).slice(0, 10))
  return Number.isNaN(d.getTime())
    ? String(iso).slice(0, 10)
    : d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric' })
}

/**
 * Alerts 페이지의 "상승흐름 신호" 서버 이력 섹션.
 *
 * 기존 3종 알림(메모리·AlertContext)과 분리된, 백엔드가 기록하는 확정 신호 이력을
 * 조회·읽음·삭제한다.
 */
export default function UptrendHistorySection() {
  const { items, unreadCount, markRead } = useUptrendAlerts()
  const queryClient = useQueryClient()

  const deleteMutation = useMutation({
    mutationFn: (id) => alertApi.deleteUptrend(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['uptrendAlerts'] }),
  })

  return (
    <section aria-label="상승흐름 신호 이력" className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          상승흐름 신호
          {unreadCount > 0 && (
            <span className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 text-[10px] font-bold text-white bg-green-500 rounded-full">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </h2>
        {unreadCount > 0 && (
          <button
            onClick={markRead}
            className="text-xs text-primary-500 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
          >
            읽음 표시
          </button>
        )}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        {items.length === 0 ? (
          <div className="py-10 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">확정된 상승흐름 신호가 없습니다</p>
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
              종목 상세의 &lsquo;상승흐름&rsquo; 탭에서 알림을 켜세요
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100 dark:divide-gray-700/50">
            {items.map(item => (
              <li key={item.id} className="flex items-start gap-3 px-4 py-3 group">
                <span className="mt-1.5 w-2.5 h-2.5 rounded-full flex-shrink-0 bg-green-400" />
                <Link to={`/etf/${item.ticker}`} className="min-w-0 flex-1">
                  <p className="text-sm text-gray-800 dark:text-gray-200">{item.message}</p>
                  <time className="mt-1 block text-xs text-gray-400">{formatDate(item.triggered_at)}</time>
                </Link>
                <button
                  onClick={() => deleteMutation.mutate(item.id)}
                  disabled={deleteMutation.isPending}
                  aria-label="삭제"
                  className="p-1 text-gray-300 hover:text-red-500 transition-colors flex-shrink-0"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
