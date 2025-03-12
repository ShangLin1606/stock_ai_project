import React, { useState, useEffect } from 'react';
import StockSearch from '../components/StockSearch';
import ReportDisplay from '../components/ReportDisplay';
import { fetchReport } from '../api';
import { ReportData } from '../types/report';
import { logUserAction } from '../analytics';

const ReportPage: React.FC = () => {
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    logUserAction('page_view', { page: 'report' });
  }, []);

  const handleSearch = async (stockId: string, startDate: string, endDate: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReport(stockId, startDate, endDate);
      setReportData(data);
      logUserAction('search', { stock_id: stockId, start_date: startDate, end_date: endDate, type: 'report' });
    } catch (err) {
      setError('無法獲取報告，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="report-page">
      <StockSearch onSearch={handleSearch} />
      {loading && <p>正在載入...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <ReportDisplay data={reportData} />
    </div>
  );
};

export default ReportPage;