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
