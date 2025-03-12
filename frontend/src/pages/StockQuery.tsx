import React, { useState, useEffect } from 'react';
import StockSearch from '../components/StockSearch';
import StockData from '../components/StockDataComponent';
import PriceChart from '../components/PriceChart';
import { fetchStockData } from '../api';
import { StockData as StockDataType } from '../types/stock';
import { logUserAction } from '../analytics';

const StockQuery: React.FC = () => {
  const [stockData, setStockData] = useState<StockDataType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    logUserAction('page_view', { page: 'stock_query' });
  }, []);

  const handleSearch = async (stockId: string, startDate: string, endDate: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStockData(stockId, startDate, endDate);
      setStockData(data);
      logUserAction('search', { stock_id: stockId, start_date: startDate, end_date: endDate });
    } catch (err) {
      setError('無法獲取股價數據，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stock-query">
      <StockSearch onSearch={handleSearch} />
      {loading && <p>正在載入...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {stockData && (
        <>
          <StockData data={stockData} />
          <PriceChart data={stockData} />
        </>
      )}
    </div>
  );
};

export default StockQuery;