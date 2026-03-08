'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';

interface Summary {
  summaryId: string;
  pmid: string;
  short: string;
  medium: string;
  long: string;
  created_at: string;
  model: string;
  verified_on_blockchain?: boolean;
  blockchain_hash?: string;
}

export default function SummariesPage() {
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest'>('newest');
  const [selectedSummary, setSelectedSummary] = useState<Summary | null>(null);

  useEffect(() => {
    loadSummaries();
  }, []);

  const loadSummaries = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/summaries`);
      if (!response.ok) throw new Error('Failed to load summaries');
      const data = await response.json();
      setSummaries(data.summaries || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load summaries');
    } finally {
      setLoading(false);
    }
  };

  const filteredSummaries = summaries
    .filter(s => 
      s.pmid.includes(filter) || 
      s.short.toLowerCase().includes(filter.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === 'newest') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      } else {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
    });

  const truncateText = (text: string, maxLength: number = 100) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto py-4 px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-8">
              <Link href="/" className="text-2xl font-bold text-blue-600">
                MedHash
              </Link>
              <nav className="flex gap-4">
                <Link 
                  href="/" 
                  className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-lg"
                >
                  Home
                </Link>
                <Link 
                  href="/summaries" 
                  className="text-blue-600 bg-blue-50 px-3 py-2 rounded-lg font-medium"
                >
                  My Summaries
                </Link>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">My Summaries</h1>
          <p className="text-gray-600 mt-2">
            View and manage all your generated paper summaries
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm border p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <input
                type="text"
                placeholder="Filter by PMID or content..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm  text-gray-700"
              />
            </div>
            <div className="flex gap-2 text-sm text-gray-600">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'newest' | 'oldest')}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
              </select>
              <button
                onClick={loadSummaries}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                ↻ Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Summary List */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Loading summaries...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-800 font-semibold">❌ Error</p>
            <p className="text-gray-600 mt-2">{error}</p>
            <button
              onClick={loadSummaries}
              className="mt-4 px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Try Again
            </button>
          </div>
        ) : filteredSummaries.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
            <p className="text-gray-500 text-lg">No summaries found</p>
            <p className="text-gray-400 mt-2">
              Generate your first summary by fetching a paper on the home page
            </p>
            <Link
              href="/"
              className="mt-6 inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Go to Home
            </Link>
          </div>
        ) : (
          <div className="grid gap-4">
            {filteredSummaries.map((summary) => (
              <div
                key={summary.summaryId}
                className="bg-white rounded-lg shadow-sm border hover:shadow-md transition-shadow"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <span className="text-sm font-mono text-gray-500">
                        PMID: {summary.pmid}
                      </span>
                      <h3 className="text-lg font-semibold text-gray-900 mt-1">
                        {truncateText(summary.short, 80)}
                      </h3>
                    </div>
                    {summary.verified_on_blockchain && (
                      <span className="px-3 py-1 bg-green-100 text-green-800 text-sm rounded-full flex items-center gap-1">
                        <span>✅</span> Verified
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                    <span className="flex items-center gap-1">
                      📅 {formatDistanceToNow(new Date(summary.created_at), { addSuffix: true })}
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      🤖 {summary.model}
                    </span>
                  </div>

                  <div className="flex gap-2">
                    <Link
                      href={`/summaries/${summary.summaryId}`}
                      className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
                    >
                      View Full Summary
                    </Link>
                    {summary.blockchain_hash && (
                      <a
                        href={`https://sepolia.etherscan.io/tx/${summary.blockchain_hash}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-4 py-2 bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        View on Etherscan
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto py-6 px-4 text-center text-sm text-gray-500">
          <p>⚠️ For educational purposes only. Always consult a healthcare provider.</p>
        </div>
      </footer>
    </div>
  );
}