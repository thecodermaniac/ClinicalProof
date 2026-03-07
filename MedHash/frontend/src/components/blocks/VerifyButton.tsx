'use client';

import { useState } from 'react';

interface VerifyButtonProps {
  pmid: string;
  summaryHash?: string;
}

export default function VerifyButton({ pmid, summaryHash }: VerifyButtonProps) {
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    txHash?: string;
    timestamp?: string;
    error?: string;
  } | null>(null);

  const handleVerify = async () => {
    if (!summaryHash) {
      alert('No summary hash available. Generate summaries first.');
      return;
    }

    setVerifying(true);
    
    // Simulate blockchain verification (will be replaced with real Web3 later)
    setTimeout(() => {
      setResult({
        success: true,
        txHash: '0x' + Math.random().toString(16).substring(2, 10) + '...',
        timestamp: new Date().toISOString()
      });
      setVerifying(false);
    }, 2000);
  };

  return (
    <div className="max-w-4xl mx-auto mt-6 p-4 border rounded-lg bg-white">
      <button
        onClick={handleVerify}
        disabled={verifying || !summaryHash}
        className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
      >
        {verifying ? (
          <>
            <span className="animate-spin">⏳</span>
            Verifying on Blockchain...
          </>
        ) : (
          <>
            🔗 Verify on Blockchain
          </>
        )}
      </button>

      {result?.success && (
        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-green-800 font-semibold">✅ Verified Successfully!</p>
          <p className="text-sm text-gray-600 mt-2">Transaction: {result.txHash}</p>
          <p className="text-sm text-gray-600">Timestamp: {new Date(result.timestamp!).toLocaleString()}</p>
          <a 
            href="#" 
            className="text-sm text-blue-600 hover:underline mt-2 inline-block"
            onClick={(e) => e.preventDefault()}
          >
            View on Explorer →
          </a>
        </div>
      )}

      {result?.error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">❌ Verification failed: {result.error}</p>
        </div>
      )}
    </div>
  );
}
