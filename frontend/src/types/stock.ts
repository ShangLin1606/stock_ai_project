export interface StockData {
    stock_id: string;
    latest_price: {
      date: string;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    } | null;
    daily_prices: {
      date: string;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    }[];
    sentiments: {
      stock_id: string;
      date: string;
      text: string;
      sentiment: string;
      timestamp: string;
    }[];
    risk_metrics: {
      VaR: number;
      Sharpe: number;
      Beta: number;
      MaxDrawdown: number;
      Volatility: number;
      CVaR: number;
      Sortino: number;
      JensenAlpha: number;
      Treynor: number;
      StopLoss: number;
      DynamicPositionSizing: number;
      RiskParity: number;
    };
  }