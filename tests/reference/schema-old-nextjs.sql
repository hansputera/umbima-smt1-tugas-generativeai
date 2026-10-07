--
-- PostgreSQL database dump
--

\restrict xJrn3WhsPS0GyK5F5P5cQsxqgxa0CnfhJg2vtHOKmO6wwocA38T0A3evEtrtR6V

-- Dumped from database version 17.11 (Debian 17.11-1.pgdg12+2)
-- Dumped by pg_dump version 17.11 (Debian 17.11-1.pgdg12+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: app_settings; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.app_settings (
    id integer NOT NULL,
    app_name text DEFAULT 'MiniCourse'::text NOT NULL,
    footer_text text DEFAULT ''::text NOT NULL,
    logo bytea,
    logo_type text,
    logo_version integer DEFAULT 0 NOT NULL,
    updated_at timestamp with time zone,
    updated_by uuid,
    CONSTRAINT app_settings_id_check CHECK ((id = 1))
);


ALTER TABLE public.app_settings OWNER TO nilai;

--
-- Name: assignment_questions; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.assignment_questions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    assignment_id uuid NOT NULL,
    "position" integer DEFAULT 0 NOT NULL,
    question text NOT NULL,
    options jsonb,
    answer_key text
);


ALTER TABLE public.assignment_questions OWNER TO nilai;

--
-- Name: assignments; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.assignments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    topic_id uuid NOT NULL,
    title text NOT NULL,
    type text NOT NULL,
    release_mode text DEFAULT 'review'::text NOT NULL,
    due_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT assignments_release_mode_check CHECK ((release_mode = ANY (ARRAY['review'::text, 'langsung'::text]))),
    CONSTRAINT assignments_type_check CHECK ((type = ANY (ARRAY['essay'::text, 'pg'::text, 'pdf'::text, 'docx'::text])))
);


ALTER TABLE public.assignments OWNER TO nilai;

--
-- Name: course_lecturers; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.course_lecturers (
    course_id uuid NOT NULL,
    user_id uuid NOT NULL
);


ALTER TABLE public.course_lecturers OWNER TO nilai;

--
-- Name: courses; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.courses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    semester integer NOT NULL,
    sks integer NOT NULL,
    period_id uuid NOT NULL,
    section text DEFAULT 'A'::text NOT NULL,
    archived_at timestamp with time zone
);


ALTER TABLE public.courses OWNER TO nilai;

--
-- Name: document_chunks; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.document_chunks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    submission_id uuid NOT NULL,
    "position" integer NOT NULL,
    content text NOT NULL,
    embedding public.vector(3072)
);


ALTER TABLE public.document_chunks OWNER TO nilai;

--
-- Name: enrollments; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.enrollments (
    course_id uuid NOT NULL,
    student_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.enrollments OWNER TO nilai;

--
-- Name: grade_revisions; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.grade_revisions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    grade_id uuid NOT NULL,
    snapshot jsonb NOT NULL,
    nilai numeric(5,2) NOT NULL,
    predikat text NOT NULL,
    state text NOT NULL,
    changed_by uuid,
    changed_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.grade_revisions OWNER TO nilai;

--
-- Name: grades; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.grades (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    submission_id uuid NOT NULL,
    state text DEFAULT 'draft'::text NOT NULL,
    criteria jsonb DEFAULT '[]'::jsonb NOT NULL,
    feedback text DEFAULT ''::text NOT NULL,
    summary text DEFAULT ''::text NOT NULL,
    nilai numeric(5,2) DEFAULT 0 NOT NULL,
    predikat text DEFAULT 'D'::text NOT NULL,
    source text NOT NULL,
    created_by uuid,
    updated_by uuid,
    published_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT grades_source_check CHECK ((source = ANY (ARRAY['model'::text, 'manual'::text, 'empty'::text, 'code'::text]))),
    CONSTRAINT grades_state_check CHECK ((state = ANY (ARRAY['draft'::text, 'published'::text])))
);


ALTER TABLE public.grades OWNER TO nilai;

--
-- Name: materi_blocks; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.materi_blocks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    topic_id uuid NOT NULL,
    type text NOT NULL,
    body text,
    url text,
    file_name text,
    "position" integer DEFAULT 0 NOT NULL,
    CONSTRAINT materi_blocks_type_check CHECK ((type = ANY (ARRAY['richtext'::text, 'link'::text, 'file'::text])))
);


ALTER TABLE public.materi_blocks OWNER TO nilai;

--
-- Name: model_settings; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.model_settings (
    id integer NOT NULL,
    provider_label text DEFAULT ''::text NOT NULL,
    base_url text DEFAULT ''::text NOT NULL,
    api_key text DEFAULT ''::text NOT NULL,
    model_name text DEFAULT ''::text NOT NULL,
    temperature numeric(3,2) DEFAULT 0.20 NOT NULL,
    max_tokens integer DEFAULT 1200 NOT NULL,
    system_preamble text DEFAULT ''::text NOT NULL,
    emb_base_url text DEFAULT ''::text NOT NULL,
    emb_api_key text DEFAULT ''::text NOT NULL,
    emb_model_name text DEFAULT ''::text NOT NULL,
    updated_at timestamp with time zone,
    updated_by uuid,
    CONSTRAINT model_settings_id_check CHECK ((id = 1))
);


ALTER TABLE public.model_settings OWNER TO nilai;

--
-- Name: periods; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.periods (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    is_active boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.periods OWNER TO nilai;

--
-- Name: rubric_criteria; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.rubric_criteria (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    assignment_id uuid NOT NULL,
    "position" integer DEFAULT 0 NOT NULL,
    name text NOT NULL,
    weight integer NOT NULL,
    level_1 text DEFAULT ''::text NOT NULL,
    level_2 text DEFAULT ''::text NOT NULL,
    level_3 text DEFAULT ''::text NOT NULL,
    level_4 text DEFAULT ''::text NOT NULL,
    prompt_notes text DEFAULT ''::text NOT NULL
);


ALTER TABLE public.rubric_criteria OWNER TO nilai;

--
-- Name: submissions; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.submissions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    assignment_id uuid NOT NULL,
    student_id uuid NOT NULL,
    answer_text text,
    answers jsonb DEFAULT '[]'::jsonb NOT NULL,
    file_name text,
    extracted_text text,
    extraction_ok boolean,
    status text DEFAULT 'draft'::text NOT NULL,
    submitted_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT submissions_status_check CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'needs_review'::text])))
);


ALTER TABLE public.submissions OWNER TO nilai;

--
-- Name: topics; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.topics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    course_id uuid NOT NULL,
    week integer NOT NULL,
    title text NOT NULL
);


ALTER TABLE public.topics OWNER TO nilai;

--
-- Name: users; Type: TABLE; Schema: public; Owner: nilai
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    email text NOT NULL,
    password_hash text,
    role text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT users_role_check CHECK ((role = ANY (ARRAY['admin'::text, 'lecturer'::text, 'student'::text]))),
    CONSTRAINT users_status_check CHECK ((status = ANY (ARRAY['active'::text, 'inactive'::text])))
);


ALTER TABLE public.users OWNER TO nilai;

--
-- Name: app_settings app_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.app_settings
    ADD CONSTRAINT app_settings_pkey PRIMARY KEY (id);


--
-- Name: assignment_questions assignment_questions_assignment_id_position_key; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.assignment_questions
    ADD CONSTRAINT assignment_questions_assignment_id_position_key UNIQUE (assignment_id, "position");


--
-- Name: assignment_questions assignment_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.assignment_questions
    ADD CONSTRAINT assignment_questions_pkey PRIMARY KEY (id);


--
-- Name: assignments assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_pkey PRIMARY KEY (id);


--
-- Name: course_lecturers course_lecturers_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.course_lecturers
    ADD CONSTRAINT course_lecturers_pkey PRIMARY KEY (course_id, user_id);


--
-- Name: courses courses_code_period_section_key; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_code_period_section_key UNIQUE (code, period_id, section);


--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (id);


--
-- Name: document_chunks document_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);


--
-- Name: enrollments enrollments_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_pkey PRIMARY KEY (course_id, student_id);


--
-- Name: grade_revisions grade_revisions_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.grade_revisions
    ADD CONSTRAINT grade_revisions_pkey PRIMARY KEY (id);


--
-- Name: grades grades_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_pkey PRIMARY KEY (id);


--
-- Name: grades grades_submission_id_key; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_submission_id_key UNIQUE (submission_id);


--
-- Name: materi_blocks materi_blocks_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.materi_blocks
    ADD CONSTRAINT materi_blocks_pkey PRIMARY KEY (id);


--
-- Name: model_settings model_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.model_settings
    ADD CONSTRAINT model_settings_pkey PRIMARY KEY (id);


--
-- Name: periods periods_name_key; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.periods
    ADD CONSTRAINT periods_name_key UNIQUE (name);


--
-- Name: periods periods_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.periods
    ADD CONSTRAINT periods_pkey PRIMARY KEY (id);


--
-- Name: rubric_criteria rubric_criteria_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.rubric_criteria
    ADD CONSTRAINT rubric_criteria_pkey PRIMARY KEY (id);


--
-- Name: submissions submissions_assignment_id_student_id_key; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_assignment_id_student_id_key UNIQUE (assignment_id, student_id);


--
-- Name: submissions submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_pkey PRIMARY KEY (id);


--
-- Name: topics topics_course_id_week_key; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_course_id_week_key UNIQUE (course_id, week);


--
-- Name: topics topics_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: document_chunks_submission_idx; Type: INDEX; Schema: public; Owner: nilai
--

CREATE INDEX document_chunks_submission_idx ON public.document_chunks USING btree (submission_id);


--
-- Name: app_settings app_settings_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.app_settings
    ADD CONSTRAINT app_settings_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id);


--
-- Name: assignment_questions assignment_questions_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.assignment_questions
    ADD CONSTRAINT assignment_questions_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: assignments assignments_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.topics(id) ON DELETE CASCADE;


--
-- Name: course_lecturers course_lecturers_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.course_lecturers
    ADD CONSTRAINT course_lecturers_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: course_lecturers course_lecturers_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.course_lecturers
    ADD CONSTRAINT course_lecturers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: courses courses_period_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_period_id_fkey FOREIGN KEY (period_id) REFERENCES public.periods(id);


--
-- Name: document_chunks document_chunks_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(id) ON DELETE CASCADE;


--
-- Name: enrollments enrollments_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: enrollments enrollments_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.enrollments
    ADD CONSTRAINT enrollments_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: grade_revisions grade_revisions_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.grade_revisions
    ADD CONSTRAINT grade_revisions_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id);


--
-- Name: grade_revisions grade_revisions_grade_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.grade_revisions
    ADD CONSTRAINT grade_revisions_grade_id_fkey FOREIGN KEY (grade_id) REFERENCES public.grades(id) ON DELETE CASCADE;


--
-- Name: grades grades_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: grades grades_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.submissions(id) ON DELETE CASCADE;


--
-- Name: grades grades_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.grades
    ADD CONSTRAINT grades_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id);


--
-- Name: materi_blocks materi_blocks_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.materi_blocks
    ADD CONSTRAINT materi_blocks_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.topics(id) ON DELETE CASCADE;


--
-- Name: model_settings model_settings_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.model_settings
    ADD CONSTRAINT model_settings_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id);


--
-- Name: rubric_criteria rubric_criteria_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.rubric_criteria
    ADD CONSTRAINT rubric_criteria_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: submissions submissions_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.assignments(id) ON DELETE CASCADE;


--
-- Name: submissions submissions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: topics topics_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: nilai
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict xJrn3WhsPS0GyK5F5P5cQsxqgxa0CnfhJg2vtHOKmO6wwocA38T0A3evEtrtR6V

