// User types
export interface User {
  id: string;
  username: string;
  email: string;
  role: 'ADMIN' | 'DEVELOPER' | 'VIEWER';
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  role?: 'ADMIN' | 'DEVELOPER' | 'VIEWER';
}

// MCP Tool types
export interface MCPTool {
  id: string;
  name: string;
  slug: string;
  description: string;
  version: string;
  author_id: string;
  status: 'DRAFT' | 'ACTIVE' | 'DEPRECATED';
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CreateToolData {
  name: string;
  slug: string;
  description: string;
  version: string;
  status?: 'DRAFT' | 'ACTIVE' | 'DEPRECATED';
  config: Record<string, any>;
}

export interface UpdateToolData {
  name?: string;
  slug?: string;
  description?: string;
  version?: string;
  status?: 'DRAFT' | 'ACTIVE' | 'DEPRECATED';
  config?: Record<string, any>;
}

export interface ToolVersion {
  version: string;
  changes: Record<string, any>;
  created_at: string;
  author_id: string;
}

// Knowledge base types
export interface Document {
  document_id: string;
  title: string;
  content: string;
  metadata: {
    source?: string;
    tags?: string[];
    language?: string;
    [key: string]: any;
  };
  created_at: string;
  updated_at: string;
}

export interface DocumentData {
  title: string;
  content: string;
  metadata?: {
    source?: string;
    tags?: string[];
    language?: string;
    [key: string]: any;
  };
}

export interface SearchQuery {
  query: string;
  limit?: number;
  threshold?: number;
}

export interface SearchResult {
  document_id: string;
  title: string;
  content: string;
  similarity_score: number;
  metadata: Record<string, any>;
}

export interface SearchResults {
  results: SearchResult[];
  total: number;
}

// Task types
export interface Task {
  task_id: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  progress?: number;
  result?: any;
  error?: string;
  created_at: string;
  completed_at?: string;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  message?: string;
}

export interface TaskStatus {
  task_id: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  progress?: number;
  result?: any;
  error?: string;
}

// AI Analysis types
export interface FeasibilityAnalysisRequest {
  config: Record<string, any>;
}

export interface ImprovementRequest {
  tool_id?: string;
  config?: Record<string, any>;
}

export interface ConfigGenerationRequest {
  requirements: Record<string, any>;
}

// GitHub types
export interface GitHubConnection {
  connection_id: string;
  repository_url: string;
  tool_id: string;
  status: 'CONNECTED' | 'SYNCING' | 'ERROR';
  last_sync?: string;
  created_at: string;
}

export interface ConnectionData {
  repository_url: string;
  access_token: string;
  tool_id?: string;
}

// Deployment types
export interface Deployment {
  deployment_id: string;
  tool_id: string;
  tool_name: string;
  endpoint_url: string;
  status: 'STARTING' | 'RUNNING' | 'STOPPED' | 'FAILED';
  health_status: 'HEALTHY' | 'UNHEALTHY' | 'UNKNOWN';
  deployed_at: string;
  last_health_check?: string;
  metrics?: {
    requests_total: number;
    avg_response_time_ms: number;
    error_rate: number;
  };
}

export interface DeploymentData {
  tool_id: string;
  config?: Record<string, any>;
}

// API Key types
export interface APIKey {
  id: string;
  user_id: string;
  name: string;
  last_used_at?: string;
  expires_at?: string;
  revoked_at?: string;
  created_at: string;
}

export interface CreateKeyData {
  name: string;
  expires_at?: string;
}

export interface APIKeyResponse {
  id: string;
  name: string;
  key: string;
  created_at: string;
  expires_at?: string;
}

// Health types
export interface HealthStatus {
  status: string;
  services: {
    [key: string]: {
      status: 'HEALTHY' | 'UNHEALTHY' | 'UNKNOWN';
      response_time_ms?: number;
      message?: string;
    };
  };
}

// Pagination types
export interface PaginationParams {
  page?: number;
  limit?: number;
  skip?: number;
}

export interface ListParams extends PaginationParams {
  search?: string;
  status?: string;
  sort_by?: string;
  order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}
