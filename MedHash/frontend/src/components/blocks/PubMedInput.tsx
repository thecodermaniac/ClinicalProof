'use client';

import { useState } from 'react';

interface PubMedInputProps {
  onFetch: (pmid: string) => void;
  loading?: boolean;
}

export default function PubMedInput({ onFetch, loading }: PubMedInputProps) {
  const [input, setInput] = useState('');
  const [error, setError] = useState('');

  const extractPMID = (input: string): string | null => {
    const urlPatterns = [
      /pubmed\.ncbi\.nlm\.nih\.gov\/(\d+)/,
      /pubmed\.ncbi\.nlm\.nih\.gov\/pubmed\/(\d+)/,
      /pmid=(\d+)/,
      /^(\d{1,20})$/
    ];

    for (const pattern of urlPatterns) {
      const match = input.match(pattern);
      if (match) return match[1];
    }
    return null;
  };

  const isValidPMID = (pmid: string): boolean => {
    return /^\d{1,20}$/.test(pmid);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    const pmid = extractPMID(input);
    
    if (!pmid || !isValidPMID(pmid)) {
      setError('Invalid PubMed URL or PMID');
      return;
    }

    try {
      await onFetch(pmid);
      setInput(''); // Clear input after successful fetch
    } catch (err) {
      setError('Failed to fetch paper');
    }
  };

  const examples = [
    { label: "COVID-19 study", pmid: "38277423" },
    { label: "Cancer research", pmid: "30705047" },
    { label: "Heart disease", pmid: "35940226" }
  ];

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Enter PubMed URL or PMID (e.g., 30705047)"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white placeholder-gray-500"
            disabled={loading}
          />
          {error && (
            <p className="mt-2 text-red-500 text-sm flex items-center gap-1">
              <span>⚠️</span>
              {error}
            </p>
          )}
        </div>
        
        <button
          type="submit"
          disabled={loading}
          className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors font-medium"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin">⏳</span>
              Fetching...
            </span>
          ) : (
            'Fetch Paper'
          )}
        </button>
      </form>

      {/* Example links */}
      <div className="mt-4 text-center">
        <p className="text-sm text-gray-500 mb-2">Try an example:</p>
        <div className="flex flex-wrap gap-2 justify-center">
          {examples.map((ex) => (
            <button
              key={ex.pmid}
              onClick={() => {
                setInput(ex.pmid);
                handleSubmit(new Event('submit') as any);
              }}
              className="text-xs px-3 py-1 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}