import { JsonRpcProvider } from 'ethers';

interface RPCConfig {
  url: string;
  weight: number; // Higher weight = more requests allowed
  lastUsed: number;
  failCount: number;
  isActive: boolean;
}

export class RPCManager {
  private rpcs: RPCConfig[] = [
    { url: 'https://sepolia.drpc.org', weight: 5, lastUsed: 0, failCount: 0, isActive: true },
    { url: 'https://rpc.sepolia.org', weight: 3, lastUsed: 0, failCount: 0, isActive: true },
    { url: 'https://sepolia.gateway.tenderly.co', weight: 4, lastUsed: 0, failCount: 0, isActive: true },
    { url: `https://sepolia.infura.io/v3/${process.env.NEXT_PUBLIC_INFURA_API_KEY}`, weight: 10, lastUsed: 0, failCount: 0, isActive: true },
    { url: 'https://ethereum-sepolia.publicnode.com', weight: 3, lastUsed: 0, failCount: 0, isActive: true },
  ];

  private requestQueue: Array<() => Promise<any>> = [];
  private isProcessing = false;
  private requestCount = 0;
  private lastRequestTime = Date.now();
  private readonly RATE_LIMIT = 10; // requests per second
  private readonly RATE_WINDOW = 1000; // 1 second

  private getAvailableRPC(): RPCConfig | null {
    const now = Date.now();
    const activeRpcs = this.rpcs.filter(r => r.isActive);
    
    if (activeRpcs.length === 0) {
      // Reset all RPCs if all are failed
      this.rpcs.forEach(r => {
        r.isActive = true;
        r.failCount = 0;
      });
      return this.rpcs[0];
    }

    // Select RPC based on weight and recent usage
    const sortedRpcs = activeRpcs.sort((a, b) => {
      const aScore = a.weight / (1 + (now - a.lastUsed) / 1000);
      const bScore = b.weight / (1 + (now - b.lastUsed) / 1000);
      return bScore - aScore;
    });

    return sortedRpcs[0];
  }

  private async rateLimit() {
    const now = Date.now();
    const timeWindow = now - this.lastRequestTime;
    
    if (timeWindow < this.RATE_WINDOW) {
      if (this.requestCount >= this.RATE_LIMIT) {
        const delay = this.RATE_WINDOW - timeWindow;
        await new Promise(resolve => setTimeout(resolve, delay));
        this.requestCount = 0;
        this.lastRequestTime = Date.now();
      }
    } else {
      this.requestCount = 0;
      this.lastRequestTime = now;
    }
    
    this.requestCount++;
  }

  async executeWithRetry<T>(
    operation: (provider: JsonRpcProvider) => Promise<T>,
    maxRetries = 5
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      this.requestQueue.push(async () => {
        let lastError: Error | null = null;
        
        for (let attempt = 0; attempt < maxRetries; attempt++) {
          const rpc = this.getAvailableRPC();
          if (!rpc) {
            await new Promise(r => setTimeout(r, 1000));
            continue;
          }

          try {
            await this.rateLimit();
            
            const provider = new JsonRpcProvider(rpc.url);
            rpc.lastUsed = Date.now();
            
            console.log(`📡 Attempt ${attempt + 1} using RPC: ${rpc.url}`);
            
            const result = await operation(provider);
            
            // Success - reset fail count
            rpc.failCount = 0;
            
            return resolve(result);
          } catch (error: any) {
            console.warn(`❌ RPC ${rpc.url} failed:`, error.message);
            
            rpc.failCount++;
            
            // Mark RPC as inactive after 3 failures
            if (rpc.failCount >= 3) {
              rpc.isActive = false;
              console.warn(`🚫 RPC ${rpc.url} disabled temporarily`);
              
              // Reactivate after 2 minutes
              setTimeout(() => {
                rpc.isActive = true;
                rpc.failCount = 0;
                console.log(`🔄 RPC ${rpc.url} re-enabled`);
              }, 120000);
            }
            
            lastError = error;
            
            // Wait before retry with exponential backoff
            const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
            await new Promise(r => setTimeout(r, delay));
          }
        }
        
        reject(lastError || new Error('All RPC endpoints failed'));
      });

      this.processQueue();
    });
  }

  private async processQueue() {
    if (this.isProcessing || this.requestQueue.length === 0) return;
    
    this.isProcessing = true;
    
    while (this.requestQueue.length > 0) {
      const task = this.requestQueue.shift();
      if (task) {
        await task().catch(() => {}); // Errors handled per task
      }
    }
    
    this.isProcessing = false;
  }

  clearQueue() {
    this.requestQueue = [];
    this.isProcessing = false;
  }
}

export const rpcManager = new RPCManager();