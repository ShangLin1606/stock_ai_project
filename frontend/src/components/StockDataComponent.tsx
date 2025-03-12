import React from 'react';
import { StockData } from '../types/stock';

interface StockDataProps {
  data: StockData | null;
}

const StockDataComponent: React.FC<StockDataProps> = ({ data }) => {
  // 若 data 為 null 或所有子項均為空，才顯示「無數據」
  if (!data || (!data.daily_prices.length && !data.sentiments.length && !Object.keys(data.risk_metrics).length && !data.latest_price)) {
    return <p>無數據可顯示</p>;
  }

  return (
    <div className="stock-data">
      <div className="card">
        <h2>最新股價</h2>
        {data.latest_price ? (
          <ul>
            <li>日期: {data.latest_price.date}</li>
            <li>開盤價: {data.latest_price.open}</li>
            <li>最高價: {data.latest_price.high}</li>
            <li>最低價: {data.latest_price.low}</li>
            <li>收盤價: {data.latest_price.close}</li>
            <li>成交量: {data.latest_price.volume}</li>
          </ul>
        ) : (
          <p>無最新股價數據</p>
        )}
      </div>
      <div className="card">
        <h2>情緒數據</h2>
        {data.sentiments && data.sentiments.length > 0 ? (
          <ul>
            {data.sentiments.slice(0, 3).map((item, index) => (
              <li key={index}>{item.text} - {item.sentiment}</li>
            ))}
          </ul>
        ) : (
          <p>無情緒數據</p>
        )}
      </div>
      <div className="card">
        <h2>風險指標</h2>
        {data.risk_metrics && Object.keys(data.risk_metrics).length > 0 ? (
          <ul>
            <li>VaR: {data.risk_metrics.VaR?.toFixed(2) ?? 'N/A'}</li>
            <li>Sharpe: {data.risk_metrics.Sharpe?.toFixed(2) ?? 'N/A'}</li>
            <li>Beta: {data.risk_metrics.Beta?.toFixed(2) ?? 'N/A'}</li>
            <li>Max Drawdown: {data.risk_metrics.MaxDrawdown?.toFixed(2) ?? 'N/A'}</li>
          </ul>
        ) : (
          <p>無風險指標</p>
        )}
      </div>
    </div>
  );
};

export default StockDataComponent;