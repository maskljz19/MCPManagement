import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

// Get base URL from environment variables
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with default configuration
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Flag to prevent multiple token refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

// Request interceptor - adds authentication token to requests
axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Try to get token from localStorage first (primary source)
    let token = localStorage.getItem('access_token');
    
    // If not in localStorage, try to get from auth-storage (Zustand persist)
    if (!token) {
      try {
        const authStorage = localStorage.getItem('auth-storage');
        if (authStorage) {
          const parsed = JSON.parse(authStorage);
          token = parsed.state?.accessToken || null;
        }
      } catch (e) {
        console.error('Failed to parse auth-storage:', e);
      }
    }
    
    // Debug log
    if (import.meta.env.DEV) {
      console.log(`🌐 ${config.method?.toUpperCase()} ${config.url}`, {
        hasToken: !!token,
        tokenPreview: token ? `${token.substring(0, 20)}...` : 'none',
      });
    }
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    } else if (!token && import.meta.env.DEV) {
      console.warn('⚠️ No token available for request');
    }
    
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handles errors and token refresh
axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Handle 401 errors - attempt token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Skip token refresh for auth endpoints
      if (originalRequest.url?.includes('/auth/login') || 
          originalRequest.url?.includes('/auth/register') ||
          originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return axiosInstance(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');

      if (!refreshToken) {
        // No refresh token available, clear auth and reject
        console.warn('⚠️ No refresh token available, clearing auth');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('auth-storage');
        isRefreshing = false;
        
        // Redirect to login if in browser
        if (typeof window !== 'undefined') {
          window.location.href = '/auth/login';
        }
        
        return Promise.reject(error);
      }

      try {
        // Attempt to refresh the token
        console.log('🔄 Attempting to refresh token...');
        const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;
        console.log('✅ Token refresh successful');

        // Store new tokens
        localStorage.setItem('access_token', access_token);
        if (newRefreshToken) {
          localStorage.setItem('refresh_token', newRefreshToken);
        }

        // Update authorization header
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        // Process queued requests
        processQueue(null, access_token);

        // Retry original request
        return axiosInstance(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens
        console.error('❌ Token refresh failed:', refreshError);
        processQueue(refreshError as Error, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('auth-storage');
        
        // Redirect to login if in browser
        if (typeof window !== 'undefined') {
          window.location.href = '/auth/login';
        }
        
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Handle 429 rate limit errors
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after'];
      const errorMessage = retryAfter
        ? `Rate limit exceeded. Please try again in ${retryAfter} seconds.`
        : 'Rate limit exceeded. Please try again later.';
      
      return Promise.reject({
        ...error,
        message: errorMessage,
        isRateLimit: true,
        retryAfter: retryAfter ? parseInt(retryAfter, 10) : null,
      });
    }

    // Handle network errors
    if (!error.response) {
      return Promise.reject({
        ...error,
        message: 'Network error. Please check your internet connection.',
        isNetworkError: true,
      });
    }

    // Handle other HTTP errors with user-friendly messages
    const responseData = error.response?.data as { message?: string; detail?: string } | undefined;
    let errorMessage = responseData?.message || 
                       responseData?.detail || 
                       error.message || 
                       'An unexpected error occurred';

    // Provide specific messages for common HTTP status codes
    if (error.response?.status === 403) {
      errorMessage = 'You do not have permission to perform this action.';
    } else if (error.response?.status === 404) {
      errorMessage = 'The requested resource was not found.';
    } else if (error.response?.status === 500) {
      errorMessage = 'A server error occurred. Please try again later.';
    } else if (error.response?.status === 503) {
      errorMessage = 'The service is temporarily unavailable. Please try again later.';
    }

    return Promise.reject({
      ...error,
      message: errorMessage,
      statusCode: error.response?.status,
    });
  }
);

export default axiosInstance;
