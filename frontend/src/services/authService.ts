import axiosInstance from '../lib/axios';
import type { User, TokenResponse, LoginCredentials, RegisterData } from '../types';
import { decodeJWT } from '../utils/jwt';

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
   * Extract user information from JWT token
   */
  private getUserFromToken(token: string): User | null {
    const payload = decodeJWT(token);
    if (!payload) {
      return null;
    }

    // Validate role
    const validRoles = ['admin', 'developer', 'viewer'] as const;
    const role = validRoles.includes(payload.role as any) 
      ? (payload.role as 'admin' | 'developer' | 'viewer')
      : 'viewer';

    return {
      id: payload.user_id,
      username: payload.username,
      email: '', // Email is not in the token, will be empty
      role: role,
      is_active: true,
      created_at: new Date().toISOString(),
    };
  }

  /**
   * Login with username and password
   */
  public async login(credentials: LoginCredentials): Promise<User> {
    const response = await axiosInstance.post<TokenResponse>('/api/v1/auth/login', {
      username: credentials.username,
      password: credentials.password,
    });

    const { access_token, refresh_token } = response.data;
    this.setTokens(access_token, refresh_token);

    // Extract user info from JWT token
    const user = this.getUserFromToken(access_token);
    if (!user) {
      throw new Error('Failed to extract user information from token');
    }

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
   * Get user profile (with caching)
   */
  public async getUserProfile(): Promise<User> {
    if (this.currentUser) {
      return this.currentUser;
    }

    // Try to get user from stored token
    const token = this.getAccessToken();
    if (token) {
      const user = this.getUserFromToken(token);
      if (user) {
        this.setCurrentUser(user);
        return user;
      }
    }

    throw new Error('No valid authentication token found');
  }
}

// Export singleton instance
export const authService = AuthService.getInstance();
export default authService;
