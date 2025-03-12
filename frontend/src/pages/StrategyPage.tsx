import React, { useState, useEffect } from 'react';
import StockSearch from '../components/StockSearch';
import StrategyDisplay from '../components/StrategyDisplay';
import { fetchStrategy } from '../api';
import { StrategyData } from '../types/strategy';
import { logUserAction } from '../analytics';

const StrategyPage: React.FC = () => {
  const [strategyData, setStrategyData] = useState<StrategyData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    logUserAction('page_view', { page: 'strategy' });
  }, []);

  const handleSearch = async (stockId: string, startDate: string, endDate: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStrategy(stockId, startDate, endDate);
      setStrategyData(data);
      logUserAction('search', { stock_id: stockId, start_date: startDate, end_date: endDate, type: 'strategy' });
    } catch (err) {
      setError('無法獲取策略，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="strategy-page">
      <StockSearch onSearch={handleSearch} />
      {loading && <p>正在載入...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <StrategyDisplay data={strategyData} />
    </div>
  );
};

export default StrategyPage;