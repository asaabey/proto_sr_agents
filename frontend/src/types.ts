export interface ManuscriptQuestion {
    framework?: string;
    population?: string;
    intervention?: string;
    comparator?: string;
    outcomes?: string[];
}

export interface Manuscript {
    manuscript_id?: string;
    title?: string;
    question?: ManuscriptQuestion;
    search?: any[];
    flow?: Record<string, number>;
    included_studies?: any[];
}

export type IssueCategory = 'PICO' | 'PRISMA' | 'STATS' | 'DATA' | 'OTHER';
export type IssueSeverity = 'LOW' | 'MEDIUM' | 'HIGH';

// Backend Issue schema uses: id, severity (lowercase), category, item, evidence (object), recommendation, agent
export interface Issue {
    id: string;
    category: IssueCategory;
    severity: IssueSeverity; // normalized to upper in UI
    title?: string; // optional (backend uses item)
    item?: string;
    evidence?: any;
    recommendation?: string;
    agent?: string;
}

// Backend MetaResult schema: outcome, k, model, pooled, se, ci_low, ci_high, Q, I2, tau2
export interface MetaResult {
    outcome?: string;
    k?: number;
    model?: string;
    pooled?: number;
    se?: number;
    ci_low?: number;
    ci_high?: number;
    Q?: number;
    I2?: number;
    tau2?: number;
    evidence?: any;
}

export interface ReviewResult {
    issues: Issue[];
    meta: MetaResult[];
    extraction_info?: any;
    analysis_metadata?: any;
    manuscript?: Manuscript;
}

export interface StreamEvent {
    event_type: string;
    message: string;
    agent?: string;
    data?: any;
    sequence?: number;
}
