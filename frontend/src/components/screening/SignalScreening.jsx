import { useState } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { alertApi, scannerApi } from '../../services/api'
import { SIGNAL_KINDS } from '../../config/signalKinds'
import { describeFilters, describeSort } from '../../config/screeningOptions'

// 백엔드 SIGNAL_BATCH_SCAN_MAX와 동일 — 초과 요청은 백엔드에서도 잘린다.
const BATCH_MAX = 50
const BATCH_DEFAULT = 30

const STATUS_META = {
  confirmed: { label: '확정', cls: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300', order: 0 },
  pending: { label: '대기', cls: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300', order: 1 },
}

const formatDate = (iso) => {
  if (!iso) return '-'
  const [, m, d] = String(iso).slice(0, 10).split('-')
  return m && d ? `${m}/${d}` : String(iso).slice(0, 10)
}

const formatWon = (v) => (v == null ? '-' : `${Math.round(v).toLocaleString()}원`)

/**
 * 종목 발굴 상승/하락 흐름 탭.
 *
 * - 관심종목 모드: 이미 이력이 있는 등록 종목을 즉시 판정 (읽기 전용, 빠름)
 * - 조건검색 모드: 현재 조건검색 결과 상위 N개의 이력을 즉시 수집 후 판정
 *   (실제 알고리즘 그대로. 종목당 수집이 필요해 다소 시간이 걸린다)
 */
export default function SignalScreening({ direction, filters }) {
  const cfg = SIGNAL_KINDS[direction]
  const [mode, setMode] = useState('watchlist')
  const [limit, setLimit] = useState(BATCH_DEFAULT)

  const watchlist = useQuery({
    queryKey: ['signalScreening', cfg.kind],
    queryFn: async () => {
      const res = await alertApi.scanWatchlist(cfg.kind)
      return res.data
    },
    enabled: mode === 'watchlist',
    staleTime: 60_000,
  })

  const batch = useMutation({
    mutationFn: async () => {
      const params = {}
      for (const [key, val] of Object.entries(filters ?? {})) {
        if (val !== undefined) params[key] = val
      }
      params.page = 1
      params.page_size = limit
      const found = await scannerApi.search(params)
      const tickers = (found.data?.items ?? []).map((i) => i.ticker)
      const res = await alertApi.scanBatch(tickers, cfg.direction, limit)
      return res.data
    },
  })

  const source = mode === 'watchlist' ? watchlist : batch
  const isBusy = mode === 'watchlist' ? watchlist.isFetching : batch.isPending
  const rows = source.data?.items ?? []

  const items = rows
    .filter((i) => i.status === 'confirmed' || i.status === 'pending')
    .sort((a, b) => {
      const so = STATUS_META[a.status].order - STATUS_META[b.status].order
      if (so !== 0) return so
      const da = a.latest?.confirmed_date || a.latest?.breakout_date || ''
      const db = b.latest?.confirmed_date || b.latest?.breakout_date || ''
      return db.localeCompare(da)
    })

  const count = (s) => rows.filter((i) => i.status === s).length
  const skipped = count('insufficient_data') + count('error')
  const levelLabel = direction === 'up' ? '돌파선' : '이탈선'
  const breakLabel = direction === 'up' ? '돌파일' : '이탈일'
  const hasRun = mode === 'watchlist' ? watchlist.isSuccess : batch.isSuccess

  return (
    <div className="space-y-3">
      {/* 대상 선택 */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          {[
            { id: 'watchlist', label: '등록 관심종목' },
            { id: 'screen', label: '조건검색 결과' },
          ].map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                mode === m.id
                  ? 'bg-white dark:bg-gray-700 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        {mode === 'screen' && (
          <div className="flex items-center gap-1.5">
            <label htmlFor="batch-limit" className="text-xs text-gray-500 dark:text-gray-400">상위</label>
            <input
              id="batch-limit"
              type="number"
              min={1}
              max={BATCH_MAX}
              value={limit}
              onChange={(e) => {
                const n = parseInt(e.target.value, 10)
                setLimit(Number.isNaN(n) ? BATCH_DEFAULT : Math.min(Math.max(n, 1), BATCH_MAX))
              }}
              className="w-16 px-2 py-1 text-sm text-right tabular-nums border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
            <span className="text-xs text-gray-500 dark:text-gray-400">개 (최대 {BATCH_MAX})</span>
          </div>
        )}

        <button
          onClick={() => (mode === 'watchlist' ? watchlist.refetch() : batch.mutate())}
          disabled={isBusy}
          className="btn btn-outline btn-sm ml-auto"
        >
          {isBusy ? '점검 중…' : mode === 'watchlist' ? '새로고침' : '점검 실행'}
        </button>
      </div>

      {mode === 'screen' && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-800/40 p-3 space-y-2">
          <div className="flex items-center gap-1.5 flex-wrap" aria-label="적용된 조건검색 필터">
            <span className="text-xs text-gray-500 dark:text-gray-400">적용 조건</span>
            {describeFilters(filters).map((chip) => (
              <span
                key={chip.key}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-200"
              >
                {chip.label}
              </span>
            ))}
            <span className="text-xs text-gray-500 dark:text-gray-400">
              · {describeSort(filters)} 상위 <strong className="tabular-nums text-gray-700 dark:text-gray-200">{limit.toLocaleString()}</strong>개
            </span>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            &lsquo;조건 검색&rsquo; 탭에서 설정한 조건이 그대로 적용됩니다(페이지는 무시하고 상위 N개).
            종목당 약 2초 소요되며, 수집된 가격·수급 이력은 저장됩니다.
          </p>
        </div>
      )}

      {/* 요약 */}
      {hasRun && !isBusy && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          총 {rows.length.toLocaleString()}종목 점검 ·{' '}
          <span className={`${cfg.accent} font-semibold`}>확정 {count('confirmed').toLocaleString()}</span>
          {' · '}
          <span className="text-amber-600 dark:text-amber-400 font-semibold">대기 {count('pending').toLocaleString()}</span>
          {skipped > 0 && (
            <span className="text-gray-400"> · 판정 불가 {skipped.toLocaleString()}</span>
          )}
        </p>
      )}

      {source.isError ? (
        <p className="py-10 text-center text-sm text-red-500">점검에 실패했습니다. 잠시 후 다시 시도하세요.</p>
      ) : isBusy ? (
        <p className="py-10 text-center text-sm text-gray-400">
          {mode === 'screen' ? `${limit.toLocaleString()}개 종목 이력 수집·판정 중… (수십 초 소요)` : '불러오는 중…'}
        </p>
      ) : !hasRun ? (
        <div className="py-12 text-center bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">&lsquo;점검 실행&rsquo;을 누르면 조건검색 결과를 점검합니다</p>
        </div>
      ) : items.length === 0 ? (
        <div className="py-12 text-center bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">현재 {cfg.label} 확정·대기 종목이 없습니다</p>
          {mode === 'watchlist' && (
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">종목 상세의 &lsquo;{cfg.label}&rsquo; 탭에서 알림을 켜면 감지 대상이 됩니다</p>
          )}
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                <th className="text-left font-medium px-4 py-2.5">종목</th>
                <th className="text-center font-medium px-3 py-2.5">상태</th>
                <th className="text-right font-medium px-3 py-2.5">확정/{breakLabel}</th>
                <th className="text-right font-medium px-4 py-2.5">{levelLabel}</th>
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

SignalScreening.propTypes = {
  direction: PropTypes.oneOf(['up', 'down']).isRequired,
  filters: PropTypes.object,
}
