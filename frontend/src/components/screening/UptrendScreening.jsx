import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { alertApi } from '../../services/api'

const STATUS_META = {
  confirmed: { label: '확정', cls: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300', order: 0 },
  pending: { label: '대기', cls: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300', order: 1 },
}

const formatDate = (iso) => {
  if (!iso) return '-'
  const [, m, d] = String(iso).slice(0, 10).split('-')
  return m && d ? `${m}/${d}` : String(iso).slice(0, 10)
}

const formatWon = (v) =>
  v == null ? '-' : `${Math.round(v).toLocaleString()}원`

/**
 * 종목 발굴 '상승흐름' 탭 — 등록 관심종목 중 확정·대기 신호만 표시.
 * watchlist API(읽기 전용)를 재사용한다. 전체 카탈로그가 아닌 등록 종목 대상.
 */
export default function UptrendScreening() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['uptrendScreening'],
    queryFn: async () => {
      const res = await alertApi.scanWatchlist()
      return res.data
    },
    staleTime: 60_000,
  })

  const items = (data?.items ?? [])
    .filter((i) => i.status === 'confirmed' || i.status === 'pending')
    .sort((a, b) => {
      const so = STATUS_META[a.status].order - STATUS_META[b.status].order
      if (so !== 0) return so
      const da = a.latest?.confirmed_date || a.latest?.breakout_date || ''
      const db = b.latest?.confirmed_date || b.latest?.breakout_date || ''
      return db.localeCompare(da)
    })

  const confirmedCount = items.filter((i) => i.status === 'confirmed').length
  const pendingCount = items.filter((i) => i.status === 'pending').length

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          등록 관심종목 중 상승흐름 <span className="text-green-600 dark:text-green-400 font-semibold">확정 {confirmedCount.toLocaleString()}</span>
          {' · '}
          <span className="text-amber-600 dark:text-amber-400 font-semibold">대기 {pendingCount.toLocaleString()}</span>
        </p>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="btn btn-outline btn-sm"
        >
          {isFetching ? '점검 중…' : '새로고침'}
        </button>
      </div>

      {isError ? (
        <p className="py-10 text-center text-sm text-red-500">점검에 실패했습니다. 잠시 후 다시 시도하세요.</p>
      ) : isLoading ? (
        <p className="py-10 text-center text-sm text-gray-400">불러오는 중…</p>
      ) : items.length === 0 ? (
        <div className="py-12 text-center bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">현재 상승흐름 확정·대기 종목이 없습니다</p>
          <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">종목 상세의 &lsquo;상승흐름&rsquo; 탭에서 알림을 켜면 감지 대상이 됩니다</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                <th className="text-left font-medium px-4 py-2.5">종목</th>
                <th className="text-center font-medium px-3 py-2.5">상태</th>
                <th className="text-right font-medium px-3 py-2.5">확정/돌파일</th>
                <th className="text-right font-medium px-4 py-2.5">돌파선</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const meta = STATUS_META[item.status]
                const date = item.latest?.confirmed_date || item.latest?.breakout_date
                return (
                  <tr key={item.ticker} className="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                    <td className="px-4 py-2.5">
                      <Link to={`/etf/${item.ticker}`} className="text-primary-600 dark:text-primary-400 hover:underline font-medium">
                        {item.name}
                      </Link>
                      <span className="ml-1.5 text-xs text-gray-400 tabular-nums">{item.ticker}</span>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${meta.cls}`}>
                        {meta.label}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-gray-600 dark:text-gray-300">{formatDate(date)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-600 dark:text-gray-300">{formatWon(item.latest?.breakout_level)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
