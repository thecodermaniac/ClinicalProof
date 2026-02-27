'use client';

import { useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

export default function Home() {
  const [pmid, setPmid] = useState('');
  const [loading, setLoading] = useState(false);
  const [paper, setPaper] = useState<any>(null);
  const [summaries, setSummaries] = useState<any>(null);
  const [hash, setHash] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('short');

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

  const fetchPaper = async () => {
    if (!pmid) return;
    
    setLoading(true);
    try {
      // Fetch paper
      const fetchRes = await axios.post(`${API_URL}/fetch`, { pmid });
      setPaper(fetchRes.data.data);
      
      // Generate summaries
      const summaryRes = await axios.post(`${API_URL}/summarize`, { pmid });
      setSummaries(summaryRes.data.summaries);
      
    } catch (error) {
      console.error('Error:', error);
      alert('Error fetching paper');
    } finally {
      setLoading(false);
    }
  };

  const createHash = async () => {
    if (!paper || !summaries) return;
    
    try {
      const hashRes = await axios.post(`${API_URL}/hash`, {
        pmid: paper.pmid,
        summaryId: summaries.summaryId || 'temp-id',
        title: paper.title,
        summary: summaries.medium
      });
      setHash(hashRes.data);
    } catch (error) {
      console.error('Error:', error);
      alert('Error creating hash');
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="container mx-auto px-4 py-12 max-w-4xl">
        <h1 className="text-4xl font-bold text-center mb-2 text-blue-800">
          MedHash 🔗
        </h1>
        <p className="text-center text-gray-600 mb-8">
          Verify medical literature with blockchain hashing
        </p>
        
        {/* Input Section */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            PubMed ID (PMID)
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={pmid}
              onChange={(e) => setPmid(e.target.value)}
              placeholder="e.g., 12345678"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              onClick={fetchPaper}
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition"
            >
              {loading ? 'Loading...' : 'Fetch Paper'}
            </button>
          </div>
        </div>
        
        {/* Paper Display */}
        {paper && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">{paper.title}</h2>
            <p className="text-sm text-gray-600 mb-2">
              Journal: {paper.journal} | Published: {paper.pubdate}
            </p>
            
            {/* Summary Tabs */}
            {summaries && (
              <div className="mt-6">
                <div className="border-b border-gray-200 mb-4">
                  <nav className="flex gap-4">
                    {['short', 'medium', 'long'].map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`pb-2 px-1 capitalize ${
                          activeTab === tab
                            ? 'border-b-2 border-blue-600 text-blue-600 font-medium'
                            : 'text-gray-500 hover:text-gray-700'
                        }`}
                      >
                        {tab} ({tab === 'short' ? '2 min' : tab === 'medium' ? '5 min' : '10 min'})
                      </button>
                    ))}
                  </nav>
                </div>
                
                <div className="prose max-w-none">
                  <ReactMarkdown>
                    {summaries[activeTab] || 'Summary not available'}
                  </ReactMarkdown>
                </div>
                
                <button
                  onClick={createHash}
                  className="mt-6 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                >
                  🔒 Create Verification Hash
                </button>
              </div>
            )}
          </div>
        )}
        
        {/* Hash Display */}
        {hash && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-green-800 mb-2">
              ✓ Hash Created Successfully
            </h3>
            <div className="bg-white rounded p-3 font-mono text-sm break-all">
              {hash.hash}
            </div>
            <p className="text-sm text-gray-600 mt-2">
              Verification URL: {hash.verificationUrl}
            </p>
          </div>
        )}
      </div>
    </main>
  );
}