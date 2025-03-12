import React from 'react';
import { ReportData } from '../types/report';

interface ReportDisplayProps {
  data: ReportData | null;
}

const ReportDisplay: React.FC<ReportDisplayProps> = ({ data }) => {
  if (!data) return <p>無報告可顯示</p>;

  return (
    <div className="card">
      <h2>投資報告</h2>
      <p><strong>股票代碼:</strong> {data.stock_id}</p>
      <p><strong>期間:</strong> {data.period}</p>
      <pre>{data.summary}</pre>
    </div>
  );
};

export default ReportDisplay;