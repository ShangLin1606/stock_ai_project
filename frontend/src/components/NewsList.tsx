import React from 'react';
import { NewsItem } from '../types/news';

interface NewsListProps {
  news: NewsItem[];
}

const NewsList: React.FC<NewsListProps> = ({ news }) => {
  if (!news.length) return <p>無新聞可顯示</p>;

  return (
    <div className="news-list">
      {news.map((item, index) => (
        <div key={index} className="news-item card">
          <h3>{item.title}</h3>
          <p><strong>日期:</strong> {item.date}</p>
          <p>{item.outline}</p>
          <p><strong>情緒:</strong> {item.sentiment}</p>
          <p><strong>標籤:</strong> {item.tags.join(', ')}</p>
        </div>
      ))}
    </div>
  );
};

export default NewsList;