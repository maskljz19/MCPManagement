/**
 * Network error detection utility
 * Validates: Requirements 11.2
 */

type NetworkStatusCallback = (isOnline: boolean) => void;

class NetworkDetector {
  private static instance: NetworkDetector;
  private listeners: Set<NetworkStatusCallback> = new Set();
  private isOnline: boolean = navigator.onLine;

  private constructor() {
    this.setupListeners();
  }

  public static getInstance(): NetworkDetector {
    if (!NetworkDetector.instance) {
      NetworkDetector.instance = new NetworkDetector();
    }
    return NetworkDetector.instance;
  }

  private setupListeners(): void {
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);
  }

  private handleOnline = (): void => {
    this.isOnline = true;
    this.notifyListeners(true);
  };

  private handleOffline = (): void => {
    this.isOnline = false;
    this.notifyListeners(false);
  };

  private notifyListeners(isOnline: boolean): void {
    this.listeners.forEach((callback) => callback(isOnline));
  }

  public subscribe(callback: NetworkStatusCallback): () => void {
    this.listeners.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(callback);
    };
  }

  public getStatus(): boolean {
    return this.isOnline;
  }

  public cleanup(): void {
    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);
    this.listeners.clear();
  }
}

export const networkDetector = NetworkDetector.getInstance();
export default networkDetector;
