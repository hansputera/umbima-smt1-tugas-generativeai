import type { ReactNode } from "react";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { CourseFrame } from "./course-frame";
import { courseTabs } from "./tabs";
import type { CourseFrameData } from "@/lib/course-view";

export function CourseTabShell({
  role,
  course,
  frame,
  tab,
  blocks,
  children,
}: {
  role: "student" | "lecturer";
  course: {
    id: string;
    code: string;
    name: string;
    semester: number;
    sks: number;
  };
  frame: CourseFrameData;
  tab: string;
  blocks?: ReactNode;
  children: ReactNode;
}) {
  const base = `/${role}/courses/${course.id}`;
  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        rootHref={`/${role}/home`}
        items={[
          { label: "Kursus", href: `/${role}/courses` },
          { label: course.code, href: base },
          { label: tab },
        ]}
      />
      <CourseFrame
        courseLabel={`${course.code} — ${course.name}`}
        courseHref={base}
        index={frame.topics}
        title={
          <>
            <h1 className="course-title">{course.name}</h1>
            <p className="mt-1 text-[14px] text-muted">
              {course.code} · Semester {course.semester} · {course.sks} SKS
            </p>
          </>
        }
        tabs={courseTabs(course.id, role)}
        blocks={blocks}
      >
        {children}
      </CourseFrame>
    </div>
  );
}
