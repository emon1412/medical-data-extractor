export type OrderStatus = "pending" | "processing" | "completed" | "cancelled";

export interface Address {
  line1?: string | null;
  line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
}

export interface Prescriber {
  name?: string | null;
  npi?: string | null;
  phone?: string | null;
  fax?: string | null;
  address?: Address | null;
}

export interface Diagnosis {
  code?: string | null;
  description?: string | null;
}

export interface OrderedItem {
  code?: string | null;
  description?: string | null;
  side?: string | null;
  quantity?: number | null;
}

export interface DocumentDetails {
  document_type?: string | null;
  order_date?: string | null;
  patient_address?: Address | null;
  prescriber?: Prescriber | null;
  diagnoses: Diagnosis[];
  items: OrderedItem[];
}

export interface Order {
  id: string;
  patient_id: string | null;
  patient_first_name: string;
  patient_last_name: string;
  patient_dob: string | null;
  status: OrderStatus;
  notes: string | null;
  source_document_name: string | null;
  extraction_confidence: string | null;
  document_metadata: DocumentDetails | null;
  created_at: string;
  updated_at: string;
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  dob: string | null;
  order_count: number;
  created_at: string;
  updated_at: string;
}

export interface PatientListResponse {
  items: Patient[];
  total: number;
  limit: number;
  offset: number;
}

export interface OrderListResponse {
  items: Order[];
  total: number;
  limit: number;
  offset: number;
}

export interface OrderCreate {
  patient_first_name: string;
  patient_last_name: string;
  patient_dob?: string | null;
  status?: OrderStatus;
  notes?: string | null;
}

export interface OrderUpdate {
  patient_first_name?: string;
  patient_last_name?: string;
  patient_dob?: string | null;
  status?: OrderStatus;
  notes?: string | null;
}

export interface PatientExtraction {
  first_name: string | null;
  last_name: string | null;
  date_of_birth: string | null;
  confidence: "high" | "medium" | "low" | string;
  source: string;
  document: DocumentDetails | null;
}

export interface ExtractionResponse {
  extracted: PatientExtraction;
  raw_text_preview: string;
  order_id: string | null;
}

export interface ActivityLog {
  id: string;
  method: string;
  path: string;
  status_code: number;
  duration_ms: number;
  action: string | null;
  resource_type: string | null;
  resource_id: string | null;
  actor: string | null;
  client_ip: string | null;
  user_agent: string | null;
  request_id: string | null;
  error_message: string | null;
  created_at: string;
}

export interface ActivityLogListResponse {
  items: ActivityLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiError {
  error: {
    type: string;
    message: string;
    status_code: number;
    details?: unknown;
    request_id?: string;
  };
}
