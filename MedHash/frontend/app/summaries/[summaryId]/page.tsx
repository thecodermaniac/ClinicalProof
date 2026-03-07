'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { apiClient } from '@/src/lib/api/client';
import { format } from 'date-fns';

interface SummaryDetail {
  summary: {
    summaryId: string;
    pmid: string;
    short: string;
    medium: string;
    long: string;
    created_at: string;
    model: string;
  };
  paper: {
    title: string;
    authors: string[];
    journal: string;
    pubdate: string;
    doi: string;
  };
  blockchain?: {
    hash: string;
    verified_at: string;
    verification_count: number;
  };
}

export default function SummaryDetailPage() {
  const params = useParams();
  const summaryId = params.summaryId as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<SummaryDetail | null>(null);
  const [activeTab, setActiveTab] = useState<'short' | 'medium' | 'long'>('medium');

  useEffect(() => {
    loadSummary();
  }, [summaryId]);

  const loadSummary = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/summaries/${summaryId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        mode: 'cors', // Explicitly request CORS mode
        credentials: 'omit', // Don't send cookies
      });
      if (!response.ok) throw new Error('Failed to load summary');
      const data = await response.json();
      setDetail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load summary');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  const downloadAsPDF = () => {
    // Will implement PDF generation later
    alert('PDF download coming soon!');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading summary...</p>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-sm border p-8 max-w-md text-center">
          <p className="text-red-600 font-semibold text-lg">❌ Error</p>
          <p className="text-gray-600 mt-2">{error || 'Summary not found'}</p>
          <Link
            href="/summaries"
            className="mt-6 inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Summaries
          </Link>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'short', label: '⚡ Quick Summary', content: detail.summary.short },
    { id: 'medium', label: '📋 Standard Summary', content: detail.summary.medium },
    { id: 'long', label: '🔍 Detailed Analysis', content: detail.summary.long }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto py-4 px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-2xl font-bold text-blue-600">
              MedHash
            </Link>
            <span className="text-gray-300">/</span>
            <Link href="/summaries" className="text-gray-600 hover:text-blue-600">
              Summaries
            </Link>
            <span className="text-gray-300">/</span>
            <span className="text-gray-900 font-mono text-sm">
              {summaryId.substring(0, 8)}...
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto py-8 px-4">
        {/* Paper Info Card */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-3">
            {detail.paper.title}
          </h1>
          <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-3">
            <span>PMID: {detail.summary.pmid}</span>
            {detail.paper.doi && <span>DOI: {detail.paper.doi}</span>}
            <span>Published: {detail.paper.pubdate}</span>
          </div>
          {detail.paper.authors && detail.paper.authors.length > 0 && (
            <p className="text-sm text-gray-500">
              {detail.paper.authors.join(', ')}
            </p>
          )}
          <p className="text-sm text-gray-500 mt-2">
            {detail.paper.journal}
          </p>
        </div>

        {/* Blockchain Status Card */}
        {detail.blockchain && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-green-800 font-semibold mb-2">
              <span>✅</span>
              <span>Verified on Blockchain</span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Transaction Hash:</span>
                <p className="font-mono text-xs break-all mt-1">
                  {detail.blockchain.hash}
                </p>
              </div>
              <div>
                <span className="text-gray-600">Verified:</span>
                <p className="mt-1">
                  {format(new Date(detail.blockchain.verified_at), 'PPpp')}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Verified {detail.blockchain.verification_count} times
                </p>
              </div>
            </div>
            <a
              href={`https://sepolia.etherscan.io/tx/${detail.blockchain.hash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-3 text-sm text-blue-600 hover:underline"
            >
              View on Etherscan →
            </a>
          </div>
        )}

        {/* Summary Tabs */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`
                    py-4 px-1 border-b-2 font-medium text-sm transition-colors
                    ${activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            <div className="prose max-w-none">
              {tabs.find(t => t.id === activeTab)?.content.split('\n').map((line, i) => {
                if (line.startsWith('##')) {
                  return <h3 key={i} className="text-lg font-bold mt-4 mb-2">{line.replace(/^##\s*/, '')}</h3>;
                }
                if (line.startsWith('**') && line.endsWith('**')) {
                  return <p key={i} className="font-semibold mt-2">{line.replace(/\*\*/g, '')}</p>;
                }
                if (line.startsWith('-')) {
                  return <li key={i} className="ml-4">{line.substring(1)}</li>;
                }
                if (line.trim() === '') {
                  return <br key={i} />;
                }
                return <p key={i} className="mb-2">{line}</p>;
              })}
            </div>

            <div className="flex gap-3 mt-6 pt-4 border-t">
              <button
                onClick={() => copyToClipboard(tabs.find(t => t.id === activeTab)?.content || '')}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
              >
                📋 Copy to Clipboard
              </button>
              <button
                onClick={downloadAsPDF}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
              >
                📥 Download as PDF
              </button>
            </div>
          </div>
        </div>

        {/* Metadata Footer */}
        <div className="mt-6 text-xs text-gray-400 text-center">
          <p>Summary ID: {detail.summary.summaryId}</p>
          <p>Generated: {format(new Date(detail.summary.created_at), 'PPpp')}</p>
          <p>Model: {detail.summary.model}</p>
        </div>
      </main>
    </div>
  );
}