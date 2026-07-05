import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { alertApi } from '../../services/api'
import { SIGNAL_KINDS } from '../../config/signalKinds'

const STATUS_META = {
  confirmed: { label: '확정', order: 0 },
  pending: { label: '대기', order: 1 },
}

const formatMMDD = (iso) => {
  if (!iso) return ''
  const [, m, d] = String(iso).slice(0, 10).split('-')
  return m && d ? `${m}/${d}` : String(iso).slice(0, 10)
}

/**
 * 관심종목(등록 종목) 상승/하락 흐름 일괄 점검 — 버튼을 누르면 저장된 데이터로
 * 현재 상태를 읽기 전용으로 평가해 확정·대기 종목만 강조한다 (DB 미변경).
 */
export default function SignalWatchlistCheck({ direction }) {
  const cfg = SIGNAL_KINDS[direction]
  const scan = useMutation({
    mutationFn: async () => {
      const res = await alertApi.scanWatchlist(cfg.kind)
      return res.data
    },
  })

  const items = scan.data?.items ?? []
  const highlighted = items
    .filter(i => i.status === 'confirmed' || i.status === 'pending')
    .sort((a, b) => STATUS_META[a.status].order - STATUS_META[b.status].order)
  const confirmedCount = items.filter(i => i.status === 'confirmed').length
  const pendingCount = items.filter(i => i.status === 'pending').length

  return (
    <section aria-label={`관심종목 ${cfg.label} 점검`} className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">관심종목 {cfg.label} 점검</h2>
        <button
          onClick={() => scan.mutate()}
          disabled={scan.isPending}
          className="text-xs px-2.5 py-1 rounded-md bg-primary-500 text-white hover:bg-primary-600 disabled:opacity-50 transition-colors font-medium"
        >
          {scan.isPending ? '점검 중…' : '일괄 점검'}
        </button>
      </div>

      {scan.isError && (
        <p className="text-xs text-red-500">점검에 실패했습니다. 잠시 후 다시 시도하세요.</p>
      )}

      {scan.isSuccess && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700/50 text-xs text-gray-500 dark:text-gray-400">
            총 {items.length.toLocaleString()}종목 점검 · 확정 {confirmedCount.toLocaleString()} · 대기 {pendingCount.toLocaleString()}
          </div>
          {highlighted.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
              현재 {cfg.label} 확정·대기 종목이 없습니다
            </p>
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-700/50">
              {highlighted.map(item => (
                <li key={item.ticker}>
                  <Link
                    to={`/etf/${item.ticker}`}
                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                  >
                    <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${item.status === 'confirmed' ? cfg.dot : 'bg-amber-500'}`} />
                    <span className="min-w-0 flex-1 text-sm text-gray-800 dark:text-gray-200 truncate">
                      {item.name} <span className="text-gray-400">{item.ticker}</span>
                    </span>
                    <span className={`text-xs font-semibold ${item.status === 'confirmed' ? cfg.accent : 'text-amber-600 dark:text-amber-400'}`}>
                      {STATUS_META[item.status].label}
                      {item.status === 'confirmed' && item.latest?.confirmed_date && (
                        <span className="font-normal text-gray-400"> ({formatMMDD(item.latest.confirmed_date)})</span>
                      )}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  )
}

SignalWatchlistCheck.propTypes = {
  direction: PropTypes.oneOf(['up', 'down']).isRequired,
}
