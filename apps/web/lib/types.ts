export interface ActionEvaluation {
  action: string;
  eligible: boolean;
  economically_viable: boolean;
  is_selected: boolean;
  expected_net_recovery: string | null;
  success_probability: number | null;
  intervention_cost: string | null;
  why_not: string | null;
}

export interface AuditEvent {
  id: number;
  event_type: string;
  occurred_at: string | null;
  actor: string | null;
  action: string | null;
  status: string | null;
  message: string | null;
}

export interface ExecutionDetails {
  execution_id: string;
  action: string;
  status: string | null;
  provider_reference: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface PolicyDecisionDetails {
  decision: string;
  approved: boolean;
  reasons: string[];
  constraints: Record<string, any>;
}

export interface DecisionSnapshot {
  recoverable_amount: string | null;
  currency: string | null;
  diagnosis: string | null;
  diagnosis_confidence: string | null;
  recommended_action: string | null;
  decision: string | null;
  decision_rationale: string | null;
  policy: PolicyDecisionDetails | null;
  context_version: number | null;
  action_evaluations: ActionEvaluation[];
}

export interface CurrentState {
  recoverable_amount: string | null;
  currency: string | null;
  payment_state: string | null;
  case_status: string;
  verification_outcome: string | null;
}

export interface ExecutiveSummaryDetails {
  text: string;
  provider: string;
  authoritative: boolean;
}

export interface RecoveryCaseDetails {
  case_id: number;
  status: string;
  version: number;
  merchant_id: number;
  customer_id: number | null;
  order_id: number | null;
  order_external_id: string | null;
  payment_id: number | null;
  provider_payment_id: string | null;
  decision_snapshot?: DecisionSnapshot;
  current_state?: CurrentState;
  executive_summary?: ExecutiveSummaryDetails;
  diagnosis: string | null;
  diagnosis_confidence: string | null;
  recoverable_amount: string | null;
  currency: string | null;
  recommended_action: string | null;
  decision: string | null;
  decision_rationale: string | null;
  context_version: number | null;
  policy_decision: PolicyDecisionDetails | null;
  execution: ExecutionDetails | null;
  verification_outcome: string | null;
  created_at: string | null;
  updated_at: string | null;
  action_evaluations: ActionEvaluation[];
  audit_events: AuditEvent[];
}

export interface DemoScenarioResponse {
  status: string;
  scenario: string;
  demo_run_id?: string;
  case_id: number | null;
  case_status: string | null;
  merchant_id?: number;
  order_external_id?: string;
  provider_payment_id?: string;
  amount?: string;
  currency?: string;
  recommended_action?: string | null;
  verification_outcome?: string | null;
  payment_state?: string | null;
}

export interface MerchantOverviewCounts {
  total_cases: number;
  active_cases: number;
  verifying_cases: number;
  recovered_cases: number;
  no_action_cases: number;
  failed_cases: number;
}

export interface MerchantOverviewAggregates {
  revenue_at_risk: string;
  recovered_amount: string;
  expected_recovery: string;
  capital_preserved: string;
  currency: string;
}

export interface MerchantOverviewCaseItem {
  case_id: number;
  customer_display: string;
  order_external_id: string;
  provider_payment_id: string;
  recoverable_amount: string;
  current_at_risk_amount: string;
  currency: string;
  diagnosis: string | null;
  recommended_action: string | null;
  status: string;
  verification_outcome: string | null;
  created_at: string | null;
  updated_at: string | null;
  decision_expected_net_recovery: string | null;
}

export interface MerchantRecoveryOverviewResponse {
  merchant_id: number;
  counts: MerchantOverviewCounts;
  aggregates: MerchantOverviewAggregates;
  cases: MerchantOverviewCaseItem[];
}
