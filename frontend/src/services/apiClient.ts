import axiosInstance from '../lib/axios';
import type {
  User,
  TokenResponse,
  LoginCredentials,
  RegisterData,
  MCPTool,
  CreateToolData,
  UpdateToolData,
  ToolVersion,
  Document,
  DocumentData,
  SearchQuery,
  SearchResults,
  TaskResponse,
  TaskStatus,
  GitHubConnection,
  ConnectionData,
  Deployment,
  DeploymentData,
  APIKey,
  CreateKeyData,
  APIKeyResponse,
  HealthStatus,
  ListParams,
  PaginatedResponse,
  ExecutionLog,
} from '../types';

/**
 * API Client for MCP Platform
 * Provides methods to interact with all backend endpoints
 */
class APIClient {
  /**
   * Authentication API methods
   */
  auth = {
    /**
     * Register a new user
     */
    register: async (data: RegisterData): Promise<User> => {
      const response = await axiosInstance.post<User>('/api/v1/auth/register', data);
      return response.data;
    },

    /**
     * Login with username and password
     */
    login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
      const response = await axiosInstance.post<TokenResponse>('/api/v1/auth/login', {
        username: credentials.username,
        password: credentials.password,
      });
      return response.data;
    },

    /**
     * Refresh access token
     */
    refresh: async (refreshToken: string): Promise<TokenResponse> => {
      const response = await axiosInstance.post<TokenResponse>('/api/v1/auth/refresh', {
        refresh_token: refreshToken,
      });
      return response.data;
    },

    /**
     * Logout user
     */
    logout: async (refreshToken: string): Promise<void> => {
      await axiosInstance.post('/api/v1/auth/logout', {
        refresh_token: refreshToken,
      });
    },
  };

  /**
   * MCP Tools API methods
   */
  tools = {
    /**
     * List all MCP tools with pagination and filters
     */
    list: async (params?: ListParams): Promise<PaginatedResponse<MCPTool>> => {
      const response = await axiosInstance.get<PaginatedResponse<MCPTool>>('/api/v1/mcps', {
        params,
      });
      return response.data;
    },

    /**
     * Get a specific MCP tool by ID
     */
    get: async (id: string): Promise<MCPTool> => {
      const response = await axiosInstance.get<MCPTool>(`/api/v1/mcps/${id}`);
      return response.data;
    },

    /**
     * Create a new MCP tool
     */
    create: async (data: CreateToolData): Promise<MCPTool> => {
      const response = await axiosInstance.post<MCPTool>('/api/v1/mcps', data);
      return response.data;
    },

    /**
     * Update an existing MCP tool
     */
    update: async (id: string, data: UpdateToolData): Promise<MCPTool> => {
      const response = await axiosInstance.put<MCPTool>(`/api/v1/mcps/${id}`, data);
      return response.data;
    },

    /**
     * Delete an MCP tool
     */
    delete: async (id: string): Promise<void> => {
      await axiosInstance.delete(`/api/v1/mcps/${id}`);
    },

    /**
     * Get version history for a tool
     */
    getHistory: async (id: string): Promise<ToolVersion[]> => {
      const response = await axiosInstance.get<ToolVersion[]>(`/api/v1/mcps/${id}/history`);
      return response.data;
    },

    /**
     * Execute an MCP tool
     */
    execute: async (
      id: string,
      data: {
        tool_name: string;
        arguments: Record<string, any>;
        timeout?: number;
      }
    ): Promise<{
      execution_id: string;
      tool_id: string;
      tool_name: string;
      status: string;
      result: Record<string, any>;
      executed_at: string;
    }> => {
      const response = await axiosInstance.post(`/api/v1/mcps/${id}/execute`, data);
      return response.data;
    },

    /**
     * Get execution history for a specific tool
     */
    getExecutionHistory: async (
      toolId: string,
      limit?: number
    ): Promise<ExecutionLog[]> => {
      const response = await axiosInstance.get<ExecutionLog[]>(
        `/api/v1/mcps/${toolId}/executions`,
        {
          params: { limit: limit || 50 },
        }
      );
      return response.data;
    },
  };

  /**
   * Knowledge Base API methods
   */
  knowledge = {
    /**
     * Upload a document to the knowledge base
     */
    uploadDocument: async (data: DocumentData): Promise<Document> => {
      const response = await axiosInstance.post<Document>('/api/v1/knowledge/documents', data);
      return response.data;
    },

    /**
     * Get a specific document by ID
     */
    getDocument: async (id: string): Promise<Document> => {
      const response = await axiosInstance.get<Document>(`/api/v1/knowledge/documents/${id}`);
      return response.data;
    },

    /**
     * Delete a document
     */
    deleteDocument: async (id: string): Promise<void> => {
      await axiosInstance.delete(`/api/v1/knowledge/documents/${id}`);
    },

    /**
     * Search documents using semantic search
     */
    search: async (query: SearchQuery): Promise<SearchResults> => {
      const response = await axiosInstance.post<SearchResults>('/api/v1/knowledge/search', query);
      return response.data;
    },

    /**
     * List all documents
     */
    listDocuments: async (params?: ListParams): Promise<PaginatedResponse<Document>> => {
      const response = await axiosInstance.get<PaginatedResponse<Document>>('/api/v1/knowledge/documents', {
        params,
      });
      return response.data;
    },
  };

  /**
   * AI Analysis API methods
   */
  analysis = {
    /**
     * Analyze feasibility of a configuration
     */
    analyzeFeasibility: async (config: Record<string, any>): Promise<TaskResponse> => {
      const response = await axiosInstance.post<TaskResponse>('/api/v1/analyze/feasibility', {
        config,
      });
      return response.data;
    },

    /**
     * Get improvement suggestions for a tool
     */
    getImprovements: async (data: { tool_name: string; description: string; config: Record<string, any> }): Promise<TaskResponse> => {
      const response = await axiosInstance.post<TaskResponse>('/api/v1/analyze/improvements', data);
      return response.data;
    },

    /**
     * Generate configuration from requirements
     */
    generateConfig: async (requirements: Record<string, any>): Promise<TaskResponse> => {
      const response = await axiosInstance.post<TaskResponse>('/api/v1/analyze/generate-config', requirements);
      return response.data;
    },

    /**
     * Get task status
     */
    getTaskStatus: async (taskId: string): Promise<TaskStatus> => {
      const response = await axiosInstance.get<TaskStatus>(`/api/v1/tasks/${taskId}`);
      return response.data;
    },
  };

  /**
   * GitHub Integration API methods
   */
  github = {
    /**
     * Connect a GitHub repository
     */
    connect: async (data: ConnectionData): Promise<GitHubConnection> => {
      const response = await axiosInstance.post<GitHubConnection>('/api/v1/github/connect', data);
      return response.data;
    },

    /**
     * Disconnect a GitHub repository
     */
    disconnect: async (id: string): Promise<void> => {
      await axiosInstance.delete(`/api/v1/github/disconnect/${id}`);
    },

    /**
     * Sync a GitHub repository
     */
    sync: async (id: string): Promise<TaskResponse> => {
      const response = await axiosInstance.post<TaskResponse>(`/api/v1/github/sync/${id}`);
      return response.data;
    },

    /**
     * List all GitHub connections
     */
    listConnections: async (): Promise<GitHubConnection[]> => {
      const response = await axiosInstance.get<GitHubConnection[]>('/api/v1/github/connections');
      return response.data;
    },
  };

  /**
   * Deployment API methods
   */
  deployments = {
    /**
     * List all deployments
     */
    list: async (params?: ListParams): Promise<Deployment[]> => {
      const response = await axiosInstance.get<Deployment[]>('/api/v1/deployments', {
        params,
      });
      return response.data;
    },

    /**
     * Get a specific deployment by ID
     */
    get: async (id: string): Promise<Deployment> => {
      const response = await axiosInstance.get<Deployment>(`/api/v1/deployments/${id}`);
      return response.data;
    },

    /**
     * Create a new deployment
     */
    create: async (data: DeploymentData): Promise<Deployment> => {
      const response = await axiosInstance.post<Deployment>('/api/v1/deployments', data);
      return response.data;
    },

    /**
     * Stop a deployment
     */
    stop: async (id: string): Promise<void> => {
      await axiosInstance.post(`/api/v1/deployments/${id}/stop`);
    },

    /**
     * Get deployment logs
     */
    getLogs: async (id: string, lines?: number): Promise<string[]> => {
      const response = await axiosInstance.get<{ logs: string[] }>(`/api/v1/deployments/${id}/logs`, {
        params: { lines },
      });
      return response.data.logs;
    },
  };

  /**
   * API Keys API methods
   */
  apiKeys = {
    /**
     * List all API keys for the current user
     */
    list: async (): Promise<APIKey[]> => {
      const response = await axiosInstance.get<APIKey[]>('/api/v1/auth/api-keys');
      return response.data;
    },

    /**
     * Create a new API key
     */
    create: async (data: CreateKeyData): Promise<APIKeyResponse> => {
      const response = await axiosInstance.post<APIKeyResponse>('/api/v1/auth/api-keys', data);
      return response.data;
    },

    /**
     * Revoke an API key
     */
    revoke: async (id: string): Promise<void> => {
      await axiosInstance.delete(`/api/v1/auth/api-keys/${id}`);
    },
  };

  /**
   * Health Check API methods
   */
  health = {
    /**
     * Check system health status
     */
    check: async (): Promise<HealthStatus> => {
      const response = await axiosInstance.get<HealthStatus>('/api/v1/health');
      return response.data;
    },
  };

  /**
   * Execution API methods
   */
  executions = {
    /**
     * Get execution status by ID
     */
    getStatus: async (executionId: string): Promise<{
      execution_id: string;
      status: string;
      progress?: number;
      metadata?: Record<string, any>;
      result?: Record<string, any>;
      error?: string;
    }> => {
      const response = await axiosInstance.get(`/api/v1/executions/${executionId}/status`);
      return response.data;
    },

    /**
     * Get execution details by ID
     */
    get: async (executionId: string): Promise<{
      execution_id: string;
      tool_id: string;
      tool_name: string;
      status: string;
      result?: Record<string, any>;
      error?: string;
      started_at: string;
      completed_at?: string;
      duration_ms?: number;
    }> => {
      const response = await axiosInstance.get(`/api/v1/executions/${executionId}`);
      return response.data;
    },

    /**
     * Cancel an execution
     */
    cancel: async (executionId: string): Promise<void> => {
      await axiosInstance.delete(`/api/v1/executions/${executionId}`);
    },

    /**
     * Get execution logs
     */
    getLogs: async (executionId: string): Promise<{
      logs: Array<{
        timestamp: string;
        level: string;
        message: string;
      }>;
    }> => {
      const response = await axiosInstance.get(`/api/v1/executions/${executionId}/logs`);
      return response.data;
    },
  };
}

// Export singleton instance
export const apiClient = new APIClient();
export default apiClient;
