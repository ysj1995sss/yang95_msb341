// Shapes returned by the workspace API (apps/api/app/workspace). They mirror the
// shared Python view models, so the screens make no decisions of their own.

export type Item = { title: string; detail: string; page: string };
export type ChecklistEntry = { label: string; state: "ready" | "attention" | "not_started" | string; detail: string };
export type NextAction = { title: string; why: string; value: string; label: string; page: string; inline: string };

export type HomeView = {
  mode: "first_time" | "returning";
  checklist: ChecklistEntry[];
  completed: number;
  next_action: NextAction;
  drafts: Item[];
  saved_jobs: Item[];
  ready_to_finish: Item[];
  followups_due: Item[];
};

export type HomeResponse = {
  view: HomeView;
  weekly: { week_start: string; week_end: string; applied: number; interviews: number; saved: number };
  recent: Array<{ date: string; role: string; company: string; status: string }>;
  first_name: string;
  weekly_goal: number;
};

export type SectionRow = {
  key: string; name: string; detail: string; status: string; tone: string; action: string; issues: string[];
};

export type Job = {
  employer: string; title: string; dates: string; location?: string | null;
  responsibilities: string[]; accomplishments: string[];
};
export type Education = { degree: string; field: string; institution: string; year: number | null; gpa: string | null };

export type Profile = {
  contact_info: { name?: string; email?: string; phone?: string; location?: string };
  summary?: string;
  work_experience: Job[];
  education: Education[];
  skills: string[];
  tools: string[];
  certifications: string[];
};

export type SavedAnswer = { question_key: string; question: string; answer: string; updated_at: string };

export type WizardStep = { key: string; title: string; help: string; required: boolean };

export type ProfileResponse = {
  readiness: {
    has_resume: boolean; facts_confirmed: boolean; required_ready: number; required_total: number;
    attention: string[]; summary: string;
  };
  rows: SectionRow[];
  first_to_review: string | null;
  attention: string[];
  provenance: Record<string, string>;
  edited: string[];
  profile: Profile;
  links: { linkedin?: string; portfolio?: string; github?: string };
  preferences: {
    job_title?: string; location?: string; relocation_willing?: boolean; remote_preference?: string;
    experience_level?: string[]; min_salary?: number; industries?: string[]; weekly_goal?: number;
  };
  authorization: { authorized_to_work: boolean | null; sponsorship_required: boolean | null };
  no_education: boolean;
  resume: { filename: string; version: number; uploaded_at: string; kind: string } | null;
  resume_versions: number;
  facts_confirmed_at: string | null;
  answers: SavedAnswer[];
  goals_summary: Array<{ label: string; value: string }>;
  goal_options: {
    steps: WizardStep[];
    suggested_titles: string[];
    experience_levels: string[];
    industries: string[];
    work_modes: Array<{ value: string; label: string }>;
  };
};

// --- Jobs (phase 2) ---

export type JobForm = {
  job_title: string; location: string; remote_preference: string; experience_level: string[];
  industries: string[]; min_salary: number; employment_type: string[]; sponsorship_required: boolean;
  relocation_willing: boolean; target_companies: string; exclude_companies: string; sources: string[];
};

export type Option = { value: string; label: string };

export type JobsSetup = {
  form: JobForm; has_goals: boolean; searched: boolean; summary_line: string; suggested_titles: string[];
  board_count: number; saved_count: number;
  options: { experience_levels: string[]; industries: string[]; employment_types: string[]; work_modes: Option[]; sources: Option[] };
};

export type JobRow = {
  job_id: string; title: string; company: string; location: string; work_mode: string; salary: string;
  source: string; is_demo: boolean; freshness: string; quality: string; quality_tone: string;
  fit: string; fit_tone: string; status: string;
};

export type JobsList = {
  view: "best" | "newest" | "saved"; state: string; partial_failure: boolean; source_note: string;
  summary_line: string; searched_at: string | null; coverage_notes: string[]; rows: JobRow[];
  total: number; offset: number;
};

export type Evidence = { requirement: string; evidence: string };

export type AtsExplainerText = { title: string; paragraphs: string[]; terms_note: string; overlap_note: string };

export type JobDetail = {
  row: JobRow; url: string; facts: Array<[string, string]>; strong: Evidence[]; partial: Evidence[];
  gaps: string[]; hard_gates: string[]; unknowns: string[]; fit_parts: Array<[string, string]>; summary: string;
  fit_measured: boolean; keywords: { summary: string; present: string[]; missing: string[] } | null;
  description: string; active: boolean; ats_explainer: AtsExplainerText;
  requirements: { summary: string; rows: number } | null;
};

// --- Tailor (phase 3) ---

export type Decision = "ACCEPTED" | "MANUALLY_EDITED" | "REJECTED";

export type Change = {
  id: string; requirement: string; fact: string; reason: string; original: string; proposed: string;
  check: string; decision: Decision | null; decision_label: string; manual_text: string;
};

export type RequirementRowView = {
  id: string; text: string; status: "direct" | "transferable" | "partial" | "mention" | "unconfirmed" | "check" | "none";
  label: string; tone: "verified" | "primary" | "review" | "blocked"; reason: string; hard_gate: boolean;
  shown_in_resume: boolean | null; evidence: Array<{ text: string; source: string; confirmed: boolean }>;
  terms: Array<{ term: string; status: string; label: string; tone: "verified" | "primary" | "review" | "blocked" }>;
};
export type KeywordReportView = {
  added: Array<{ term: string; change_id: string | null }>; already: string[];
  left_out: Array<{ key: string; label: string; terms: string[] }>; note: string;
};
export type RequirementReviewView = {
  summary: string; computed_from: "run" | "now"; note: string;
  groups: Array<{ section: string; label: string; rows: RequirementRowView[] }>;
};
export type Readability = {
  note: string; items: Array<{ label: string; state: "ok" | "warn" | "fail" | "not_checked"; message: string }>;
};

export type Review = {
  version: number; status: "PASS" | "WARNING" | "FAIL"; status_text: string; status_tone: string; findings: string[];
  fidelity: string; page_count: number | null; preview_pages: number; has_pdf: boolean; has_docx: boolean;
  tailored_text: string; alignment: { before: number | null; after: number | null }; overlap_note: string; sync_summary: string;
  requirement_review: RequirementReviewView | null; readability: Readability; keyword_report: KeywordReportView | null;
  pages_before_after: [number | null, number | null]; unsupported_claims: string[];
  progress: { reviewed: number; total: number; needs_rebuild: boolean; can_continue: boolean; blocker: string; label: string };
  next_undecided: string | null; changes: Change[]; empty_message: string;
  turned_down: Array<{ original: string; reason: string }>; true_gaps: Array<{ label: string; full: string }>;
  blocked: string[]; show_all: boolean; verbs: Record<Decision, string>;
};

export type RunStatus = { status: "idle" | "running" | "done" | "failed"; step?: string; error?: string; job_id?: string };

export type TailorPage = {
  job: { job_id: string; title: string; company: string; fit: number | null } | null;
  resume: { label: string; one_off: boolean } | null;
  model_ready: boolean;
  custom_api_base_allowed: boolean;
  ats_explainer: AtsExplainerText;
  run: RunStatus;
  review: Review | null;
  existing: { version: number; status: string; review_complete: boolean } | null;
};

// --- Apply and Tracker (phase 4) ---

export type CheckItem = { label: string; state: "ok" | "review" | "blocked" | "neutral"; detail: string };
export type ModeOption = { name: string; available: boolean; recommended: boolean; detail: string };
export type KitField = { label: string; value: string; source: string; state: "ready" | "missing" | "optional"; fix: string };

export type ApplyPage = {
  job: { job_id: string; title: string; company: string; url: string } | null;
  empty?: { items: Array<{ label: string; done: boolean }>; action_label: string; action_page: string };
  staged?: Array<{ job_id: string; title: string; company: string }>;
  view?: {
    checklist: CheckItem[]; can_open: boolean; can_track: boolean; can_mark_applied: boolean;
    stage: "not_ready" | "ready" | "tracked" | "applied"; headline: string; modes: ModeOption[];
  };
  handoff?: { version: number; has_file: boolean } | null;
  application_id?: string | null;
  kit?: KitField[];
  kit_summary?: string;
  helper_code?: string;
};

export type TrackerRow = {
  application_id: string; company: string; role: string; status: string; status_label: string;
  applied: string | null; next_action: string; due: string | null; fit: string; resume_version: string;
  source: string; mode: string; last_update: string; url: string;
};

export type TrackerBoard = {
  total: number; views: Array<{ name: string; count: number }>; view: string; rows: TrackerRow[];
  lifecycle: string[]; weekly: { week_start: string; applied: number; interviews: number; saved: number };
  weekly_goal: number; status_options: Option[];
};

export type ApplicationDetail = {
  row: TrackerRow; facts: Array<{ label: string; value: string }>; answers: Array<{ question: string; answer: string }>;
  history: Array<{ when: string; status: string; who: string; note: string }>;
  next_action: { text: string; due: string; notes: string }; job_id: string | null; status_options: Option[];
};

export type GmailStatus = { available: boolean; connected: boolean; connected_at: string | null; last_scan: string | null };
export type GmailSuggestion = {
  message_id: string; subject: string; from: string; email_date: string | null; status: string; status_label: string;
  phrase: string; chosen: string | null; options: Array<{ application_id: string; label: string; backwards: boolean }>;
};

export type EmailReading = {
  status: string | null; status_label: string; phrase: string; chosen: string | null; email_date: string | null;
  subject: string; options: Array<{ application_id: string; label: string; matched: boolean; backwards: boolean }>;
};
