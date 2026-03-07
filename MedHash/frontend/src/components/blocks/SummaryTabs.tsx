'use client';

import { useState } from 'react';

interface SummaryTabsProps {
  summaries: {
    short: string;
    medium: string;
    long: string;
  };
}

export default function SummaryTabs({ summaries }: SummaryTabsProps) {
  const [activeTab, setActiveTab] = useState<'short' | 'medium' | 'long'>('medium');
  
  const tabs = [
    { id: 'short', label: '⚡ Quick (2 min)', icon: '⚡' },
    { id: 'medium', label: '📋 Standard (5 min)', icon: '📋' },
    { id: 'long', label: '🔍 Detailed (10 min)', icon: '🔍' }
  ];

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  };

  const renderSummary = (text: string) => {
    // Convert markdown-style formatting to HTML
    return text.split('\n').map((line, i) => {
      if (line.startsWith('##')) {
        return <h3 key={i} className="text-lg font-bold mt-4 mb-2">{line.replace(/^##\s*/, '')}</h3>;
      }
      if (line.startsWith('**') && line.endsWith('**')) {
        return <p key={i} className="font-semibold mt-2">{line.replace(/\*\*/g, '')}</p>;
      }
      if (line.trim() === '') {
        return <br key={i} />;
      }
      return <p key={i} className="mb-2">{line}</p>;
    });
  };

  return (
    <div className="w-full bg-white rounded-lg shadow-sm border">
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8 px-6" aria-label="Tabs">
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
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>
      
      <div className="p-6">
        <div className="prose max-w-none text-gray-700">
          {renderSummary(summaries[activeTab])}
        </div>
        <button
          onClick={() => copyToClipboard(summaries[activeTab])}
          className="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors inline-flex items-center gap-2"
        >
          <span>📋</span>
          Copy to Clipboard
        </button>
      </div>
    </div>
  );
}