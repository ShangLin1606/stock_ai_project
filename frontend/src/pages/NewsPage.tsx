import React, { useState, useEffect } from 'react';
import NewsSearch from '../components/NewsSearch';
import NewsList from '../components/NewsList';
import { searchNews } from '../api';
import { NewsItem } from '../types/news';
import { logUserAction } from '../analytics';

const NewsPage: React.FC = () => {
  const [newsData, setNewsData] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    logUserAction('page_view', { page: 'news' });
  }, []);

  const handleSearch = async (stockId: string, query: string, date: string, sentiment: string, tags: string) => {
    setLoading(true);
    setError(null);
    try {
      const tagsArray = tags ? tags.split(',').map(t => t.trim()) : undefined;
      const data = await searchNews(stockId, query, date, sentiment || undefined, tagsArray);
      setNewsData(data);
      logUserAction('search', { stock_id: stockId, query, date, sentiment, tags, type: 'news' });
    } catch (err) {
      setError('無法獲取新聞，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="news-page">
      <NewsSearch onSearch={handleSearch} />
      {loading && <p>正在載入...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <NewsList news={newsData} />
    </div>
  );
};

export default NewsPage;