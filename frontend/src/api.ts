import axios from 'axios';
import { StockData } from './types/stock';
import { ReportData } from './types/report';
import { StrategyData } from './types/strategy';
import { NewsItem } from './types/news';

const API_URL = 'http://localhost:8000';

export const fetchStockData = async (stockId: string, startDate: string, endDate: string): Promise<StockData> => {
  const response = await axios.get(`${API_URL}/stocks/${stockId}`, {
    params: { start_date: startDate, end_date: endDate }
  });
  return response.data;
};

export const fetchReport = async (stockId: string, startDate: string, endDate: string): Promise<ReportData> => {
  const response = await axios.get(`${API_URL}/reports/${stockId}`, {
    params: { start_date: startDate, end_date: endDate }
  });
  return response.data;
};

export const fetchStrategy = async (stockId: string, startDate: string, endDate: string): Promise<StrategyData> => {
  const response = await axios.get(`${API_URL}/strategies/${stockId}`, {
    params: { start_date: startDate, end_date: endDate }
  });
  return response.data;
};

export const searchNews = async (
  stockId: string,
  query: string,
  date?: string,
  sentiment?: string,
  tags?: string[]
): Promise<NewsItem[]> => {
  const response = await axios.get(`${API_URL}/news/search`, {
    params: { stock_id: stockId, query, date, sentiment, tags: tags?.join(',') }
  });
  return response.data;
};