export type AssignmentType = "essay" | "pg" | "pdf" | "docx";
export type ReleaseMode = "review" | "langsung";

export type RubricCriterion = {
  id: string;
  assignment_id: string;
  position: number;
  name: string;
  weight: number;
  level_1: string;
  level_2: string;
  level_3: string;
  level_4: string;
  prompt_notes: string;
};

export type GradeCriterion = {
  criterion_id: string;
  name: string;
  weight: number;
  score: number;
  quote: string;
  comment: string;
};

export type GradeSource = "model" | "manual" | "empty" | "code";

export type GradeData = {
  criteria: GradeCriterion[];
  feedback: string;
  summary: string;
  nilai: number;
  predikat: string;
  source: GradeSource;
};

export type GradeFailure = {
  ok: false;
  message: string;
  raw?: string;
};

export type GradeOutcome = ({ ok: true } & GradeData) | GradeFailure;

export type ModelPayload = {
  criteria: {
    id: string;
    score: number;
    quote: string;
    comment: string;
  }[];
  feedback: string;
  summary: string;
};
