import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { alertApi } from '../services/api'

// 신호는 16:40 스캔·앱 시작 시에만 생기므로 저빈도(10분) 폴링으로 충분.
const POLL_INTERVAL_MS = 10 * 60 * 1000

/**
 * 상승/하락 흐름 확정 알림 이력·미읽음 폴링 훅 (kind: 'uptrend' | 'downtrend').
 *
 * 기존 AlertContext(벨/토스트, 3종 상태 알림)와 완전히 분리된 서버 이력 기반이다.
 */
export function useSignalAlerts(kind = 'uptrend') {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['signalAlerts', kind],
    queryFn: async () => {
      const res = await alertApi.getFlowAlerts(kind)
      return res.data
    },
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: true,
    staleTime: POLL_INTERVAL_MS,
  })

  const markRead = useCallback(async () => {
    await alertApi.markFlowRead(kind)
    await queryClient.invalidateQueries({ queryKey: ['signalAlerts', kind] })
  }, [queryClient, kind])

  return {
    items: data?.items ?? [],
    unreadCount: data?.unread_count ?? 0,
    isLoading,
    markRead,
  }
}

export default useSignalAlerts
