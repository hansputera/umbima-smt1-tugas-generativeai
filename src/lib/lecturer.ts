import { redirect } from "next/navigation";
import { q1 } from "@/db/pool";
import { requireRole, type SessionUser } from "@/lib/session";
import type { AssignmentType, ReleaseMode } from "@/lib/grading/types";

export type LecturerCourse = {
  id: string;
  code: string;
  name: string;
  semester: number;
  sks: number;
  archived_at: string | null;
  period_name: string;
  section: string;
};

export type LecturerTopic = {
  id: string;
  course_id: string;
  week: number;
  title: string;
};

export type LecturerAssignment = {
  id: string;
  topic_id: string;
  title: string;
  type: AssignmentType;
  release_mode: ReleaseMode;
  created_at: string;
};

export async function requireLecturer(): Promise<SessionUser> {
  return requireRole("lecturer");
}

export async function requireLecturerCourse(
  courseId: string,
): Promise<{ course: LecturerCourse; lecturer: SessionUser }> {
  const lecturer = await requireLecturer();
  const course = await q1<LecturerCourse>(
    `SELECT c.id, c.code, c.name, c.semester, c.sks, c.archived_at,
            p.name AS period_name, c.section
     FROM courses c
     JOIN periods p ON p.id = c.period_id
     JOIN course_lecturers cl ON cl.course_id = c.id AND cl.user_id = $2
     WHERE c.id = $1`,
    [courseId, lecturer.id],
  );
  if (!course) redirect("/lecturer/courses");
  return { course, lecturer };
}

export async function requireLecturerTopic(
  topicId: string,
): Promise<{
  topic: LecturerTopic;
  course: LecturerCourse;
  lecturer: SessionUser;
}> {
  const lecturer = await requireLecturer();
  const row = await q1<
    LecturerTopic & {
      code: string;
      name: string;
      semester: number;
      sks: number;
      archived_at: string | null;
      period_name: string;
      section: string;
    }
  >(
    `SELECT t.id, t.course_id, t.week, t.title,
            c.code, c.name, c.semester, c.sks, c.archived_at,
            p.name AS period_name, c.section
     FROM topics t
     JOIN courses c ON c.id = t.course_id
     JOIN periods p ON p.id = c.period_id
     JOIN course_lecturers cl ON cl.course_id = c.id AND cl.user_id = $2
     WHERE t.id = $1`,
    [topicId, lecturer.id],
  );
  if (!row) redirect("/lecturer/courses");
  return {
    topic: {
      id: row.id,
      course_id: row.course_id,
      week: row.week,
      title: row.title,
    },
    course: {
      id: row.course_id,
      code: row.code,
      name: row.name,
      semester: row.semester,
      sks: row.sks,
      archived_at: row.archived_at,
      period_name: row.period_name,
      section: row.section,
    },
    lecturer,
  };
}

export async function requireLecturerAssignment(
  assignmentId: string,
): Promise<{
  assignment: LecturerAssignment;
  topic: LecturerTopic;
  course: LecturerCourse;
  lecturer: SessionUser;
}> {
  const lecturer = await requireLecturer();
  const row = await q1<
    LecturerAssignment & {
      week: number;
      topic_title: string;
      c_id: string;
      c_code: string;
      c_name: string;
      c_semester: number;
      c_sks: number;
      c_archived: string | null;
      c_period: string;
      c_section: string;
    }
  >(
    `SELECT a.id, a.topic_id, a.title, a.type, a.release_mode, a.created_at,
            t.week, t.title AS topic_title,
            c.id AS c_id, c.code AS c_code, c.name AS c_name,
            c.semester AS c_semester, c.sks AS c_sks, c.archived_at AS c_archived,
            p.name AS c_period, c.section AS c_section
     FROM assignments a
     JOIN topics t ON t.id = a.topic_id
     JOIN courses c ON c.id = t.course_id
     JOIN periods p ON p.id = c.period_id
     JOIN course_lecturers cl ON cl.course_id = c.id AND cl.user_id = $2
     WHERE a.id = $1`,
    [assignmentId, lecturer.id],
  );
  if (!row) redirect("/lecturer/courses");

  return {
    assignment: {
      id: row.id,
      topic_id: row.topic_id,
      title: row.title,
      type: row.type,
      release_mode: row.release_mode,
      created_at: row.created_at,
    },
    topic: {
      id: row.topic_id,
      course_id: row.c_id,
      week: row.week,
      title: row.topic_title,
    },
    course: {
      id: row.c_id,
      code: row.c_code,
      name: row.c_name,
      semester: row.c_semester,
      sks: row.c_sks,
      archived_at: row.c_archived,
      period_name: row.c_period,
      section: row.c_section,
    },
    lecturer,
  };
}
