import React from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { StockData } from '../types/stock';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface PriceChartProps {
  data: StockData | null;
}

const PriceChart: React.FC<PriceChartProps> = ({ data }) => {
  if (!data || !data.daily_prices.length) return <p>無歷史價格數據可顯示</p>;

  const chartData = {
    labels: data.daily_prices.map(item => item.date),
    datasets: [
      {
        label: '收盤價',
        data: data.daily_prices.map(item => item.close),
        borderColor: '#1e3a8a',
        fill: false,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { position: 'top' as const },
      title: { display: true, text: `${data.stock_id} 歷史股價` },
    },
  };

  return (
    <div className="chart-container">
      <Line data={chartData} options={options} />
    </div>
  );
};

export default PriceChart;