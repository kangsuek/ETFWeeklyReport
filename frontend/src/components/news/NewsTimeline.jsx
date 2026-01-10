import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import PropTypes from 'prop-types'
import { newsApi } from '../../services/api'

/**
 * NewsTimeline 컴포넌트
 * 종목 관련 뉴스를 타임라인 형태로 표시
 * 
 * @param {string} ticker - 종목 티커
 */
const NewsTimeline = ({ ticker }) => {
  const [limit, setLimit] = useState(10)

  const { data, isLoading, error } = useQuery({
    queryKey: ['news', ticker, limit],
    queryFn: async () => {
      const response = await newsApi.getByTicker(ticker, { days: 7, limit })
      return response.data
    },
    staleTime: 5 * 60 * 1000, // 5분
  })

  // 날짜별로 그룹핑 (hooks는 항상 먼저 호출되어야 함)
  const groupedNews = useMemo(() => {
    if (!data || data.length === 0) return {}

    const groups = {}
    data.forEach((news) => {
      // 날짜 유효성 검사 추가
      if (!news.date) return

      try {
        const date = new Date(news.date)
        // Invalid Date 체크
        if (isNaN(date.getTime())) return

        const dateKey = format(date, 'yyyy-MM-dd')
        if (!groups[dateKey]) {
          groups[dateKey] = []
        }
        groups[dateKey].push(news)
      } catch (error) {
        // Invalid date - skip this news item
      }
    })
    return groups
  }, [data])

  // 관련도 점수 색상 반환
  const getRelevanceColor = (score) => {
    if (score >= 0.8) return 'bg-green-500'
    if (score >= 0.5) return 'bg-yellow-500'
    return 'bg-gray-400'
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-2"></div>
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <p>뉴스를 불러오는데 실패했습니다</p>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        <p>최근 뉴스가 없습니다</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {Object.entries(groupedNews).map(([date, newsItems]) => (
        <div key={date}>
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            {format(new Date(date), 'yyyy년 MM월 dd일')}
          </h4>
          <div className="space-y-3 ml-4 border-l-2 border-gray-200 dark:border-gray-700 pl-4">
            {newsItems.map((news, index) => (
              <div
                key={news.url || `${news.date}-${index}`}
                className="bg-white dark:bg-gray-800 rounded-lg p-4 hover:shadow-md transition-shadow border border-gray-100 dark:border-gray-700"
              >
                <a
                  href={news.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-base font-medium text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                >
                  {news.title}
                </a>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
                  <span>{news.source}</span>
                  <span>•</span>
                  <span>
                    {news.date ? (() => {
                      try {
                        const date = new Date(news.date)
                        return isNaN(date.getTime()) ? '-' : format(date, 'HH:mm')
                      } catch {
                        return '-'
                      }
                    })() : '-'}
                  </span>
                  {news.relevance_score && (
                    <>
                      <span>•</span>
                      <div className="flex items-center gap-1">
                        <span>관련도</span>
                        <div className="w-20 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${getRelevanceColor(news.relevance_score)}`}
                            style={{ width: `${news.relevance_score * 100}%` }}
                          ></div>
                        </div>
                        <span>{(news.relevance_score * 100).toFixed(0)}%</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

NewsTimeline.propTypes = {
  ticker: PropTypes.string.isRequired,
}

export default NewsTimeline

