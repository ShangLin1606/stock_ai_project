import React, { useState } from 'react';
import { format } from 'date-fns';

interface NewsSearchProps {
  onSearch: (stockId: string, query: string, date: string, sentiment: string, tags: string) => void;
}

const NewsSearch: React.FC<NewsSearchProps> = ({ onSearch }) => {
  const [stockId, setStockId] = useState('');
  const [query, setQuery] = useState('');
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [sentiment, setSentiment] = useState('');
  const [tags, setTags] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (stockId && query) {
      onSearch(stockId, query, date, sentiment, tags);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="news-search">
      <input
        type="text"
        value={stockId}
        onChange={(e) => setStockId(e.target.value)}
        placeholder="股票代碼 (如 0050)"
      />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="關鍵詞 (如 市場動態)"
      />
      <input
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value)}
      />
      <select value={sentiment} onChange={(e) => setSentiment(e.target.value)}>
        <option value="">所有情緒</option>
        <option value="positive">正向</option>
        <option value="negative">負向</option>
        <option value="neutral">中性</option>
      </select>
      <input
        type="text"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
        placeholder="標籤 (用逗號分隔，如 市場,ETF)"
      />
      <button type="submit">搜索</button>
    </form>
  );
};

export default NewsSearch;