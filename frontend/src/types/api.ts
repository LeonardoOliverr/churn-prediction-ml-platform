// ── Health ────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok' | 'degraded'
  version: string
  timestamp: string
  latency_ms: number
}

export interface HealthCheckDetail {
  status: 'ok' | 'degraded'
  latency_ms: number
}

export interface HealthReadyResponse {
  status: 'ready' | 'degraded'
  timestamp: string
  checks: {
    database: HealthCheckDetail
    mlflow: HealthCheckDetail
  }
}

// ── Tenant & Project ──────────────────────────────────────────────────────────

export interface TenantCreate {
  name: string
  slug: string
}

export interface TenantResponse {
  id: string
  name: string
  slug: string
}

export interface ProjectCreate {
  tenant_id: string
  name: string
  slug: string
}

export interface ProjectResponse {
  id: string
  tenant_id: string
  name: string
  slug: string
}

// ── API Keys ──────────────────────────────────────────────────────────────────

export type ApiScope = 'predict' | 'predictions:read'

export interface ApiKeyCreate {
  tenant_id: string
  project_id?: string | null
  scopes?: ApiScope[]
  description?: string
  expires_at?: string | null
}

export interface ApiKeyResponse {
  id: string
  key_prefix: string
  secret: string
  tenant_id: string
  project_id?: string | null
  scopes: string[]
  expires_at?: string | null
}

export interface ApiKeyRecord {
  id: string
  key_prefix: string
  tenant_id: string
  project_id?: string | null
  scopes: string[]
  is_active: boolean
  created_at: string
  expires_at?: string | null
  last_used_at?: string | null
}

// ── Model Config ──────────────────────────────────────────────────────────────

export type ModelRole = 'champion' | 'challenger'

export interface ProjectModelConfigRecord {
  id: string
  tenant_id: string
  project_id?: string | null
  model_id: string
  model_name: string
  model_version: string
  model_status: string
  role: ModelRole
  threshold: number
  traffic_split: number
  is_active: boolean
  environment: string
  configured_by?: string
  description?: string
  activation_reason?: string
  configured_at: string
  deactivated_at?: string | null
  created_at: string
  updated_at: string
}

export interface ProjectModelConfigResponse {
  config: ProjectModelConfigRecord
}

export interface ProjectModelConfigListResponse {
  champion: ProjectModelConfigRecord | null
  challenger: ProjectModelConfigRecord | null
  history: ProjectModelConfigRecord[]
}

export interface ChampionModelConfigure {
  model_id: string
  threshold?: number
  activation_reason?: string
  description?: string
}

export interface ChallengerModelConfigure {
  model_id: string
  threshold?: number
  traffic_split: number
  activation_reason?: string
  description?: string
}

export interface ModelPromotionRequest {
  activation_reason?: string
}

export interface ModelDeactivationRequest {
  reason: string
  replacement_model_id?: string
}

// ── Predictions ───────────────────────────────────────────────────────────────

export type RiskLevel = 'low' | 'medium' | 'high'

export interface CustomerFeatures {
  customer_id: string
  tenure_months: number
  monthly_charges: number
  total_charges: number
  senior_citizen: 0 | 1
  partner: 0 | 1
  dependents: 0 | 1
  phone_service: 0 | 1
  paperless_billing: 0 | 1
  gender: 'Male' | 'Female'
  multiple_lines: 'No' | 'Yes' | 'No phone service'
  internet_service: 'DSL' | 'Fiber optic' | 'No'
  online_security: 'No' | 'Yes' | 'No internet service'
  online_backup: 'No' | 'Yes' | 'No internet service'
  device_protection: 'No' | 'Yes' | 'No internet service'
  tech_support: 'No' | 'Yes' | 'No internet service'
  streaming_tv: 'No' | 'Yes' | 'No internet service'
  streaming_movies: 'No' | 'Yes' | 'No internet service'
  contract: 'Month-to-month' | 'One year' | 'Two year'
  payment_method:
    | 'Electronic check'
    | 'Mailed check'
    | 'Bank transfer (automatic)'
    | 'Credit card (automatic)'
}

export interface PredictResponse {
  prediction_id: string
  customer_id: string
  churn_probability: number
  risk_level: RiskLevel
  churn_pred: boolean
  threshold_used: number
  model_version: string
  model_name: string
  model_id: string
}

export interface BatchPredictRequest {
  customers: CustomerFeatures[]
}

export interface BatchPredictResponse {
  results: PredictResponse[]
  total: number
}

export interface PredictionRecord {
  id: string
  customer_id: string
  churn_probability: number
  churn_pred: boolean
  threshold_used: number
  latency_ms?: number | null
  requested_at: string
  model_id: string
}

export interface PredictionsListResponse {
  items: PredictionRecord[]
  total: number
  page: number
  page_size: number
}

// ── Error response ────────────────────────────────────────────────────────────

export interface ApiError {
  error: string
  message: string
  request_id?: string
}
