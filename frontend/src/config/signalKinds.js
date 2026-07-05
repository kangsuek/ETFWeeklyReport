// 상승/하락 흐름 신호의 방향별 표시 설정 (컴포넌트 파라미터화용).
export const SIGNAL_KINDS = {
  up: {
    kind: 'uptrend',
    direction: 'up',
    label: '상승흐름',
    short: '상승',
    arrow: '▲',
    dot: 'bg-green-500',
    dotSoft: 'bg-green-400',
    accent: 'text-green-600 dark:text-green-400',
    badge: 'bg-green-500',
    chip: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300',
  },
  down: {
    kind: 'downtrend',
    direction: 'down',
    label: '하락흐름',
    short: '하락',
    arrow: '▼',
    dot: 'bg-rose-500',
    dotSoft: 'bg-rose-400',
    accent: 'text-rose-600 dark:text-rose-400',
    badge: 'bg-rose-500',
    chip: 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-300',
  },
}

export const KIND_LIST = [SIGNAL_KINDS.up, SIGNAL_KINDS.down]
