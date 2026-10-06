import { embeddingDim } from "./pool";

export function schemaSql(): string {
  const dim = embeddingDim();
  return `
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  email text NOT NULL UNIQUE,
  password_hash text,
  role text NOT NULL CHECK (role IN ('admin','lecturer','student')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS periods (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  is_active boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS courses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL,
  name text NOT NULL,
  semester int NOT NULL,
  sks int NOT NULL,
  period_id uuid NOT NULL REFERENCES periods(id),
  section text NOT NULL DEFAULT 'A',
  archived_at timestamptz,
  CONSTRAINT courses_code_period_section_key UNIQUE (code, period_id, section)
);

CREATE TABLE IF NOT EXISTS course_lecturers (
  course_id uuid NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  PRIMARY KEY (course_id, user_id)
);

CREATE TABLE IF NOT EXISTS enrollments (
  course_id uuid NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (course_id, student_id)
);

CREATE TABLE IF NOT EXISTS topics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id uuid NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  week int NOT NULL,
  title text NOT NULL,
  UNIQUE (course_id, week)
);

CREATE TABLE IF NOT EXISTS materi_blocks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id uuid NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  type text NOT NULL CHECK (type IN ('richtext','link','file')),
  body text,
  url text,
  file_name text,
  position int NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS assignments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id uuid NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  title text NOT NULL,
  type text NOT NULL CHECK (type IN ('essay','pg','pdf','docx')),
  release_mode text NOT NULL DEFAULT 'review' CHECK (release_mode IN ('review','langsung')),
  due_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assignment_questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id uuid NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
  position int NOT NULL DEFAULT 0,
  question text NOT NULL,
  options jsonb,
  answer_key text,
  UNIQUE (assignment_id, position)
);

CREATE TABLE IF NOT EXISTS rubric_criteria (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id uuid NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
  position int NOT NULL DEFAULT 0,
  name text NOT NULL,
  weight int NOT NULL,
  level_1 text NOT NULL DEFAULT '',
  level_2 text NOT NULL DEFAULT '',
  level_3 text NOT NULL DEFAULT '',
  level_4 text NOT NULL DEFAULT '',
  prompt_notes text NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS submissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id uuid NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
  student_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  answer_text text,
  answers jsonb NOT NULL DEFAULT '[]'::jsonb,
  file_name text,
  extracted_text text,
  extraction_ok boolean,
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','submitted','needs_review')),
  submitted_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (assignment_id, student_id)
);

CREATE TABLE IF NOT EXISTS document_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id uuid NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
  position int NOT NULL,
  content text NOT NULL,
  embedding vector(${dim})
);

CREATE INDEX IF NOT EXISTS document_chunks_submission_idx
  ON document_chunks (submission_id);

CREATE TABLE IF NOT EXISTS grades (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id uuid NOT NULL UNIQUE REFERENCES submissions(id) ON DELETE CASCADE,
  state text NOT NULL DEFAULT 'draft' CHECK (state IN ('draft','published')),
  criteria jsonb NOT NULL DEFAULT '[]'::jsonb,
  feedback text NOT NULL DEFAULT '',
  summary text NOT NULL DEFAULT '',
  nilai numeric(5,2) NOT NULL DEFAULT 0,
  predikat text NOT NULL DEFAULT 'D',
  source text NOT NULL CHECK (source IN ('model','manual','empty','code')),
  created_by uuid REFERENCES users(id),
  updated_by uuid REFERENCES users(id),
  published_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS grade_revisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  grade_id uuid NOT NULL REFERENCES grades(id) ON DELETE CASCADE,
  snapshot jsonb NOT NULL,
  nilai numeric(5,2) NOT NULL,
  predikat text NOT NULL,
  state text NOT NULL,
  changed_by uuid REFERENCES users(id),
  changed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS model_settings (
  id int PRIMARY KEY CHECK (id = 1),
  provider_label text NOT NULL DEFAULT '',
  base_url text NOT NULL DEFAULT '',
  api_key text NOT NULL DEFAULT '',
  model_name text NOT NULL DEFAULT '',
  temperature numeric(3,2) NOT NULL DEFAULT 0.20,
  max_tokens int NOT NULL DEFAULT 1200,
  system_preamble text NOT NULL DEFAULT '',
  emb_base_url text NOT NULL DEFAULT '',
  emb_api_key text NOT NULL DEFAULT '',
  emb_model_name text NOT NULL DEFAULT '',
  updated_at timestamptz,
  updated_by uuid REFERENCES users(id)
);
`;
}
