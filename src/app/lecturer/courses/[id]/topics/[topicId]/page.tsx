import { q } from "@/db/pool";
import { requireLecturerTopic } from "@/lib/lecturer";
import { getCourseFrame } from "@/lib/course-view";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { TopicDetailClient } from "./topic-detail-client";

export const dynamic = "force-dynamic";

export default async function TopicPage({
  params,
}: {
  params: Promise<{ id: string; topicId: string }>;
}) {
  const { topicId } = await params;
  const { topic, course } = await requireLecturerTopic(topicId);

  const frame = await getCourseFrame(course.id, "lecturer");

  const blocks = await q<{
    id: string;
    type: string;
    body: string | null;
    url: string | null;
    file_name: string | null;
  }>(
    `SELECT id, type, body, url, file_name FROM materi_blocks
     WHERE topic_id = $1 ORDER BY position`,
    [topic.id],
  );

  const assignments = await q<{
    id: string;
    title: string;
    type: string;
    release_mode: string;
    submission_count: number;
  }>(
    `SELECT a.id, a.title, a.type, a.release_mode,
            (SELECT count(*)::int FROM submissions s WHERE s.assignment_id = a.id) AS submission_count
     FROM assignments a
     WHERE a.topic_id = $1
     ORDER BY a.created_at`,
    [topic.id],
  );

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        rootHref="/lecturer/home"
        items={[
          { label: "Kursus", href: "/lecturer/courses" },
          { label: course.code, href: `/lecturer/courses/${course.id}` },
          { label: `Pertemuan ${topic.week}` },
        ]}
      />
      <TopicDetailClient
        topic={topic}
        course={{ id: course.id, code: course.code, name: course.name }}
        frame={frame}
        blocks={blocks}
        assignments={assignments}
      />
    </div>
  );
}
