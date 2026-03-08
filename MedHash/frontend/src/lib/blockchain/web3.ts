import { BrowserProvider, Contract, JsonRpcProvider, keccak256, toUtf8Bytes } from 'ethers';
import MedHashABI from './MedHashABI.json';

const CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_CONTRACT_ADDRESS;
const INFURA_KEY = process.env.NEXT_PUBLIC_INFURA_API_KEY;
const INFURA_URL = `https://sepolia.infura.io/v3/${INFURA_KEY}`;

console.log('🔧 Blockchain Config:', {
  contractAddress: CONTRACT_ADDRESS,
  infuraUrl: INFURA_URL,
  networkId: process.env.NEXT_PUBLIC_NETWORK_ID
});

export class BlockchainService {
  private provider: BrowserProvider | null = null;
  private contract: Contract | null = null;
  private signerAddress: string = '';

  async connect(): Promise<string> {
    try {
      if (!window.ethereum) throw new Error('Please install MetaMask');
      
      this.provider = new BrowserProvider(window.ethereum);
      const signer = await this.provider.getSigner();
      this.signerAddress = await signer.getAddress();
      
      const network = await this.provider.getNetwork();
      console.log('🌐 Connected to network:', {
        chainId: Number(network.chainId),
        name: network.name
      });
      
      if (Number(network.chainId) !== 11155111) {
        throw new Error(`Wrong network! Please switch to Sepolia (current: ${Number(network.chainId)})`);
      }
      
      console.log('📝 Using contract at:', CONTRACT_ADDRESS);
      
      // Verify contract exists
      const code = await this.provider.getCode(CONTRACT_ADDRESS!);
      if (code === '0x') {
        throw new Error(`No contract found at address ${CONTRACT_ADDRESS}`);
      }
      console.log('✅ Contract verified, code length:', code.length);
      
      this.contract = new Contract(CONTRACT_ADDRESS!, MedHashABI.abi, signer);
      
      return this.signerAddress;
    } catch (error: any) {
      console.error('❌ Connection failed:', {
        message: error.message,
        code: error.code,
        stack: error.stack
      });
      throw error;
    }
  }

  async storeProof(pmid: string, summaryType: string, summaryHash: string) {
    try {
      if (!this.contract) await this.connect();

      console.log('📦 Storing proof:', { pmid, summaryType, summaryHash });

      // First check if proof already exists using public provider
      try {
        const publicProvider = new JsonRpcProvider(INFURA_URL);
        const readContract = new Contract(CONTRACT_ADDRESS!, MedHashABI.abi, publicProvider);
        const exists = await readContract.verifyProof(pmid, summaryType, summaryHash);
        console.log('🔍 Pre-verify check:', { exists: exists[0], timestamp: exists[1] });
        
        if (exists[0]) {
          throw new Error('This proof already exists on blockchain');
        }
      } catch (verifyError: any) {
        console.log('Pre-verify check failed (continuing anyway):', verifyError.message);
      }

      // Get the signer's address for logging
      const signer = await this.contract!.runner.getAddress();
      console.log('👤 Signer address:', signer);

      // Check balance
      const balance = await this.provider!.getBalance(signer);
      console.log('💰 Signer balance:', balance.toString(), 'wei');

      if (balance === 0n) {
        throw new Error('Insufficient balance. Get Sepolia ETH from a faucet.');
      }

      // Estimate gas first
      let gasEstimate;
      try {
        gasEstimate = await this.contract!.storeProof.estimateGas(pmid, summaryType, summaryHash);
        console.log('⛽ Estimated gas:', gasEstimate.toString());
      } catch (estimateError: any) {
        console.error('Gas estimation failed:', {
          message: estimateError.message,
          data: estimateError.data,
          transaction: estimateError.transaction
        });
        // Use default gas limit
        gasEstimate = 500000n;
      }

      // Send transaction with explicit gas limit
      const tx = await this.contract!.storeProof(pmid, summaryType, summaryHash, {
        gasLimit: gasEstimate * 120n / 100n, // Add 20% buffer
      });
      
      console.log('✍️ Transaction sent:', {
        hash: tx.hash,
        to: tx.to,
        from: tx.from,
        data: tx.data.substring(0, 66) + '...' // Log first part of data
      });
      
      // Wait for confirmation with timeout
      const receipt = await Promise.race([
        tx.wait(),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Transaction confirmation timeout after 60 seconds')), 60000)
        )
      ]);
      
      console.log('✅ Transaction confirmed:', {
        hash: receipt.hash,
        blockNumber: receipt.blockNumber,
        gasUsed: receipt.gasUsed?.toString()
      });
      
      return {
        success: true,
        txHash: receipt.hash,
        blockNumber: receipt.blockNumber,
        timestamp: new Date().toISOString()
      };
      
    } catch (error: any) {
      // Detailed error logging
      console.error('❌ Store proof failed - DETAILS:', {
        name: error.name,
        message: error.message,
        code: error.code,
        data: error.data,
        transaction: error.transaction ? {
          to: error.transaction.to,
          from: error.transaction.from,
          data: error.transaction.data?.substring(0, 66)
        } : null,
        shortMessage: error.shortMessage,
        stack: error.stack,
        error: JSON.stringify(error, Object.getOwnPropertyNames(error))
      });

      // User-friendly error messages
      if (error.message?.includes('insufficient funds')) {
        throw new Error('Insufficient Sepolia ETH for gas. Get free test ETH from a faucet.');
      }
      if (error.message?.includes('nonce')) {
        throw new Error('Transaction nonce error. Reset your MetaMask account (Settings > Advanced > Clear activity tab data)');
      }
      if (error.message?.includes('already known')) {
        throw new Error('Transaction is already pending. Check MetaMask.');
      }
      if (error.code === 'CALL_EXCEPTION') {
        throw new Error('Contract execution failed. The transaction was reverted by the contract.');
      }
      
      throw error;
    }
  }

  async verifyProof(pmid: string, summaryType: string, summaryHash: string) {
    try {
      const provider = new JsonRpcProvider(INFURA_URL);
      const contract = new Contract(CONTRACT_ADDRESS!, MedHashABI.abi, provider);
      
      const result = await contract.verifyProof(pmid, summaryType, summaryHash);
      
      return {
        verified: result[0],
        timestamp: result[1] ? Number(result[1]) : null
      };
    } catch (error: any) {
      console.error('❌ Verify failed:', error);
      throw error;
    }
  }

  isConnected(): boolean {
    return this.contract !== null;
  }

  getSignerAddress(): string {
    return this.signerAddress;
  }
}

export const blockchainService = new BlockchainService();