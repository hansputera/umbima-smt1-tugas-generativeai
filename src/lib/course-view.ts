import { q } from "@/db/pool";

export type FrameItem = {
  kind: "materi" | "assignment";
  id: string;
  topicId: string;
  title: string;
  type: string;
  href: string;
  due_at?: string | null;
  release_mode?: string | null;
  status?: string | null;
  grade_state?: string | null;
  nilai?: number | string | null;
  submitted_count?: number | null;
};

export type FrameTopic = {
  id: string;
  week: number;
  title: string;
  href: string;
  items: FrameItem[];
};

export type CourseFrameData = {
  topics: FrameTopic[];
  enrolled: number;
};

function materiTitle(b: {
  type: string;
  body: string | null;
  url: string | null;
  file_name: string | null;
}): string {
  if (b.type === "file") return b.file_name?.trim() || "Berkas";
  if (b.type === "link") return b.body?.trim() || b.url?.trim() || "Tautan";
  const first = (b.body ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)[0];
  if (!first) return "Materi";
  return first.length > 60 ? `${first.slice(0, 60)}…` : first;
}

export async function getCourseFrame(
  courseId: string,
  role: "student" | "lecturer",
  studentId?: string,
): Promise<CourseFrameData> {
  const topics = await q<{
    id: string;
    week: number;
    title: string;
  }>("SELECT id, week, title FROM topics WHERE course_id = $1 ORDER BY week", [
    courseId,
  ]);

  const materi = await q<{
    id: string;
    topic_id: string;
    type: string;
    body: string | null;
    url: string | null;
    file_name: string | null;
    position: number;
  }>(
    `SELECT m.id, m.topic_id, m.type, m.body, m.url, m.file_name, m.position
     FROM materi_blocks m
     JOIN topics t ON t.id = m.topic_id
     WHERE t.course_id = $1
     ORDER BY t.week, m.position`,
    [courseId],
  );

  const assignments =
    role === "student"
      ? await q<{
          id: string;
          topic_id: string;
          title: string;
          type: string;
          release_mode: string;
          due_at: string | null;
          status: string | null;
          grade_state: string | null;
          nilai: number | string | null;
        }>(
          `SELECT a.id, a.topic_id, a.title, a.type, a.release_mode, a.due_at,
                  s.status, g.state AS grade_state, g.nilai
           FROM assignments a
           JOIN topics t ON t.id = a.topic_id
           LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = $2
           LEFT JOIN grades g ON g.submission_id = s.id
           WHERE t.course_id = $1
           ORDER BY t.week, a.created_at`,
          [courseId, studentId ?? ""],
        )
      : await q<{
          id: string;
          topic_id: string;
          title: string;
          type: string;
          release_mode: string;
          due_at: string | null;
          submitted_count: number;
        }>(
          `SELECT a.id, a.topic_id, a.title, a.type, a.release_mode, a.due_at,
                  (SELECT count(*)::int FROM submissions s
                   WHERE s.assignment_id = a.id AND s.status <> 'draft') AS submitted_count
           FROM assignments a
           JOIN topics t ON t.id = a.topic_id
           WHERE t.course_id = $1
           ORDER BY t.week, a.created_at`,
          [courseId],
        );

  const enrolledRow = await q1Enrolled(courseId);

  const topicHref = (topicId: string) =>
    `/${role}/courses/${courseId}/topics/${topicId}`;

  const frameTopics: FrameTopic[] = topics.map((t) => {
    const items: FrameItem[] = [
      ...materi
        .filter((m) => m.topic_id === t.id)
        .map((m) => ({
          kind: "materi" as const,
          id: m.id,
          topicId: t.id,
          title: materiTitle(m),
          type: "materi",
          href: topicHref(t.id),
        })),
      ...assignments
        .filter((a) => a.topic_id === t.id)
        .map((a) => ({
          kind: "assignment" as const,
          id: a.id,
          topicId: t.id,
          title: a.title,
          type: a.type,
          href:
            role === "student"
              ? `/student/assignments/${a.id}`
              : `/lecturer/assignments/${a.id}`,
          due_at: a.due_at,
          release_mode: a.release_mode,
          status: "status" in a ? (a.status as string | null) : undefined,
          grade_state: "grade_state" in a ? (a.grade_state as string | null) : undefined,
          nilai: "nilai" in a ? (a.nilai as number | string | null) : undefined,
          submitted_count:
            "submitted_count" in a ? (a.submitted_count as number) : undefined,
        })),
    ];
    return { id: t.id, week: t.week, title: t.title, href: topicHref(t.id), items };
  });

  return { topics: frameTopics, enrolled: enrolledRow };
}

async function q1Enrolled(courseId: string): Promise<number> {
  const rows = await q<{ count: number }>(
    "SELECT count(*)::int AS count FROM enrollments WHERE course_id = $1",
    [courseId],
  );
  return rows[0]?.count ?? 0;
}

export type UpcomingItem = {
  id: string;
  title: string;
  type: string;
  due_at: string;
  status: string | null;
  href: string;
};

export async function getUpcoming(
  courseId: string,
  role: "student" | "lecturer",
  studentId?: string,
): Promise<UpcomingItem[]> {
  const params: (string | null)[] = [
    courseId,
    role === "student" ? (studentId ?? null) : null,
  ];
  let studentFilter = "";
  if (role === "student") {
    studentFilter = "AND (s.id IS NULL OR s.status = 'draft')";
  }
  const rows = await q<{
    id: string;
    title: string;
    type: string;
    due_at: string;
    status: string | null;
  }>(
    `SELECT a.id, a.title, a.type, a.due_at, s.status
     FROM assignments a
     JOIN topics t ON t.id = a.topic_id
     LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = $2
     WHERE t.course_id = $1 AND a.due_at > now() ${studentFilter}
     ORDER BY a.due_at ASC
     LIMIT 5`,
    params,
  );
  return rows.map((r) => ({
    ...r,
    href:
      role === "student"
        ? `/student/assignments/${r.id}`
        : `/lecturer/assignments/${r.id}`,
  }));
}

export type RecentGradeItem = {
  title: string;
  nilai: number | string;
  predikat: string;
  published_at: string | null;
  href: string;
};

export async function getRecentGrades(
  courseId: string,
  role: "student" | "lecturer",
  studentId?: string,
): Promise<RecentGradeItem[]> {
  const params: (string | null)[] = [courseId];
  let studentFilter = "";
  if (role === "student") {
    params.push(studentId ?? "");
    studentFilter = "AND s.student_id = $2";
  }
  const rows = await q<{
    assignment_id: string;
    title: string;
    nilai: number | string;
    predikat: string;
    published_at: string | null;
  }>(
    `SELECT a.id AS assignment_id, a.title, g.nilai, g.predikat, g.published_at
     FROM grades g
     JOIN submissions s ON s.id = g.submission_id
     JOIN assignments a ON a.id = s.assignment_id
     JOIN topics t ON t.id = a.topic_id
     WHERE t.course_id = $1 AND g.state = 'published' ${studentFilter}
     ORDER BY g.published_at DESC NULLS LAST, g.updated_at DESC
     LIMIT 5`,
    params,
  );
  return rows.map((r) => ({
    ...r,
    href:
      role === "student"
        ? `/student/assignments/${r.assignment_id}`
        : `/lecturer/assignments/${r.assignment_id}`,
  }));
}
