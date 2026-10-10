/**
 * User and Authentication type contracts matching FastAPI backend schemas
 */

export type UserRole = 'frontline_agent' | 'tier2_supervisor' | 'senior_supervisor'

export interface UserResponse {
  id: number
  username: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserResponse
}

export interface AuthContextType {
  user: UserResponse | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  role: UserRole | null
  login: (credentials: LoginRequest) => Promise<UserResponse>
  logout: () => void
  refreshProfile: () => Promise<void>
}
