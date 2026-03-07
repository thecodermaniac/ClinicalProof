export interface PubMedPaper {
  pmid: string;
  title: string;
  abstract: string;
  authors: string[];
  journal: string;
  year: string;
  doi?: string;
  meshTerms?: string[];
}

export interface PubMedSearchResult {
  id: string;
  title: string;
  authors: string[];
  journal: string;
  year: string;
  relevanceScore?: number;
}

export interface PubMedApiResponse {
  papers: PubMedPaper[];
  totalResults: number;
  queryId?: string;
}