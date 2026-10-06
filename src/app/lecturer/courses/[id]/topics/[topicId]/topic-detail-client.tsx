"use client";

import { useActionState, useState } from "react";
import Link from "next/link";
import { Plus, X } from "lucide-react";
import {
  createAssignment,
  saveTopic,
  type AssignmentFormState,
  type TopicSaveState,
} from "./actions";
import { Button, buttonClass } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { Card, ErrorLine, Notice, Section } from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { MODE_LABEL, TYPE_LABEL } from "@/lib/status";
import { CourseFrame } from "@/components/course/course-frame";
import { courseTabs } from "@/components/course/tabs";
import type { CourseFrameData } from "@/lib/course-view";

type Block = {
  key: string;
  type: "richtext" | "link" | "file";
  body: string;
  url: string;
  file_name: string;
};

type AssignmentRow = {
  id: string;
  title: string;
  type: string;
  release_mode: string;
  submission_count: number;
};

type PgQuestion = {
  key: string;
  text: string;
  options: { key: string; text: string }[];
  answerKey: string;
};

function newBlock(type: Block["type"]): Block {
  return {
    key:
      typeof crypto !== "undefined" ? crypto.randomUUID() : String(Math.random()),
    type,
    body: "",
    url: "",
    file_name: "",
  };
}

function newPgQuestion(): PgQuestion {
  return {
    key:
      typeof crypto !== "undefined" ? crypto.randomUUID() : String(Math.random()),
    text: "",
    options: [
      { key: "A", text: "" },
      { key: "B", text: "" },
      { key: "C", text: "" },
      { key: "D", text: "" },
    ],
    answerKey: "A",
  };
}

export function TopicDetailClient(props: {
  topic: { id: string; week: number; title: string };
  course: { id: string; code: string; name: string };
  frame: CourseFrameData;
  blocks: {
    id?: string;
    type: string;
    body: string | null;
    url: string | null;
    file_name: string | null;
  }[];
  assignments: AssignmentRow[];
}) {
  const [title, setTitle] = useState(props.topic.title);
  const [week, setWeek] = useState(String(props.topic.week));
  const [blocks, setBlocks] = useState<Block[]>(
    props.blocks.map((b) => ({
      key: b.id ?? newBlock("richtext").key,
      type: (b.type as Block["type"]) ?? "richtext",
      body: b.body ?? "",
      url: b.url ?? "",
      file_name: b.file_name ?? "",
    })),
  );

  const [saveState, saveAction, savePending] = useActionState<TopicSaveState,
    FormData
  >(saveTopic, undefined);

  const [creating, setCreating] = useState(false);
  const [aState, aAction, aPending] = useActionState<AssignmentFormState,
    FormData
  >(createAssignment, undefined);

  const [aTitle, setATitle] = useState("");
  const [aType, setAType] = useState("essay");
  const [aQuestion, setAQuestion] = useState("");
  const [pgQuestions, setPgQuestions] = useState<PgQuestion[]>([
    newPgQuestion(),
  ]);

  const [seenAState, setSeenAState] = useState(aState);
  if (aState !== seenAState) {
    setSeenAState(aState);
    if (aState && !aState.errors && !aState.error) {
      setCreating(false);
      setATitle("");
      setAQuestion("");
      setPgQuestions([newPgQuestion()]);
    }
  }

  function updateBlock(index: number, patch: Partial<Block>) {
    setBlocks((prev) =>
      prev.map((b, i) => (i === index ? { ...b, ...patch } : b)),
    );
  }

  const errors = saveState?.errors ?? {};
  const aErrors = aState?.errors ?? {};
  const serializedBlocks = JSON.stringify(
    blocks.map(({ type, body, url, file_name }) => ({
      type,
      body,
      url,
      file_name,
    })),
  );
  const serializedPgQuestions = JSON.stringify(
    pgQuestions.map((q) => ({
      question: q.text,
      options: q.options.filter((o) => o.text.trim()),
      answer_key: q.answerKey,
    })),
  );

  function updatePgQuestion(index: number, patch: Partial<PgQuestion>) {
    setPgQuestions((prev) =>
      prev.map((q, i) => (i === index ? { ...q, ...patch } : q)),
    );
  }

  return (
    <CourseFrame
      courseLabel={`${props.course.code} — ${props.course.name}`}
      courseHref={`/lecturer/courses/${props.course.id}`}
      index={props.frame.topics}
      activeTopicId={props.topic.id}
      title={
        <>
          <h1 className="course-title">
            Pertemuan {props.topic.week}: {props.topic.title}
          </h1>
          <p className="mt-1 text-[14px] text-muted">
            {props.course.code} — {props.course.name}
          </p>
        </>
      }
      action={
        <div className="flex items-center gap-3">
          <Link
            href={`/lecturer/courses/${props.course.id}`}
            className={buttonClass()}
          >
            Ke mata kuliah
          </Link>
          {creating ? (
            <Button onClick={() => setCreating(false)}>Batal</Button>
          ) : (
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus size={16} strokeWidth={1.5} aria-hidden />
              Tambah tugas
            </Button>
          )}
        </div>
      }
      tabs={courseTabs(props.course.id, "lecturer")}
    >
      <form
        id="topic-form"
        action={saveAction}
        className="flex flex-col gap-4"
      >
        <input type="hidden" name="topic_id" value={props.topic.id} />
        <input type="hidden" name="blocks" value={serializedBlocks} />

        <Card className="flex flex-col gap-4 p-6">
          <h2>Detail pertemuan</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Judul" htmlFor="td-title" error={errors.title}>
              <Input
                id="td-title"
                name="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </Field>
            <Field label="Minggu" htmlFor="td-week" error={errors.week}>
              <Input
                id="td-week"
                name="week"
                type="number"
                min="1"
                max="30"
                value={week}
                onChange={(e) => setWeek(e.target.value)}
              />
            </Field>
          </div>
        </Card>

        <Card className="flex flex-col gap-4 p-6">
          <div className="flex items-center justify-between gap-4">
            <h2>Materi</h2>
            <Button
              type="button"
              onClick={() => setBlocks((prev) => [...prev, newBlock("richtext")])}
            >
              <Plus size={16} strokeWidth={1.5} aria-hidden />
              Tambah materi
            </Button>
          </div>

          {blocks.length === 0 ? (
            <p className="text-[14px] text-muted">
              Belum ada materi. Tambahkan materi pertama.
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {blocks.map((b, i) => (
                <div
                  key={b.key}
                  className="flex flex-col gap-3 rounded-md border border-border p-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="label">Materi {i + 1}</span>
                      <Select
                        aria-label={`Tipe materi ${i + 1}`}
                        className="w-40"
                        value={b.type}
                        onChange={(e) =>
                          updateBlock(i, {
                            type: e.target.value as Block["type"],
                          })
                        }
                      >
                        <option value="richtext">Teks</option>
                        <option value="link">Tautan</option>
                        <option value="file">Berkas</option>
                      </Select>
                    </div>
                    <button
                      type="button"
                      className="cursor-pointer text-muted hover:text-ink"
                      aria-label={`Hapus materi ${i + 1}`}
                      onClick={() =>
                        setBlocks((prev) => prev.filter((_, j) => j !== i))
                      }
                    >
                      <X size={16} strokeWidth={1.5} aria-hidden />
                    </button>
                  </div>

                  {b.type === "richtext" ? (
                    <Textarea
                      rows={3}
                      placeholder="Tulis isi materi..."
                      value={b.body}
                      onChange={(e) => updateBlock(i, { body: e.target.value })}
                    />
                  ) : null}

                  {b.type === "link" ? (
                    <div className="grid grid-cols-2 gap-3">
                      <Input
                        placeholder="Judul tautan"
                        value={b.body}
                        onChange={(e) => updateBlock(i, { body: e.target.value })}
                      />
                      <Input
                        placeholder="https://..."
                        value={b.url}
                        onChange={(e) => updateBlock(i, { url: e.target.value })}
                      />
                    </div>
                  ) : null}

                  {b.type === "file" ? (
                    <div className="flex items-center gap-3">
                      <input
                        type="file"
                        accept=".pdf,.docx"
                        className="text-[14px] text-muted file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-border file:bg-white file:px-3 file:py-1.5 file:text-[14px]"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) updateBlock(i, { file_name: f.name });
                        }}
                      />
                      {b.file_name ? (
                        <span className="text-[13px] text-muted">
                          {b.file_name}
                        </span>
                      ) : (
                        <span className="text-[13px] text-muted">
                          Pilih PDF atau DOCX.
                        </span>
                      )}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}

          {saveState?.error ? <ErrorLine>{saveState.error}</ErrorLine> : null}
          {saveState?.info ? <Notice dot="#1d7a3e">{saveState.info}</Notice> : null}

          <div className="flex items-center gap-3 border-t border-border pt-4">
            <Button type="submit" disabled={savePending}>
              {savePending ? "Menyimpan..." : "Simpan pertemuan"}
            </Button>
            <p className="text-[13px] text-muted">
              Tautan materi tersimpan, berkas hanya namanya.
            </p>
          </div>
        </Card>
      </form>

      <Section title="Tugas">
        {creating ? (
          <Card className="p-6">
            <h3>Tugas baru</h3>
            <form action={aAction} className="mt-4 flex flex-col gap-4">
              <input type="hidden" name="topic_id" value={props.topic.id} />
              {aType === "pg" ? (
                <input type="hidden" name="questions" value={serializedPgQuestions} />
              ) : null}
              <div className="grid grid-cols-2 gap-4">
                <Field label="Judul" htmlFor="a-title" error={aErrors.title}>
                  <Input
                    id="a-title"
                    name="title"
                    value={aTitle}
                    onChange={(e) => setATitle(e.target.value)}
                    placeholder="Esai: bentuk normalisasi"
                  />
                </Field>
                <Field label="Tipe" htmlFor="a-type" error={aErrors.type}>
                  <Select
                    id="a-type"
                    name="type"
                    value={aType}
                    onChange={(e) => setAType(e.target.value)}
                  >
                    <option value="essay">Esai</option>
                    <option value="pg">Pilihan ganda</option>
                    <option value="pdf">Unggah PDF</option>
                    <option value="docx">Unggah DOCX</option>
                  </Select>
                </Field>
              </div>

              {aType !== "pg" ? (
                <Field
                  label="Pertanyaan"
                  htmlFor="a-question"
                  error={aErrors.question}
                >
                  <Textarea
                    id="a-question"
                    name="question"
                    rows={3}
                    value={aQuestion}
                    onChange={(e) => setAQuestion(e.target.value)}
                  />
                </Field>
              ) : (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="label">Daftar soal</span>
                    <button
                      type="button"
                      className="cursor-pointer text-[13px] text-muted hover:text-ink"
                      onClick={() =>
                        setPgQuestions((prev) => [...prev, newPgQuestion()])
                      }
                    >
                      + Tambah soal
                    </button>
                  </div>
                  {aErrors.question ? (
                    <ErrorLine>{aErrors.question}</ErrorLine>
                  ) : null}
                  {aErrors.options ? (
                    <ErrorLine>{aErrors.options}</ErrorLine>
                  ) : null}
                  {pgQuestions.map((q, qi) => (
                    <div
                      key={q.key}
                      className="flex flex-col gap-3 rounded-md border border-border p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="label">Soal {qi + 1}</span>
                        {pgQuestions.length > 1 ? (
                          <button
                            type="button"
                            className="cursor-pointer text-muted hover:text-ink"
                            aria-label={`Hapus soal ${qi + 1}`}
                            onClick={() =>
                              setPgQuestions((prev) =>
                                prev.filter((_, j) => j !== qi),
                              )
                            }
                          >
                            <X size={16} strokeWidth={1.5} aria-hidden />
                          </button>
                        ) : null}
                      </div>

                      <Textarea
                        rows={2}
                        placeholder="Tulis soal..."
                        value={q.text}
                        onChange={(e) =>
                          updatePgQuestion(qi, { text: e.target.value })
                        }
                      />

                      <div className="flex flex-col gap-2">
                        {q.options.map((o) => (
                          <div key={o.key} className="flex items-center gap-3">
                            <input
                              type="radio"
                              name={`answer_key_${q.key}`}
                              value={o.key}
                              className="size-4 accent-accent"
                              aria-label={`Kunci soal ${qi + 1}: ${o.key}`}
                              checked={q.answerKey === o.key}
                              onChange={() =>
                                updatePgQuestion(qi, { answerKey: o.key })
                              }
                            />
                            <span className="w-4 text-[14px] font-medium">
                              {o.key}
                            </span>
                            <Input
                              placeholder={`Opsi ${o.key}`}
                              value={o.text}
                              onChange={(e) =>
                                updatePgQuestion(qi, {
                                  options: q.options.map((p) =>
                                    p.key === o.key
                                      ? { ...p, text: e.target.value }
                                      : p,
                                  ),
                                })
                              }
                            />
                          </div>
                        ))}
                        {q.options.length < 6 ? (
                          <div>
                            <button
                              type="button"
                              className="cursor-pointer text-[13px] text-muted hover:text-ink"
                              onClick={() =>
                                updatePgQuestion(qi, {
                                  options: [
                                    ...q.options,
                                    {
                                      key: String.fromCharCode(65 + q.options.length),
                                      text: "",
                                    },
                                  ],
                                })
                              }
                            >
                              + Tambah opsi
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ))}

                  <p className="text-[13px] text-muted">
                    Kunci hanya terlihat dosen.
                  </p>
                </div>
              )}

              {aState?.error ? <ErrorLine>{aState.error}</ErrorLine> : null}

              <div className="flex gap-3">
                <Button type="submit" variant="primary" disabled={aPending}>
                  {aPending ? "Membuat..." : "Buat tugas"}
                </Button>
                <Button type="button" onClick={() => setCreating(false)}>
                  Batal
                </Button>
              </div>
            </form>
          </Card>
        ) : null}

        <Table>
          <thead>
            <tr>
              <Th>Judul</Th>
              <Th>Tipe</Th>
              <Th>Mode rilis</Th>
              <Th>Pengumpulan</Th>
              <Th className="text-right">Aksi</Th>
            </tr>
          </thead>
          <tbody>
            {props.assignments.map((a) => (
              <Tr key={a.id}>
                <Td className="font-medium">{a.title}</Td>
                <Td>{TYPE_LABEL[a.type] ?? a.type}</Td>
                <Td>{MODE_LABEL[a.release_mode] ?? a.release_mode}</Td>
                <Td>{a.submission_count}</Td>
                <Td>
                  <div className="flex justify-end">
                    <Link
                      href={`/lecturer/assignments/${a.id}`}
                      className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                    >
                      Buka
                    </Link>
                  </div>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      </Section>
    </CourseFrame>
  );
}
