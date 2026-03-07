'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import PubMedInput from '@/src/components/blocks/PubMedInput';
import SummaryTabs from '@/src/components/blocks/SummaryTabs';
import { blockchainService } from '@/src/lib/blockchain/web3';
import { apiClient } from '@/src/lib/api/client';

export default function Home() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [paper, setPaper] = useState<any>(null);
  const [summaries, setSummaries] = useState<any>(null);
  const [summaryId, setSummaryId] = useState<string>('');
  const [hash, setHash] = useState<string>('');
  const [walletConnected, setWalletConnected] = useState(false);
  const [walletAddress, setWalletAddress] = useState('');
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [blockchainStatus, setBlockchainStatus] = useState<{
    verifying: boolean;
    result?: any;
    error?: string;
  }>({ verifying: false });

  useEffect(() => {
    if (blockchainService.isConnected()) {
      setWalletConnected(true);
      setWalletAddress(blockchainService.getSignerAddress());
    }
  }, []);

  const connectWallet = async () => {
    try {
      setBlockchainStatus({ verifying: true });
      const address = await blockchainService.connect();
      setWalletConnected(true);
      setWalletAddress(address);
      setBlockchainStatus({ verifying: false });
    } catch (error: any) {
      console.error('Failed to connect wallet:', error);
      setBlockchainStatus({ 
        verifying: false, 
        error: error.message || 'Failed to connect wallet' 
      });
      alert(error.message || 'Please install MetaMask to use blockchain features');
    }
  };

  const handleFetch = async (pmid: string) => {
    setLoading(true);
    try {
      const paperData = await apiClient.fetchPaper(pmid);
      setPaper(paperData);
      
      const summaryData = await apiClient.generateSummary(pmid, 'all');
      setSummaries(summaryData.summaries);
      setSummaryId(summaryData.summaryId);
      
    } catch (error: any) {
      console.error('Error:', error);
      alert(error.message || 'Failed to fetch paper. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateHash = async () => {
    if (!paper || !summaries || !summaryId) {
      alert('Please fetch a paper and generate summaries first');
      return;
    }

    setLoading(true);
    try {
      const hashData = await apiClient.createHash({
        pmid: paper.pmid,
        summaryId: summaryId,
        title: paper.title,
        summary: summaries.medium || summaries.patient,
        storeOnChain: false
      });
      
      setHash(hashData.hash);
      
      // Show success modal
      setShowSuccessModal(true);
      
    } catch (error: any) {
      console.error('Hash creation error:', error);
      alert(error.message || 'Failed to create hash');
    } finally {
      setLoading(false);
    }
  };

  const handleBlockchainVerify = async () => {
    if (!walletConnected) {
      await connectWallet();
    }
    
    if (!paper || !hash) {
      alert('Please create a hash first');
      return;
    }

    setBlockchainStatus({ verifying: true });
    
    try {
      const lambdaVerification = await apiClient.verifyHash(hash);
      
      if (!lambdaVerification.verified) {
        throw new Error('Hash not found in database');
      }
      
      const summaryType = 'patient';
      const result = await blockchainService.storeProof(
        paper.pmid,
        summaryType,
        hash
      );
      
      setBlockchainStatus({
        verifying: false,
        result: {
          ...result,
          message: '✅ Proof stored on blockchain successfully!'
        }
      });
      
    } catch (error: any) {
      console.error('Blockchain verification error:', error);
      setBlockchainStatus({
        verifying: false,
        error: error.message || 'Failed to verify on blockchain'
      });
    }
  };

  const handleCheckBlockchain = async () => {
    if (!walletConnected) {
      await connectWallet();
    }
    
    if (!paper || !hash) {
      alert('Please create a hash first');
      return;
    }

    setBlockchainStatus({ verifying: true });
    
    try {
      const summaryType = 'patient';
      const result = await blockchainService.verifyProof(
        paper.pmid,
        summaryType,
        hash
      );
      
      if (result.verified) {
        setBlockchainStatus({
          verifying: false,
          result: {
            success: true,
            message: '✅ Proof verified on blockchain!',
            timestamp: result.timestamp ? new Date(result.timestamp * 1000).toLocaleString() : null,
            proof: result.proof
          }
        });
      } else {
        setBlockchainStatus({
          verifying: false,
          result: {
            success: false,
            message: '❌ Proof not found on blockchain. Click "Store on Blockchain" first.'
          }
        });
      }
    } catch (error: any) {
      console.error('Blockchain check error:', error);
      setBlockchainStatus({
        verifying: false,
        error: error.message || 'Failed to check blockchain'
      });
    }
  };

  // Success Modal Component
  const SuccessModal = () => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div className="text-center mb-4">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
            <span className="text-3xl">✅</span>
          </div>
          <h3 className="text-xl font-bold text-gray-900">Summary Generated!</h3>
          <p className="text-gray-600 mt-2">
            Your summary has been created successfully and saved to your library.
          </p>
        </div>
        
        <div className="space-y-3">
          <Link
            href={`/summaries/${summaryId}`}
            className="block w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-center font-medium"
            onClick={() => setShowSuccessModal(false)}
          >
            🔍 View This Summary
          </Link>
          
          <Link
            href="/summaries"
            className="block w-full px-4 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-center font-medium"
            onClick={() => setShowSuccessModal(false)}
          >
            📚 Go to My Summaries
          </Link>
          
          <button
            onClick={() => setShowSuccessModal(false)}
            className="block w-full px-4 py-3 text-gray-500 hover:text-gray-700 text-center"
          >
            Continue with current paper
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Success Modal */}
      {showSuccessModal && <SuccessModal />}

      <header className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto py-4 px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-8">
              <Link href="/" className="text-2xl font-bold text-blue-600">
                MedHash
              </Link>
              <nav className="hidden md:flex gap-4">
                <Link 
                  href="/" 
                  className="text-blue-600 bg-blue-50 px-3 py-2 rounded-lg font-medium"
                >
                  Home
                </Link>
                <Link 
                  href="/summaries" 
                  className="text-gray-600 hover:text-blue-600 px-3 py-2 rounded-lg transition-colors"
                >
                  My Summaries
                </Link>
              </nav>
            </div>
            <div className="flex items-center gap-4">
              {/* Mobile menu button */}
              <button className="md:hidden p-2 text-gray-600 hover:text-gray-900">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              
              {!walletConnected ? (
                <button
                  onClick={connectWallet}
                  disabled={blockchainStatus.verifying}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 text-sm md:text-base"
                >
                  {blockchainStatus.verifying ? 'Connecting...' : 'Connect Wallet'}
                </button>
              ) : (
                <div className="flex items-center gap-3">
                  <span className="hidden md:inline text-sm text-gray-600 bg-gray-100 px-3 py-2 rounded-lg">
                    🔗 {walletAddress.substring(0, 6)}...{walletAddress.substring(38)}
                  </span>
                  <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                    ✓ Connected
                  </span>
                </div>
              )}
            </div>
          </div>
          
          {/* Mobile Navigation */}
          <div className="md:hidden mt-4 flex gap-2">
            <Link 
              href="/" 
              className="flex-1 text-center px-3 py-2 bg-blue-600 text-white rounded-lg text-sm"
            >
              Home
            </Link>
            <Link 
              href="/summaries" 
              className="flex-1 text-center px-3 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm"
            >
              My Summaries
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-12 px-4">
        {/* Quick link to summaries */}
        {paper && (
          <div className="mb-6 flex justify-end">
            <Link
              href="/summaries"
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <span>📚</span>
              View all your summaries →
            </Link>
          </div>
        )}

        {!paper ? (
          <div className="max-w-3xl mx-auto mt-12">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Medical Research, Verified
              </h2>
              <p className="text-lg text-gray-600">
                Enter any PubMed paper to get AI-powered summaries with blockchain proof
              </p>
            </div>
            <PubMedInput onFetch={handleFetch} loading={loading} />
          </div>
        ) : (
          <div className="space-y-8">
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">{paper.title}</h2>
              <p className="text-sm text-gray-600 mb-3">PMID: {paper.pmid}</p>
              {paper.authors && paper.authors.length > 0 && (
                <p className="text-sm text-gray-500">
                  {paper.authors.slice(0, 3).join(', ')}{paper.authors.length > 3 ? ' et al.' : ''}
                </p>
              )}
            </div>

            {loading ? (
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                <p className="mt-4 text-gray-600">Processing...</p>
              </div>
            ) : (
              summaries && (
                <>
                  <SummaryTabs summaries={summaries} />
                  
                  <div className="flex flex-col gap-4 max-w-2xl mx-auto">
                    <button
                      onClick={handleCreateHash}
                      disabled={!paper || !summaries || loading}
                      className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors font-medium"
                    >
                      🔐 Create Hash
                    </button>

                    {hash && (
                      <div className="space-y-3">
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                          <p className="text-green-800 font-semibold mb-2">✅ Hash Generated</p>
                          <p className="font-mono text-sm break-all bg-white p-2 rounded border">
                            {hash}
                          </p>
                        </div>

                        <div className="flex gap-3">
                          <button
                            onClick={handleBlockchainVerify}
                            disabled={blockchainStatus.verifying || !walletConnected}
                            className="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors font-medium"
                          >
                            {blockchainStatus.verifying ? (
                              <span className="flex items-center justify-center gap-2">
                                <span className="animate-spin">⏳</span>
                                Processing...
                              </span>
                            ) : (
                              '🔗 Store on Blockchain'
                            )}
                          </button>

                          <button
                            onClick={handleCheckBlockchain}
                            disabled={blockchainStatus.verifying || !walletConnected}
                            className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors font-medium"
                          >
                            🔍 Check Blockchain
                          </button>
                        </div>
                      </div>
                    )}

                    {blockchainStatus.result && (
                      <div className={`mt-4 p-4 rounded-lg border ${
                        blockchainStatus.result.success 
                          ? 'bg-green-50 border-green-200' 
                          : 'bg-yellow-50 border-yellow-200'
                      }`}>
                        <p className={`font-semibold mb-2 ${
                          blockchainStatus.result.success ? 'text-green-800' : 'text-yellow-800'
                        }`}>
                          {blockchainStatus.result.message}
                        </p>
                        {blockchainStatus.result.txHash && (
                          <p className="text-sm text-gray-600 break-all">
                            <span className="font-medium">Transaction:</span> {blockchainStatus.result.txHash}
                          </p>
                        )}
                        {blockchainStatus.result.timestamp && (
                          <p className="text-sm text-gray-600">
                            <span className="font-medium">Timestamp:</span> {blockchainStatus.result.timestamp}
                          </p>
                        )}
                      </div>
                    )}

                    {blockchainStatus.error && (
                      <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-red-800 font-semibold mb-2">❌ Error</p>
                        <p className="text-sm text-gray-600">{blockchainStatus.error}</p>
                      </div>
                    )}
                  </div>
                </>
              )
            )}
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