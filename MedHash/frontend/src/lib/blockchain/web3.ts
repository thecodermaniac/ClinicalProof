import { BrowserProvider, Contract, formatEther, keccak256, toUtf8Bytes } from 'ethers';
import MedHashABI from './MedHashABI.json';

// Get contract address from environment
const CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_CONTRACT_ADDRESS;

export interface Proof {
  hash: string;
  timestamp: number;
  pmid: string;
  summaryType: string;
}

export interface TransactionReceipt {
  success: boolean;
  txHash: string;
  blockNumber: number;
  timestamp: string;
  gasUsed?: string;
}

export class BlockchainService {
  private provider: BrowserProvider | null = null;
  private contract: Contract | null = null;
  private signerAddress: string = '';
  private chainId: number | null = null;

  constructor() {
    if (typeof window !== 'undefined' && window.ethereum) {
      this.provider = new BrowserProvider(window.ethereum);
    }
  }

  async connect(): Promise<string> {
    try {
      if (!window.ethereum) {
        throw new Error('Please install MetaMask to use blockchain features');
      }
      
      if (!this.provider) {
        this.provider = new BrowserProvider(window.ethereum);
      }

      // Request accounts
      const accounts = await window.ethereum.request({ 
        method: 'eth_requestAccounts' 
      });
      
      const signer = await this.provider.getSigner();
      this.signerAddress = await signer.getAddress();
      
      // Get network
      const network = await this.provider.getNetwork();
      this.chainId = Number(network.chainId);
      
      // Check if we're on the right network
      const expectedChainId = parseInt(process.env.NEXT_PUBLIC_NETWORK_ID || '31337');
      if (this.chainId !== expectedChainId) {
        console.warn(`Connected to chain ID ${this.chainId}, expected ${expectedChainId}`);
        // You might want to prompt network switch here
      }
      
      // Initialize contract
      this.contract = new Contract(CONTRACT_ADDRESS, MedHashABI.abi, signer);
      
      // Listen for account changes
      window.ethereum.on('accountsChanged', (accounts: string[]) => {
        if (accounts.length === 0) {
          this.disconnect();
        } else {
          this.signerAddress = accounts[0];
        }
      });

      // Listen for chain changes
      window.ethereum.on('chainChanged', () => {
        window.location.reload();
      });
      
      return this.signerAddress;
    } catch (error) {
      console.error('Connection error:', error);
      throw error;
    }
  }

  async switchToLocalNetwork() {
    try {
      await window.ethereum.request({
        method: 'wallet_addEthereumChain',
        params: [{
          chainId: '0x7A69', // 31337 in hex
          chainName: 'Hardhat Local',
          nativeCurrency: {
            name: 'ETH',
            symbol: 'ETH',
            decimals: 18
          },
          rpcUrls: ['http://127.0.0.1:8545'],
        }],
      });
    } catch (error) {
      console.error('Failed to switch network:', error);
    }
  }

  // ... rest of the methods remain the same ...
  calculateContractHash(pmid: string, summaryType: string, summaryHash: string): string {
    const message = pmid + summaryType + summaryHash;
    return keccak256(toUtf8Bytes(message));
  }

  async storeProof(pmid: string, summaryType: string, summaryHash: string): Promise<TransactionReceipt> {
    try {
      if (!this.contract) {
        await this.connect();
      }
      
      if (!this.contract) {
        throw new Error('Contract not initialized');
      }

      console.log('Storing proof on blockchain:', { pmid, summaryType, summaryHash });
      
      const tx = await this.contract.storeProof(pmid, summaryType, summaryHash);
      const receipt = await tx.wait();
      
      return {
        success: true,
        txHash: receipt.hash,
        blockNumber: receipt.blockNumber,
        timestamp: new Date().toISOString(),
        gasUsed: receipt.gasUsed?.toString()
      };
    } catch (error: any) {
      console.error('Store error:', error);
      if (error.message?.includes('Proof already exists')) {
        throw new Error('This proof has already been stored on the blockchain');
      }
      throw error;
    }
  }

  async verifyProof(pmid: string, summaryType: string, summaryHash: string): Promise<{
    verified: boolean;
    timestamp: number | null;
    proof?: Proof;
  }> {
    try {
      if (!this.contract) {
        await this.connect();
      }
      
      if (!this.contract) {
        throw new Error('Contract not initialized');
      }
      
      const result = await this.contract.verifyProof(pmid, summaryType, summaryHash);
      
      const exists = result[0];
      const timestamp = result[1] ? Number(result[1]) : null;
      
      let proof: Proof | undefined;
      
      if (exists && timestamp) {
        const key = this.calculateContractHash(pmid, summaryType, summaryHash);
        proof = {
          hash: key,
          timestamp,
          pmid,
          summaryType
        };
      }
      
      return {
        verified: exists,
        timestamp,
        proof
      };
    } catch (error) {
      console.error('Verify error:', error);
      throw error;
    }
  }

  async getPaperProofs(pmid: string): Promise<Proof[]> {
    try {
      if (!this.contract) {
        await this.connect();
      }
      
      if (!this.contract) {
        throw new Error('Contract not initialized');
      }
      
      const proofHashes = await this.contract.getPaperProofs(pmid);
      
      const proofs: Proof[] = [];
      
      for (const hash of proofHashes) {
        const proof = await this.contract.proofs(hash);
        proofs.push({
          hash,
          timestamp: Number(proof.timestamp),
          pmid: proof.pmid,
          summaryType: proof.summaryType
        });
      }
      
      return proofs;
    } catch (error) {
      console.error('Get proofs error:', error);
      throw error;
    }
  }

  isConnected(): boolean {
    return this.contract !== null && this.signerAddress !== '';
  }

  getSignerAddress(): string {
    return this.signerAddress;
  }

  getChainId(): number | null {
    return this.chainId;
  }

  async getBalance(): Promise<string> {
    if (!this.provider || !this.signerAddress) {
      return '0';
    }
    const balance = await this.provider.getBalance(this.signerAddress);
    return formatEther(balance);
  }
}

export const blockchainService = new BlockchainService();

declare global {
  interface Window {
    ethereum?: any;
  }
}