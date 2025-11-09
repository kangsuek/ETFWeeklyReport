export default function ETFCardSkeleton() {
  return (
    <div className="card animate-pulse">
      {/* 헤더 */}
      <div className="mb-3">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1">
            <div className="h-5 bg-gray-200 rounded w-3/4 mb-2"></div>
          </div>
          <div className="h-6 w-12 bg-gray-200 rounded-full ml-2"></div>
        </div>
        <div className="h-4 bg-gray-200 rounded w-1/2"></div>
      </div>

      {/* 가격 정보 */}
      <div className="mb-4 py-3 border-t border-b border-gray-100">
        <div className="flex items-baseline justify-between mb-1">
          <div className="h-8 bg-gray-200 rounded w-24"></div>
          <div className="h-5 bg-gray-200 rounded w-16"></div>
        </div>
        <div className="flex justify-between">
          <div className="h-3 bg-gray-200 rounded w-20"></div>
          <div className="h-3 bg-gray-200 rounded w-20"></div>
        </div>
      </div>

      {/* 하단 */}
      <div className="flex justify-between">
        <div className="h-3 bg-gray-200 rounded w-16"></div>
        <div className="h-3 bg-gray-200 rounded w-20"></div>
      </div>
    </div>
  )
}
