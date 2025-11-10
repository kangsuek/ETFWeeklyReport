import { useState, useEffect, memo } from 'react';
import { subDays, subMonths, format, isAfter, differenceInDays } from 'date-fns';

/**
 * DateRangeSelector - 차트 데이터 기간 선택 컴포넌트
 *
 * @param {Object} props
 * @param {Function} props.onDateRangeChange - 날짜 범위 변경 콜백 함수
 * @param {string} props.defaultRange - 기본 범위 ('7d', '1m', '3m', 'custom')
 */
const DateRangeSelector = memo(function DateRangeSelector({ onDateRangeChange, defaultRange = '7d' }) {
  const [selectedRange, setSelectedRange] = useState(defaultRange);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [error, setError] = useState('');

  // 프리셋 버튼 클릭 핸들러
  const handlePresetClick = (range) => {
    setSelectedRange(range);
    setError('');

    const today = new Date();
    let calculatedStartDate;

    switch (range) {
      case '7d':
        calculatedStartDate = subDays(today, 7);
        break;
      case '1m':
        calculatedStartDate = subMonths(today, 1);
        break;
      case '3m':
        calculatedStartDate = subMonths(today, 3);
        break;
      default:
        return;
    }

    const formattedStartDate = format(calculatedStartDate, 'yyyy-MM-dd');
    const formattedEndDate = format(today, 'yyyy-MM-dd');

    setStartDate(formattedStartDate);
    setEndDate(formattedEndDate);

    onDateRangeChange({
      startDate: formattedStartDate,
      endDate: formattedEndDate,
      range
    });
  };

  // 커스텀 날짜 변경 핸들러
  const handleCustomDateChange = (type, value) => {
    if (type === 'start') {
      setStartDate(value);
    } else {
      setEndDate(value);
    }
  };

  // 커스텀 날짜 적용
  const applyCustomRange = () => {
    if (!startDate || !endDate) {
      setError('시작 날짜와 종료 날짜를 모두 입력해주세요.');
      return;
    }

    const start = new Date(startDate);
    const end = new Date(endDate);

    // 날짜 검증: startDate <= endDate
    if (isAfter(start, end)) {
      setError('시작 날짜는 종료 날짜보다 이전이어야 합니다.');
      return;
    }

    // 최대 범위 검증: 1년 (365일)
    const daysDiff = differenceInDays(end, start);
    if (daysDiff > 365) {
      setError('최대 조회 기간은 1년(365일)입니다.');
      return;
    }

    setError('');
    setSelectedRange('custom');

    onDateRangeChange({
      startDate,
      endDate,
      range: 'custom'
    });
  };

  // 초기 기본값 설정
  useEffect(() => {
    handlePresetClick(defaultRange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const presetButtons = [
    { label: '7일', value: '7d' },
    { label: '1개월', value: '1m' },
    { label: '3개월', value: '3m' },
    { label: '커스텀', value: 'custom' }
  ];

  return (
    <div className="date-range-selector bg-white rounded-lg shadow p-4 mb-4">
      {/* 프리셋 버튼 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
        {presetButtons.map(({ label, value }) => (
          <button
            key={value}
            onClick={() => value === 'custom' ? setSelectedRange('custom') : handlePresetClick(value)}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              selectedRange === value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      {/* 커스텀 날짜 선택기 */}
      {selectedRange === 'custom' && (
        <div className="border-t pt-4 mt-2">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="startDate" className="block text-sm font-medium text-gray-700 mb-1">
                시작 날짜
              </label>
              <input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => handleCustomDateChange('start', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label htmlFor="endDate" className="block text-sm font-medium text-gray-700 mb-1">
                종료 날짜
              </label>
              <input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => handleCustomDateChange('end', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {error && (
            <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <button
            onClick={applyCustomRange}
            className="mt-3 w-full md:w-auto px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            type="button"
          >
            적용
          </button>
        </div>
      )}

      {/* 현재 선택된 기간 표시 */}
      {startDate && endDate && selectedRange !== 'custom' && (
        <div className="mt-3 text-sm text-gray-600">
          선택된 기간: {startDate} ~ {endDate}
        </div>
      )}
    </div>
  );
})

export default DateRangeSelector;
