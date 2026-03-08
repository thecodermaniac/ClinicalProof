import { JsonRpcProvider } from 'ethers';

export class GasManager {
  private static instance: GasManager;
  private gasPrice: bigint = BigInt(0);
  private lastUpdate: number = 0;
  private readonly UPDATE_INTERVAL = 30000; // 30 seconds

  private constructor() {}

  static getInstance(): GasManager {
    if (!GasManager.instance) {
      GasManager.instance = new GasManager();
    }
    return GasManager.instance;
  }

  async getGasPrice(provider: JsonRpcProvider): Promise<bigint> {
    const now = Date.now();
    
    if (now - this.lastUpdate > this.UPDATE_INTERVAL || this.gasPrice === BigInt(0)) {
      try {
        const feeData = await provider.getFeeData();
        this.gasPrice = feeData.gasPrice || BigInt(0);
        this.lastUpdate = now;
        console.log('⛽ Updated gas price:', this.gasPrice.toString());
      } catch (error) {
        console.warn('Failed to get gas price, using default');
        if (this.gasPrice === BigInt(0)) {
          this.gasPrice = BigInt(10000000000); // 10 gwei default
        }
      }
    }
    
    return this.gasPrice;
  }
}

export const gasManager = GasManager.getInstance();