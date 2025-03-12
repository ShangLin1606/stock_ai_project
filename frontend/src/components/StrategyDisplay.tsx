import React from 'react';
import { StrategyData } from '../types/strategy';

interface StrategyDisplayProps {
  data: StrategyData | null;
}

const StrategyDisplay: React.FC<StrategyDisplayProps> = ({ data }) => {
  if (!data) return <p>無策略可顯示</p>;

  return (
    <div className="card">
      <h2>交易策略</h2>
      <p><strong>股票代碼:</strong> {data.stock_id}</p>
      <p><strong>策略:</strong> {data.strategy}</p>
      <p><strong>信號:</strong> {data.signal}</p>
      <p><strong>混合評分:</strong> {data.hybrid_score.toFixed(2)}</p>
      <p><strong>新聞影響:</strong> {data.news_impact.toFixed(2)}</p>
      <h3>風險指標</h3>
      {data.risk_metrics && (
        <ul>
          <li>VaR: {data.risk_metrics.VaR.toFixed(2)}</li>
          <li>Sharpe: {data.risk_metrics.Sharpe.toFixed(2)}</li>
        </ul>
      )}
    </div>
  );
};

export default StrategyDisplay;