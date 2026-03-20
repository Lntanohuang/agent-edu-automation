import type {
  AnalysisData,
  AssistantReply,
  CaseItem,
  CitationItem,
  ContractReviewData,
  DraftWorkspaceData,
  DocumentItem,
  SystemSettingItem,
  SystemUserItem,
  TaskCenterItem,
  TaskItem,
  WorkbenchData,
  WorkbenchTask
} from '@/types';

const mockCases: CaseItem[] = [
  {
    id: 'case-001',
    name: '华晨设备买卖合同纠纷',
    cause: '买卖合同纠纷',
    stage: '一审审理中',
    owner: '李律师',
    updatedAt: '2026-02-20 17:20',
    hearingDate: '2026-03-08',
    riskScore: 72,
    progress: 64
  },
  {
    id: 'case-002',
    name: '南湾科技劳动争议案',
    cause: '劳动争议',
    stage: '庭前准备',
    owner: '王实习生',
    updatedAt: '2026-02-23 10:15',
    hearingDate: '2026-03-12',
    riskScore: 51,
    progress: 48
  },
  {
    id: 'case-003',
    name: '云海传媒侵权责任纠纷',
    cause: '侵权责任纠纷',
    stage: '文书提交',
    owner: '陈合伙人',
    updatedAt: '2026-02-21 14:45',
    hearingDate: '2026-03-19',
    riskScore: 63,
    progress: 82
  }
];

const mockTasks: WorkbenchTask[] = [
  {
    id: 'wt-001',
    title: '核对交货验收单与付款节点',
    deadline: '2026-02-26 18:00',
    priority: 'high',
    assignee: '李律师',
    status: 'processing'
  },
  {
    id: 'wt-002',
    title: '补充类案裁判要旨 3 条',
    deadline: '2026-02-27 12:00',
    priority: 'medium',
    assignee: '王实习生',
    status: 'todo'
  },
  {
    id: 'wt-003',
    title: '形成庭审发问提纲初稿',
    deadline: '2026-02-28 20:00',
    priority: 'high',
    assignee: '陈合伙人',
    status: 'todo'
  }
];

const mockDocs: DocumentItem[] = [
  {
    id: 'doc-001',
    title: '买卖合同主协议.pdf',
    caseName: '华晨设备买卖合同纠纷',
    pages: 24,
    updatedAt: '2026-02-23 11:20',
    uploader: '李律师',
    status: 'ready'
  },
  {
    id: 'doc-002',
    title: '交货验收单据汇编.pdf',
    caseName: '华晨设备买卖合同纠纷',
    pages: 56,
    updatedAt: '2026-02-23 12:10',
    uploader: '王实习生',
    status: 'processing'
  },
  {
    id: 'doc-003',
    title: '劳动仲裁申请书.pdf',
    caseName: '南湾科技劳动争议案',
    pages: 17,
    updatedAt: '2026-02-22 16:30',
    uploader: '陈合伙人',
    status: 'pending'
  }
];

const mockPipelineTasks: TaskItem[] = [
  {
    id: 'task-001',
    type: '文档解析',
    targetName: '交货验收单据汇编.pdf',
    progress: 65,
    status: 'processing',
    updatedAt: '2026-02-24 09:45'
  },
  {
    id: 'task-002',
    type: '向量入库',
    targetName: '买卖合同主协议.pdf',
    progress: 100,
    status: 'success',
    updatedAt: '2026-02-24 09:10'
  },
  {
    id: 'task-003',
    type: '合同审阅',
    targetName: '劳动仲裁申请书.pdf',
    progress: 0,
    status: 'queued',
    updatedAt: '2026-02-24 09:50'
  }
];

const mockDraftWorkspace: DraftWorkspaceData = {
  templates: [
    {
      id: 'tpl-001',
      name: '民事起诉状',
      type: '诉讼文书',
      description: '适用于合同违约、侵权纠纷等一般民事一审案件。',
      lastUsedAt: '2026-02-24 09:10'
    },
    {
      id: 'tpl-002',
      name: '答辩状',
      type: '诉讼文书',
      description: '用于被告方答辩，支持争点与证据分段生成。',
      lastUsedAt: '2026-02-21 18:40'
    },
    {
      id: 'tpl-003',
      name: '律师函',
      type: '函件',
      description: '用于催告履约、违约责任通知与谈判前置沟通。',
      lastUsedAt: '2026-02-20 11:30'
    }
  ],
  drafts: [
    {
      id: 'dr-001',
      title: '华晨设备买卖合同纠纷起诉状（初稿）',
      caseName: '华晨设备买卖合同纠纷',
      templateName: '民事起诉状',
      updatedAt: '2026-02-24 10:20',
      status: 'reviewing',
      content:
        '诉讼请求：\n1. 判令被告支付拖欠货款人民币 1,260,000 元；\n2. 判令被告承担逾期付款违约金；\n3. 本案诉讼费用由被告承担。\n\n事实与理由：\n原告与被告于 2025 年 6 月签订《设备买卖合同》，约定设备验收合格后 15 个工作日内支付尾款。现设备已验收，但被告逾期未付款。'
    },
    {
      id: 'dr-002',
      title: '南湾科技劳动争议案答辩意见（草稿）',
      caseName: '南湾科技劳动争议案',
      templateName: '答辩状',
      updatedAt: '2026-02-22 17:45',
      status: 'draft',
      content:
        '答辩要点：\n1. 申请人的加班事实尚缺完整考勤链条；\n2. 绩效扣减依据已在员工手册与告知确认中明确；\n3. 经济补偿金计算口径存在重复主张。'
    }
  ]
};

const mockContractReviewData: ContractReviewData = {
  contractName: '供应链采购框架合同（2026版）',
  clauses: [
    {
      id: 'clause-001',
      title: '4.2 付款条款',
      summary: '约定验收后 90 日内付款，未明确逾期利息标准。'
    },
    {
      id: 'clause-002',
      title: '7.1 违约责任',
      summary: '违约金比例固定为合同总额 5%，未区分违约情形。'
    },
    {
      id: 'clause-003',
      title: '10.3 争议解决',
      summary: '约定提交甲方所在地仲裁委，未明确仲裁规则版本。'
    }
  ],
  risks: [
    {
      id: 'risk-001',
      clauseId: 'clause-001',
      level: 'high',
      title: '回款周期过长且利息标准缺失',
      suggestion: '建议将付款期调整为 30 日，并补充逾期付款按 LPR 上浮比例计息。',
      status: 'pending'
    },
    {
      id: 'risk-002',
      clauseId: 'clause-002',
      level: 'medium',
      title: '违约金条款未分层',
      suggestion: '按交付违约、付款违约、保密违约分别设置违约责任与上限。',
      status: 'pending'
    },
    {
      id: 'risk-003',
      clauseId: 'clause-003',
      level: 'low',
      title: '仲裁规则描述不完整',
      suggestion: '补充具体仲裁规则版本及仲裁语言，避免程序争议。',
      status: 'accepted',
      remark: '客户接受补充版本号。'
    }
  ]
};

const mockAnalysisData: AnalysisData = {
  similarCases: [
    {
      id: 'sc-001',
      title: '某设备公司诉某制造公司买卖合同纠纷案',
      court: '上海一中院',
      cause: '买卖合同纠纷',
      supportRate: 84,
      focus: '验收完成后逾期付款责任的认定标准'
    },
    {
      id: 'sc-002',
      title: '某科技公司诉某贸易公司合同纠纷案',
      court: '江苏高院',
      cause: '合同纠纷',
      supportRate: 69,
      focus: '违约金过高时的酌减路径'
    },
    {
      id: 'sc-003',
      title: '某材料公司诉某建设公司买卖合同纠纷案',
      court: '浙江高院',
      cause: '买卖合同纠纷',
      supportRate: 73,
      focus: '验收单证据链完整性对胜诉影响'
    }
  ],
  hearingPoints: [
    {
      id: 'hp-001',
      title: '确认验收是否完成',
      category: '争点',
      detail: '准备验收报告、签收单及项目交付邮件，锁定验收时间点。',
      done: true
    },
    {
      id: 'hp-002',
      title: '逾期付款证据链',
      category: '举证',
      detail: '整理应收账款台账、催款函、对账确认函与回执。',
      done: false
    },
    {
      id: 'hp-003',
      title: '针对抗辩的发问提纲',
      category: '发问',
      detail: '围绕“是否收到发票”“是否存在质量异议”设计封闭式发问。',
      done: false
    }
  ]
};

const mockTaskCenter: TaskCenterItem[] = [
  {
    id: 'tc-001',
    module: '文档入库',
    title: '交货验收单据汇编 PDF 解析',
    owner: '王实习生',
    priority: 'high',
    status: 'processing',
    progress: 65,
    updatedAt: '2026-02-24 09:45'
  },
  {
    id: 'tc-002',
    module: '检索问答',
    title: '买卖合同纠纷问答回归集评测',
    owner: '李律师',
    priority: 'medium',
    status: 'queued',
    progress: 0,
    updatedAt: '2026-02-24 10:03'
  },
  {
    id: 'tc-003',
    module: '合同审阅',
    title: '供应链采购框架合同批量审阅',
    owner: '陈合伙人',
    priority: 'high',
    status: 'blocked',
    progress: 38,
    updatedAt: '2026-02-24 10:12'
  },
  {
    id: 'tc-004',
    module: '文书',
    title: '华晨设备案起诉状导出',
    owner: '李律师',
    priority: 'low',
    status: 'success',
    progress: 100,
    updatedAt: '2026-02-24 08:58'
  }
];

const mockSystemUsers: SystemUserItem[] = [
  {
    id: 'su-001',
    name: '陈合伙人',
    role: 'partner',
    team: '民商事一组',
    status: 'active'
  },
  {
    id: 'su-002',
    name: '李律师',
    role: 'lawyer',
    team: '民商事一组',
    status: 'active'
  },
  {
    id: 'su-003',
    name: '王实习生',
    role: 'intern',
    team: '民商事一组',
    status: 'active'
  }
];

const mockSystemSettings: SystemSettingItem[] = [
  {
    id: 'ss-001',
    key: 'answer.citation.required',
    value: 'true',
    description: '回答必须附带引用依据'
  },
  {
    id: 'ss-002',
    key: 'export.word.enabled',
    value: 'true',
    description: '启用文书一键 Word 导出'
  },
  {
    id: 'ss-003',
    key: 'audit.log.retention.days',
    value: '180',
    description: '审计日志保留天数'
  }
];

function wait(milliseconds: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}

function buildCitations(mode: 'library' | 'case', caseId?: string): CitationItem[] {
  const baseCitations: CitationItem[] = [
    {
      id: 'ct-001',
      sourceTitle: '《中华人民共和国民法典》第五百七十七条',
      sourceType: 'law',
      pageNo: 1,
      snippet: '当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。'
    },
    {
      id: 'ct-002',
      sourceTitle: '最高人民法院公报案例（2024）民商终字第12号',
      sourceType: 'case',
      pageNo: 7,
      snippet: '判定违约责任时，应当结合实际履行情况与合同目的实现程度综合判断。'
    }
  ];

  if (mode === 'case' && caseId) {
    baseCitations.push({
      id: 'ct-003',
      sourceTitle: '买卖合同主协议.pdf',
      sourceType: 'case_doc',
      pageNo: 14,
      snippet: '乙方应于验收合格后十五个工作日内支付尾款。'
    });
  }

  return baseCitations;
}

export async function fetchWorkbenchData(): Promise<WorkbenchData> {
  await wait(400);
  return {
    cases: mockCases,
    tasks: mockTasks
  };
}

export async function fetchCases(): Promise<CaseItem[]> {
  await wait(250);
  return mockCases;
}

export async function fetchDocuments(): Promise<DocumentItem[]> {
  await wait(300);
  return mockDocs;
}

export async function fetchPipelineTasks(): Promise<TaskItem[]> {
  await wait(320);
  return mockPipelineTasks;
}

export async function askAssistant(payload: {
  question: string;
  mode: 'library' | 'case';
  caseId?: string;
}): Promise<AssistantReply> {
  await wait(700);
  const citations = buildCitations(payload.mode, payload.caseId);
  const withCaseContext = payload.mode === 'case' && payload.caseId;
  const answer = withCaseContext
    ? `基于当前案件材料与公开法条，现阶段可主张对方存在逾期付款违约，建议在诉请中明确违约金计算起点，并补充验收日期证据。`
    : `基于公开法规和案例，建议先确认违约事实、损失证据与违约责任条款适配性，再形成书面法律意见。`;

  const warning =
    payload.question.length < 8
      ? '问题描述较短，建议补充争议焦点、合同条款编号或证据编号以提升结论确定性。'
      : undefined;

  return {
    answer,
    citations,
    warning
  };
}

export async function fetchDraftWorkspaceData(): Promise<DraftWorkspaceData> {
  await wait(320);
  return mockDraftWorkspace;
}

export async function fetchContractReviewData(): Promise<ContractReviewData> {
  await wait(360);
  return mockContractReviewData;
}

export async function fetchAnalysisData(): Promise<AnalysisData> {
  await wait(340);
  return mockAnalysisData;
}

export async function fetchTaskCenterData(): Promise<TaskCenterItem[]> {
  await wait(280);
  return mockTaskCenter;
}

export async function fetchSystemUsers(): Promise<SystemUserItem[]> {
  await wait(260);
  return mockSystemUsers;
}

export async function fetchSystemSettings(): Promise<SystemSettingItem[]> {
  await wait(260);
  return mockSystemSettings;
}
