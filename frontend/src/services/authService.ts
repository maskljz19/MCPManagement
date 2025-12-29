import axiosInstance from '../lib/axios';
import type { User, TokenResponse, LoginCredentials, RegisterData } from '../types';

class AuthService {
  private static instance: AuthService;
  private currentUser: User | null = null;

  private constructor() {
    // Load user from localStorage on initialization
    this.loadUserFromStorage();
  }

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  /**
   * Get the current access token from localStorage
   */
  public getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  /**
   * Get the current refresh token from localStorage
   */
  public getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  /**
   * Store authentication tokens in localStorage
   */
  public setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  /**
   * Clear all authentication tokens from localStorage
   */
  public clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('current_user');
    this.currentUser = null;
  }

  /**
   * Check if user is authenticated
   */
  public isAuthenticated(): boolean {
    const token = this.getAccessToken();
    return token !== null && token !== '';
  }

  /**
   * Refresh the access token using the refresh token
   */
  public async refreshAccessToken(): Promise<string> {
    const refreshToken = this.getRefreshToken();
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await axiosInstance.post<TokenResponse>('/api/v1/auth/refresh', {
        refresh_token: refreshToken,
      });

      const { access_token, refresh_token: newRefreshToken } = response.data;

      // Store new tokens
      this.setTokens(access_token, newRefreshToken || refreshToken);

      return access_token;
    } catch (error) {
      // If refresh fails, clear tokens
      this.clearTokens();
      throw error;
    }
  }

  /**
   * Get the current user
   */
  public getCurrentUser(): User | null {
    return this.currentUser;
  }

  /**
   * Set the current user and store in localStorage
   */
  public setCurrentUser(user: User): void {
    this.currentUser = user;
    localStorage.setItem('current_user', JSON.stringify(user));
  }

  /**
   * Load user from localStorage
   */
  private loadUserFromStorage(): void {
    const userStr = localStorage.getItem('current_user');
    if (userStr) {
      try {
        this.currentUser = JSON.parse(userStr);
      } catch (error) {
        console.error('Failed to parse user from localStorage:', error);
        localStorage.removeItem('current_user');
      }
    }
  }

  /**
   * Login with username and password
   */
  public async login(credentials: LoginCredentials): Promise<User> {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await axiosInstance.post<TokenResponse>('/api/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    const { access_token, refresh_token } = response.data;
    this.setTokens(access_token, refresh_token);

    // Fetch user profile
    const user = await this.fetchCurrentUser();
    this.setCurrentUser(user);

    return user;
  }

  /**
   * Register a new user
   */
  public async register(data: RegisterData): Promise<User> {
    const response = await axiosInstance.post<User>('/api/v1/auth/register', data);
    
    // Auto-login after registration
    await this.login({
      username: data.username,
      password: data.password,
    });

    return response.data;
  }

  /**
   * Logout the current user
   */
  public async logout(): Promise<void> {
    const refreshToken = this.getRefreshToken();
    
    if (refreshToken) {
      try {
        await axiosInstance.post('/api/v1/auth/logout', {
          refresh_token: refreshToken,
        });
      } catch (error) {
        console.error('Logout request failed:', error);
        // Continue with local cleanup even if API call fails
      }
    }

    this.clearTokens();
  }

  /**
   * Fetch the current user profile
   */
  private async fetchCurrentUser(): Promise<User> {
    const response = await axiosInstance.get<User>('/api/v1/auth/me');
    return response.data;
  }

  /**
   * Get user profile (with caching)
   */
  public async getUserProfile(): Promise<User> {
    if (this.currentUser) {
      return this.currentUser;
    }

    const user = await this.fetchCurrentUser();
    this.setCurrentUser(user);
    return user;
  }
}

// Export singleton instance
export const authService = AuthService.getInstance();
export default authService;
