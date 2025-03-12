export interface StrategyData {
    stock_id: string;
    strategy: string;
    signal: string;
    hybrid_score: number;
    signals: { [key: string]: number };
    optimized_weights: { [key: string]: number };
    risk_metrics: { [key: string]: number };
    news_impact: number;
  }