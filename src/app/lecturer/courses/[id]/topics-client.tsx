"use client";

import { useActionState, useState } from "react";
import Link from "next/link";
import { Circle, CircleCheck, Pencil, Plus } from "lucide-react";
import { createTopic, type TopicFormState } from "./actions";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { Card, EmptyState } from "@/components/ui/misc";
import { TYPE_LABEL } from "@/lib/status";
import { fmtDate } from "@/lib/format";
import { ActivityIcon } from "@/components/course/activity-icon";
import type { FrameTopic } from "@/lib/course-view";

export function TopicsClient({
  courseId,
  topics,
  enrolled,
}: {
  courseId: string;
  topics: FrameTopic[];
  enrolled: number;
}) {
  const [creating, setCreating] = useState(false);
  const [state, formAction, pending] = useActionState<TopicFormState, FormData>(
    createTopic,
    undefined,
  );

  const [seenState, setSeenState] = useState(state);
  if (state !== seenState) {
    setSeenState(state);
    if (state && !state.errors) setCreating(false);
  }

  const errors = state?.errors ?? {};

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button variant="primary" onClick={() => setCreating((v) => !v)}>
          <Plus size={16} strokeWidth={1.5} aria-hidden />
          Tambah pertemuan
        </Button>
      </div>

      {creating ? (
        <Card className="p-6">
          <h2>Pertemuan baru</h2>
          <form action={formAction} className="mt-4 flex flex-col gap-4">
            <input type="hidden" name="course_id" value={courseId} />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Judul" htmlFor="t-title" error={errors.title}>
                <Input
                  id="t-title"
                  name="title"
                  placeholder="Normalisasi"
                />
              </Field>
              <Field label="Minggu" htmlFor="t-week" error={errors.week}>
                <Input
                  id="t-week"
                  name="week"
                  type="number"
                  min="1"
                  max="30"
                  placeholder="4"
                />
              </Field>
            </div>
            <div className="flex gap-3">
              <Button type="submit" variant="primary" disabled={pending}>
                {pending ? "Menyimpan..." : "Simpan"}
              </Button>
              <Button type="button" onClick={() => setCreating(false)}>
                Batal
              </Button>
            </div>
          </form>
        </Card>
      ) : null}

      {topics.length === 0 ? (
        <EmptyState message="Belum ada pertemuan. Tambahkan yang pertama, yuk!" />
      ) : (
        topics.map((t) => {
          return (
            <section
              key={t.id}
              className="overflow-hidden rounded-lg border border-border bg-white"
            >
              <div className="flex items-center justify-between gap-4 border-b border-border px-4 py-3">
                <Link
                  href={t.href}
                  className="truncate text-[15px] font-semibold text-ink hover:text-link"
                >
                  Pertemuan {t.week}: {t.title}
                </Link>
                <Link
                  href={t.href}
                  aria-label={`Edit Pertemuan ${t.week}`}
                  title="Edit pertemuan"
                  className="rounded-md p-1.5 text-muted transition-colors hover:bg-canvas hover:text-ink"
                >
                  <Pencil size={15} strokeWidth={1.75} aria-hidden />
                </Link>
              </div>

              {t.items.length === 0 ? (
                <p className="px-4 py-4 text-[14px] text-muted">
                  Belum ada aktivitas. Buka pertemuan untuk menambahkan materi
                  atau tugas.
                </p>
              ) : (
                t.items.map((item) => {
                  const count = item.submitted_count ?? 0;
                  const allIn = enrolled > 0 && count >= enrolled;
                  return (
                    <Link
                      key={item.id}
                      href={item.href}
                      className="flex items-center gap-3 border-b border-border px-4 py-3.5 transition-colors last:border-b-0 hover:bg-row-hover"
                    >
                      <ActivityIcon type={item.type} size={40} />
                      <span className="flex min-w-0 flex-col">
                        <span className="truncate text-[15px] font-medium text-ink">
                          {item.title}
                        </span>
                        <span className="text-[13px] text-muted">
                          {TYPE_LABEL[item.type] ?? item.type}
                          {item.due_at
                            ? ` · Tenggat ${fmtDate(item.due_at)}`
                            : ""}
                        </span>
                      </span>
                      {item.kind === "assignment" ? (
                        <span className="ml-auto flex shrink-0 items-center gap-3">
                          <span className="text-[13px] text-muted">
                            {count}/{enrolled} terkumpul
                          </span>
                          {allIn ? (
                            <CircleCheck
                              size={16}
                              strokeWidth={2}
                              className="text-ok"
                              aria-hidden
                            />
                          ) : (
                            <Circle
                              size={16}
                              strokeWidth={2}
                              className="text-faint"
                              aria-hidden
                            />
                          )}
                        </span>
                      ) : null}
                    </Link>
                  );
                })
              )}

              <div className="border-t border-border px-4 py-2.5">
                <Link
                  href={t.href}
                  className="inline-flex items-center gap-1.5 text-[13px] text-muted transition-colors hover:text-link"
                >
                  <Plus size={14} strokeWidth={2} aria-hidden />
                  Tambah aktivitas
                </Link>
              </div>
            </section>
          );
        })
      )}
    </div>
  );
}
