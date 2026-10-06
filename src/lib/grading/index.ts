import { q, q1 } from "@/db/pool";
import {
  getSettings,
  isEmbeddingConfigured,
  isModelConfigured,
} from "@/lib/settings";
import { buildMessages, type AnswerContext } from "./prompt";
import { callChat } from "./call";
import { parseModelResponse } from "./validate";
import { computeNilai, predikatOf } from "./score";
import { ensureChunks, retrieveExcerpts } from "./rag";
import type {
  AssignmentType,
  GradeCriterion,
  GradeData,
  GradeOutcome,
  GradeSource,
  ReleaseMode,
  RubricCriterion,
} from "./types";

export type SubmissionQuestion = {
  position: number;
  question: string;
  options: { key: string; text: string }[] | null;
  answer_key: string | null;
};

export type SubmissionContext = {
  id: string;
  assignment_id: string;
  student_id: string;
  answer_text: string | null;
  answers: string[];
  file_name: string | null;
  extracted_text: string | null;
  extraction_ok: boolean | null;
  status: string;
  submitted_at: string | null;
  updated_at: string;
  assignment_title: string;
  type: AssignmentType;
  questions: SubmissionQuestion[];
  release_mode: ReleaseMode;
  topic_id: string;
  topic_title: string;
  week: number;
  course_id: string;
  course_code: string;
  course_name: string;
  student_name: string;
  student_email: string;
};

export type GradeRow = {
  id: string;
  submission_id: string;
  state: "draft" | "published";
  criteria: GradeCriterion[];
  feedback: string;
  summary: string;
  nilai: number | string;
  predikat: string;
  source: GradeSource;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
};

const SUBMISSION_SQL = `
  SELECT
    s.id, s.assignment_id, s.student_id, s.answer_text, s.answers,
    s.file_name, s.extracted_text, s.extraction_ok, s.status, s.submitted_at, s.updated_at,
    a.title AS assignment_title, a.type,
    COALESCE((
      SELECT jsonb_agg(
               jsonb_build_object(
                 'position', q.position,
                 'question', q.question,
                 'options', q.options,
                 'answer_key', q.answer_key
               ) ORDER BY q.position
             )
      FROM assignment_questions q
      WHERE q.assignment_id = a.id
    ), '[]'::jsonb) AS questions,
    a.release_mode, a.topic_id,
    t.title AS topic_title, t.week,
    c.id AS course_id, c.code AS course_code, c.name AS course_name,
    u.name AS student_name, u.email AS student_email
  FROM submissions s
  JOIN assignments a ON a.id = s.assignment_id
  JOIN topics t ON t.id = a.topic_id
  JOIN courses c ON c.id = t.course_id
  JOIN users u ON u.id = s.student_id
  WHERE s.id = $1
`;

export async function getSubmissionContext(
  submissionId: string,
): Promise<SubmissionContext | null> {
  return q1<SubmissionContext>(SUBMISSION_SQL, [submissionId]);
}

export async function getRubric(
  assignmentId: string,
): Promise<RubricCriterion[]> {
  return q<RubricCriterion>(
    "SELECT * FROM rubric_criteria WHERE assignment_id = $1 ORDER BY position, name",
    [assignmentId],
  );
}

export async function getAssignmentQuestions(
  assignmentId: string,
): Promise<SubmissionQuestion[]> {
  return q<SubmissionQuestion>(
    `SELECT position, question, options, answer_key
     FROM assignment_questions
     WHERE assignment_id = $1
     ORDER BY position`,
    [assignmentId],
  );
}

export async function getGrade(
  submissionId: string,
): Promise<GradeRow | null> {
  return q1<GradeRow>("SELECT * FROM grades WHERE submission_id = $1", [
    submissionId,
  ]);
}

export async function isLecturerAssigned(
  courseId: string,
  lecturerId: string,
): Promise<boolean> {
  const row = await q1(
    "SELECT 1 AS ok FROM course_lecturers WHERE course_id = $1 AND user_id = $2",
    [courseId, lecturerId],
  );
  return Boolean(row);
}

export async function isStudentEnrolled(
  courseId: string,
  studentId: string,
): Promise<boolean> {
  const row = await q1(
    "SELECT 1 AS ok FROM enrollments WHERE course_id = $1 AND student_id = $2",
    [courseId, studentId],
  );
  return Boolean(row);
}

export async function getLecturerSubmission(
  submissionId: string,
  lecturerId: string,
): Promise<SubmissionContext | null> {
  const ctx = await getSubmissionContext(submissionId);
  if (!ctx) return null;
  const allowed = await isLecturerAssigned(ctx.course_id, lecturerId);
  return allowed ? ctx : null;
}

export async function getStudentSubmission(
  submissionId: string,
  studentId: string,
): Promise<SubmissionContext | null> {
  const ctx = await getSubmissionContext(submissionId);
  if (!ctx) return null;
  return ctx.student_id === studentId ? ctx : null;
}

// ---------------------------------------------------------------------------
// Grading
// ---------------------------------------------------------------------------

export async function computeGrade(
  submissionId: string,
): Promise<GradeOutcome> {
  const sub = await getSubmissionContext(submissionId);
  if (!sub) return { ok: false, message: "Pengumpulan tidak ditemukan." };
  const rubric = await getRubric(sub.assignment_id);

  if (sub.type === "pg") {
    const questions = sub.questions ?? [];
    const answers = sub.answers ?? [];
    const total = questions.length;
    const correct = questions.filter(
      (q, i) => q.answer_key && answers[i] === q.answer_key,
    ).length;
    const nilai = total === 0 ? 0 : Math.round((correct / total) * 10000) / 100;
    return {
      ok: true,
      criteria: [],
      feedback: `${correct} dari ${total} jawaban benar.`,
      summary: "Dinilai otomatis dari kunci jawaban, tanpa model.",
      nilai,
      predikat: predikatOf(nilai),
      source: "code",
    };
  }

  const isFile = sub.type === "pdf" || sub.type === "docx";
  const text = isFile ? (sub.extracted_text ?? "") : (sub.answer_text ?? "");
  const promptText = (sub.questions ?? [])
    .map((item) => item.question)
    .join("\n");

  if (isFile && sub.extraction_ok === false) {
    return { ok: false, message: "Teks tidak terbaca." };
  }

  if (!text.trim()) {
    if (rubric.length === 0) {
      return { ok: false, message: "Rubrik belum disetel." };
    }
    const criteria: GradeCriterion[] = rubric.map((c) => ({
      criterion_id: c.id,
      name: c.name,
      weight: c.weight,
      score: 1,
      quote: "",
      comment: "Jawaban kosong.",
    }));
    const nilai = computeNilai(criteria);
    return {
      ok: true,
      criteria,
      feedback: "Jawaban kosong.",
      summary: "Jawaban kosong, model tidak dipanggil.",
      nilai,
      predikat: predikatOf(nilai),
      source: "empty",
    };
  }

  const settings = await getSettings();
  if (!isModelConfigured(settings)) {
    return { ok: false, message: "Model belum disetel." };
  }
  if (rubric.length === 0) {
    return { ok: false, message: "Rubrik belum disetel." };
  }

  let answer: AnswerContext;
  const needRag = isFile || text.length > 6000;
  if (needRag) {
    if (!isEmbeddingConfigured(settings)) {
      return { ok: false, message: "Embedding belum disetel." };
    }
    try {
      await ensureChunks(sub.id, text, settings);
      const query = `${promptText}\n${rubric.map((r) => r.name).join("\n")}`;
      const excerpts = await retrieveExcerpts(sub.id, query, settings);
      if (excerpts.length === 0) {
        return { ok: false, message: "Teks tidak terbaca." };
      }
      answer = { kind: "doc", excerpts };
    } catch (err) {
      const detail = err instanceof Error ? err.message : "tidak diketahui";
      return {
        ok: false,
        message: `Embedding gagal. ${detail}`.slice(0, 300),
      };
    }
  } else {
    answer = { kind: "text", text };
  }

  const messages = buildMessages({
    preamble: settings.system_preamble,
    question: promptText,
    answer,
    rubric,
  });

  const result = await callChat(settings, messages, {
    temperature: Number(settings.temperature),
    maxTokens: Number(settings.max_tokens),
  });
  if (!result.ok) {
    return { ok: false, message: `Gagal memanggil model. ${result.message}` };
  }

  const parsed = parseModelResponse(result.content, rubric);
  if (!parsed.ok) {
    return {
      ok: false,
      message: `Respons model tidak valid. ${parsed.errors.join(" ")}`,
      raw: result.content,
    };
  }

  const criteria: GradeCriterion[] = [];
  for (const entry of parsed.data.criteria) {
    const c = rubric.find((r) => r.id === entry.id);
    if (!c) continue;
    criteria.push({
      criterion_id: c.id,
      name: c.name,
      weight: c.weight,
      score: entry.score,
      quote: entry.quote,
      comment: entry.comment,
    });
  }

  const nilai = computeNilai(criteria);
  return {
    ok: true,
    criteria,
    feedback: parsed.data.feedback,
    summary: parsed.data.summary,
    nilai,
    predikat: predikatOf(nilai),
    source: "model",
  };
}

export async function persistGrade(args: {
  submissionId: string;
  data: GradeData;
  actorId: string | null;
  publish: boolean;
}): Promise<{ id: string; state: "draft" | "published" }> {
  const existing = await q1<{ id: string; state: "draft" | "published" }>(
    "SELECT id, state FROM grades WHERE submission_id = $1",
    [args.submissionId],
  );
  const state: "draft" | "published" = args.publish
    ? "published"
    : (existing?.state ?? "draft");
  const justPublished = state === "published" && existing?.state !== "published";
  const d = args.data;
  const snapshot = JSON.stringify({
    criteria: d.criteria,
    feedback: d.feedback,
    summary: d.summary,
  });

  const row = existing
    ? await q1<{ id: string }>(
        `UPDATE grades
         SET state = $2, criteria = $3::jsonb, feedback = $4, summary = $5,
             nilai = $6, predikat = $7, source = $8, updated_by = $9, updated_at = now(),
             published_at = CASE WHEN $10 THEN now() ELSE published_at END
         WHERE id = $1
         RETURNING id`,
        [
          existing.id,
          state,
          JSON.stringify(d.criteria),
          d.feedback,
          d.summary,
          d.nilai,
          d.predikat,
          d.source,
          args.actorId,
          justPublished,
        ],
      )
    : await q1<{ id: string }>(
        `INSERT INTO grades
           (submission_id, state, criteria, feedback, summary, nilai, predikat, source, created_by, updated_by, published_at)
         VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8, $9, $9, CASE WHEN $2 = 'published' THEN now() ELSE null END)
         RETURNING id`,
        [
          args.submissionId,
          state,
          JSON.stringify(d.criteria),
          d.feedback,
          d.summary,
          d.nilai,
          d.predikat,
          d.source,
          args.actorId,
        ],
      );

  if (!row) throw new Error("Gagal menyimpan nilai.");

  await q(
    `INSERT INTO grade_revisions (grade_id, snapshot, nilai, predikat, state, changed_by)
     VALUES ($1, $2::jsonb, $3, $4, $5, $6)`,
    [row.id, snapshot, d.nilai, d.predikat, state, args.actorId],
  );

  return { id: row.id, state };
}

export type GradeEditInput = {
  scores?: Record<string, number>;
  quotes?: Record<string, string>;
  comments?: Record<string, string>;
  feedback: string;
  summary: string;
  publish: boolean;
  actorId: string;
};

export async function applyGradeEdits(
  submissionId: string,
  input: GradeEditInput,
): Promise<
  | { ok: true; nilai: number; predikat: string; state: "draft" | "published" }
  | { ok: false; error: string }
> {
  const grade = await getGrade(submissionId);

  const ctx = await getSubmissionContext(submissionId);
  if (!ctx) return { ok: false, error: "Pengumpulan tidak ditemukan." };

  if (!input.feedback.trim()) {
    return { ok: false, error: "Umpan balik wajib diisi." };
  }

  const rubric =
    ctx.type === "pg" ? [] : await getRubric(ctx.assignment_id);

  if (!grade && rubric.length === 0) {
    return {
      ok: false,
      error: "Belum ada nilai. Jalankan penilaian otomatis terlebih dahulu.",
    };
  }

  let criteria: GradeCriterion[];
  if (rubric.length > 0) {
    criteria = [];
    for (const c of rubric) {
      const prev = grade?.criteria.find((x) => x.criterion_id === c.id);
      const raw = input.scores?.[c.id] ?? prev?.score ?? 1;
      const score = Number(raw);
      if (!Number.isInteger(score) || score < 1 || score > 4) {
        return { ok: false, error: `Skor tidak valid pada "${c.name}".` };
      }
      criteria.push({
        criterion_id: c.id,
        name: c.name,
        weight: c.weight,
        score,
        quote: input.quotes?.[c.id] ?? prev?.quote ?? "",
        comment: input.comments?.[c.id] ?? prev?.comment ?? "",
      });
    }
  } else {
    criteria = grade!.criteria;
  }

  const nilai =
    criteria.length > 0 ? computeNilai(criteria) : Number(grade!.nilai);
  const predikat = predikatOf(nilai);

  const saved = await persistGrade({
    submissionId,
    data: {
      criteria,
      feedback: input.feedback.trim(),
      summary: input.summary.trim(),
      nilai,
      predikat,
      source: grade?.source ?? "manual",
    },
    actorId: input.actorId,
    publish: input.publish,
  });

  return { ok: true, nilai, predikat, state: saved.state };
}
