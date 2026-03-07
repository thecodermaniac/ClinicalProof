const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';

export interface Paper {
  pmid: string;
  title: string;
  abstract: string;
  authors: string[];
  journal: string;
  pubdate: string;
  doi?: string;
  fetched_at: string;
}

export interface SummaryResponse {
  summaryId: string;
  pmid: string;
  summaries: {
    short: string;
    medium: string;
    long: string;
  };
  created_at: string;
  cached: boolean;
  model: string;
}

export interface HashResponse {
  hash: string;
  pmid: string;
  summaryId: string;
  created_at: string;
  verification_url: string;
  blockchain?: {
    network: string;
    transactionHash: string;
    timestamp: string;
  };
}

export interface VerificationResponse {
  verified: boolean;
  hash: string;
  pmid?: string;
  summaryId?: string;
  paper_title?: string;
  created_at?: string;
  verification_count?: number;
  message?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  async fetchPaper(pmid: string): Promise<Paper> {
    const response = await fetch(`${this.baseUrl}/fetch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ pmid }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to fetch paper');
    }

    const data = await response.json();
    return data.data;
  }

  async generateSummary(pmid: string, type: 'short' | 'medium' | 'long' | 'all' = 'all'): Promise<SummaryResponse> {
    const response = await fetch(`${this.baseUrl}/summarize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ pmid, type }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to generate summary');
    }

    return response.json();
  }

  async createHash(params: {
    pmid: string;
    summaryId: string;
    title: string;
    summary: string;
    secretKey?: string;
    storeOnChain?: boolean;
  }): Promise<HashResponse> {
    const response = await fetch(`${this.baseUrl}/hash`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to create hash');
    }

    return response.json();
  }

  async verifyHash(hash: string): Promise<VerificationResponse> {
    const response = await fetch(`${this.baseUrl}/verify/${hash}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return { verified: false, hash, message: 'Hash not found' };
      }
      const error = await response.json();
      throw new Error(error.message || 'Failed to verify hash');
    }

    return response.json();
  }

  async getPaperByPMID(pmid: string): Promise<Paper> {
    const response = await fetch(`${this.baseUrl}/fetch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ pmid }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to get paper');
    }

    const data = await response.json();
    return data.data;
  }
}

export const apiClient = new ApiClient();