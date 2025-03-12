import React, { useState } from 'react';
import { format } from 'date-fns';

interface StockSearchProps {
  onSearch: (stockId: string, startDate: string, endDate: string) => void;
}

const StockSearch: React.FC<StockSearchProps> = ({ onSearch }) => {
  const [stockId, setStockId] = useState('');
  const [startDate, setStartDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(new Date(), 'yyyy-MM-dd'));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (stockId) {
      onSearch(stockId, startDate, endDate);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="stock-search">
      <input
        type="text"
        value={stockId}
        onChange={(e) => setStockId(e.target.value)}
        placeholder="輸入股票代碼 (如 0050)"
      />
      <input
        type="date"
        value={startDate}
        onChange={(e) => setStartDate(e.target.value)}
      />
      <input
        type="date"
        value={endDate}
        onChange={(e) => setEndDate(e.target.value)}
      />
      <button type="submit">查詢</button>
    </form>
  );
};

export default StockSearch;