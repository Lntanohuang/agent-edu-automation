export type UserRole = 'partner' | 'lawyer' | 'intern';

export interface UserProfile {
  id: string;
  name: string;
  role: UserRole;
  tenantName: string;
}

export interface CaseItem {
  id: string;
  name: string;
  cause: string;
  stage: string;
  owner: string;
  updatedAt: string;
  hearingDate: string;
  riskScore: number;
  progress: number;
}

export interface WorkbenchTask {
  id: string;
  title: string;
  deadline: string;
  priority: 'high' | 'medium' | 'low';
  assignee: string;
  status: 'todo' | 'processing' | 'done';
}

export interface WorkbenchData {
  cases: CaseItem[];
  tasks: WorkbenchTask[];
}

export interface DocumentItem {
  id: string;
  title: string;
  caseName: string;
  pages: number;
  updatedAt: string;
  uploader: string;
  status: 'pending' | 'processing' | 'ready' | 'failed';
}

export interface TaskItem {
  id: string;
  type: string;
  targetName: string;
  progress: number;
  status: 'queued' | 'processing' | 'success' | 'failed';
  updatedAt: string;
}

export interface CitationItem {
  id: string;
  sourceTitle: string;
  sourceType: 'law' | 'case' | 'case_doc';
  pageNo: number;
  snippet: string;
}

export interface AssistantReply {
  answer: string;
  citations: CitationItem[];
  warning?: string;
}

export interface DraftTemplate {
  id: string;
  name: string;
  type: string;
  description: string;
  lastUsedAt: string;
}

export interface DraftItem {
  id: string;
  title: string;
  caseName: string;
  templateName: string;
  updatedAt: string;
  status: 'draft' | 'reviewing' | 'final';
  content: string;
}

export interface DraftWorkspaceData {
  templates: DraftTemplate[];
  drafts: DraftItem[];
}

export interface ContractClause {
  id: string;
  title: string;
  summary: string;
}

export interface ContractRisk {
  id: string;
  clauseId: string;
  level: 'high' | 'medium' | 'low';
  title: string;
  suggestion: string;
  status: 'pending' | 'accepted' | 'ignored';
  remark?: string;
}

export interface ContractReviewData {
  contractName: string;
  clauses: ContractClause[];
  risks: ContractRisk[];
}

export interface SimilarCaseItem {
  id: string;
  title: string;
  court: string;
  cause: string;
  supportRate: number;
  focus: string;
}

export interface HearingPoint {
  id: string;
  title: string;
  category: '争点' | '举证' | '发问';
  detail: string;
  done: boolean;
}

export interface AnalysisData {
  similarCases: SimilarCaseItem[];
  hearingPoints: HearingPoint[];
}

export interface TaskCenterItem {
  id: string;
  module: string;
  title: string;
  owner: string;
  priority: 'high' | 'medium' | 'low';
  status: 'queued' | 'processing' | 'blocked' | 'success' | 'failed';
  progress: number;
  updatedAt: string;
}

export interface SystemUserItem {
  id: string;
  name: string;
  role: UserRole;
  team: string;
  status: 'active' | 'disabled';
}

export interface SystemSettingItem {
  id: string;
  key: string;
  value: string;
  description: string;
}
