import { requireLecturerCourse } from "@/lib/lecturer";
import { getCourseFrame, getUpcoming } from "@/lib/course-view";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { CourseFrame } from "@/components/course/course-frame";
import { courseTabs } from "@/components/course/tabs";
import { UpcomingList } from "@/components/course/right-blocks";
import { TopicsClient } from "./topics-client";

export const dynamic = "force-dynamic";

export default async function LecturerCoursePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { course } = await requireLecturerCourse(id);

  const [frame, upcoming] = await Promise.all([
    getCourseFrame(course.id, "lecturer"),
    getUpcoming(course.id, "lecturer"),
  ]);

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        rootHref="/lecturer/home"
        items={[
          { label: "Kursus", href: "/lecturer/courses" },
          { label: course.code },
        ]}
      />
      <CourseFrame
        courseLabel={`${course.code} — ${course.name}`}
        courseHref={`/lecturer/courses/${course.id}`}
        index={frame.topics}
        title={
          <>
            <h1 className="course-title">{course.name}</h1>
            <p className="mt-1 text-[14px] text-muted">
              {course.code} · Semester {course.semester} · {course.sks} SKS
            </p>
          </>
        }
        tabs={courseTabs(course.id, "lecturer")}
        blocks={<UpcomingList items={upcoming} />}
      >
        <TopicsClient
          courseId={course.id}
          topics={frame.topics}
          enrolled={frame.enrolled}
        />
      </CourseFrame>
    </div>
  );
}
