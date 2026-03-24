export interface ToolResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface AgentResponse {
  id: string;
  tenant_id: string;
  name: string;
  role: string;
  description: string;
  tools: ToolResponse[];
  created_at: string;
  updated_at: string;
}

export interface AgentListResponse {
  items: AgentResponse[];
  total: number;
}

export interface ToolListResponse {
  items: ToolResponse[];
  total: number;
}

export interface ExecutionStepResponse {
  id: string;
  step_number: number;
  step_type: string;
  tool_name: string | null;
  tool_input: string | null;
  tool_output: string | null;
  llm_output: string | null;
  created_at: string;
}

export interface RunResponse {
  id: string;
  agent_id: string;
  tenant_id: string;
  model: string;
  task: string;
  structured_prompt: string;
  final_response: string | null;
  status: string;
  steps: ExecutionStepResponse[];
  created_at: string;
}

export interface ExecutionListResponse {
  items: RunResponse[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface ChatSession {
  id: string;
  tenant_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  tenant_id: string;
  role: "user" | "agent";
  content: string;
  agent_name: string | null;
  execution_id: string | null;
  created_at: string;
}

export interface StreamStepEvent {
  step_number: number;
  step_type: string;
  tool_name: string | null;
  tool_input: string | null;
  tool_output: string | null;
  llm_output: string | null;
}

export interface StreamFinalEvent {
  execution_id: string;
  status: string;
  final_response: string | null;
  total_steps: number;
}
