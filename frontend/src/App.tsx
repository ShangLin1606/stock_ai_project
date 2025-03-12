import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import StockQuery from './pages/StockQuery';
import ReportPage from './pages/ReportPage';
import StrategyPage from './pages/StrategyPage';
import NewsPage from './pages/NewsPage';

const App: React.FC = () => {
  return (
    <div className="app">
      <header className="app-header">
        <h1>股票分析平台</h1>
        <nav>
          <Link to="/" className="nav-link">股價查詢</Link>
          <Link to="/reports" className="nav-link">報告</Link>
          <Link to="/strategies" className="nav-link">策略</Link>
          <Link to="/news" className="nav-link">新聞</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<StockQuery />} />
          <Route path="/reports" element={<ReportPage />} />
          <Route path="/strategies" element={<StrategyPage />} />
          <Route path="/news" element={<NewsPage />} />
        </Routes>
      </main>
    </div>
  );
};

export default App;