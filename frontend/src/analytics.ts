import { Client } from '@elastic/elasticsearch';

const esClient = new Client({ node: 'http://localhost:9200' });

export const logUserAction = async (action: string, data: any): Promise<void> => {
  try {
    await esClient.index({
      index: 'user_actions',
      body: {
        action,
        data,
        timestamp: new Date().toISOString(),
      },
    });

    await fetch('http://localhost:8000/log-action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, data }),
    });
  } catch (error) {
    console.error('Error logging user action:', error);
  }
};