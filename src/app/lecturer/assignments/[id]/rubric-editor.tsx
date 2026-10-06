"use client";

import { useActionState, useState } from "react";
import {
  closestCenter,
  DndContext,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  sortableKeyboardCoordinates,
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Plus, X } from "lucide-react";
import { saveRubric, type RubricSaveState } from "./actions";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/field";
import { Card, EmptyState, ErrorLine, Notice } from "@/components/ui/misc";

type Row = {
  key: string;
  id: string | null;
  name: string;
  weight: string;
  level_1: string;
  level_2: string;
  level_3: string;
  level_4: string;
  prompt_notes: string;
};

function newRow(): Row {
  return {
    key:
      typeof crypto !== "undefined" ? crypto.randomUUID() : String(Math.random()),
    id: null,
    name: "",
    weight: "0",
    level_1: "",
    level_2: "",
    level_3: "",
    level_4: "",
    prompt_notes: "",
  };
}

function fromServer(c: {
  id: string;
  name: string;
  weight: number;
  level_1: string;
  level_2: string;
  level_3: string;
  level_4: string;
  prompt_notes: string;
}): Row {
  return {
    key: c.id,
    id: c.id,
    name: c.name,
    weight: String(c.weight),
    level_1: c.level_1 ?? "",
    level_2: c.level_2 ?? "",
    level_3: c.level_3 ?? "",
    level_4: c.level_4 ?? "",
    prompt_notes: c.prompt_notes ?? "",
  };
}

const LEVELS: { key: keyof Row; score: number }[] = [
  { key: "level_1", score: 1 },
  { key: "level_2", score: 2 },
  { key: "level_3", score: 3 },
  { key: "level_4", score: 4 },
];

function CriterionRow({
  row,
  index,
  onChange,
  onRemove,
}: {
  row: Row;
  index: number;
  onChange: (patch: Partial<Row>) => void;
  onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: row.key });

  return (
    <tr
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.6 : undefined,
      }}
      className="border-b border-border align-top hover:bg-row-hover"
    >
      <td className="w-9 px-2 py-2.5">
        <button
          type="button"
          className="cursor-grab touch-none text-faint hover:text-ink"
          aria-label={`Pindahkan kriteria ${index + 1}`}
          {...attributes}
          {...listeners}
        >
          <GripVertical size={16} strokeWidth={1.5} aria-hidden />
        </button>
      </td>
      <td className="min-w-[240px] px-2.5 py-2.5">
        <Input
          aria-label={`Nama kriteria ${index + 1}`}
          placeholder="Nama kriteria"
          value={row.name}
          onChange={(e) => onChange({ name: e.target.value })}
        />
      </td>
      <td className="w-[92px] px-2.5 py-2.5">
        <Input
          aria-label={`Bobot kriteria ${index + 1}`}
          type="number"
          min="0"
          max="100"
          value={row.weight}
          onChange={(e) => onChange({ weight: e.target.value })}
        />
      </td>
      {LEVELS.map((l) => (
        <td key={l.key} className="min-w-[210px] px-2.5 py-2.5">
          <Textarea
            rows={4}
            aria-label={`Kriteria ${index + 1} deskripsi skor ${l.score}`}
            placeholder={`Skor ${l.score}: ...`}
            value={String(row[l.key])}
            onChange={(e) => onChange({ [l.key]: e.target.value } as Partial<Row>)}
          />
        </td>
      ))}
      <td className="min-w-[210px] px-2.5 py-2.5">
        <Textarea
          rows={4}
          aria-label={`Catatan prompt kriteria ${index + 1}`}
          placeholder="Catatan prompt (opsional)"
          value={row.prompt_notes}
          onChange={(e) => onChange({ prompt_notes: e.target.value })}
        />
      </td>
      <td className="w-9 px-2 py-2.5 text-right">
        <button
          type="button"
          className="flex cursor-pointer items-center justify-center text-muted hover:text-danger"
          aria-label={`Hapus kriteria ${index + 1}`}
          onClick={onRemove}
        >
          <X size={16} strokeWidth={1.5} aria-hidden />
        </button>
      </td>
    </tr>
  );
}

export function RubricEditor({
  assignmentId,
  initialRows,
}: {
  assignmentId: string;
  initialRows: {
    id: string;
    name: string;
    weight: number;
    level_1: string;
    level_2: string;
    level_3: string;
    level_4: string;
    prompt_notes: string;
  }[];
}) {
  const [rows, setRows] = useState<Row[]>(() => initialRows.map(fromServer));
  const [state, action, pending] = useActionState<RubricSaveState, FormData>(
    saveRubric,
    undefined,
  );

  const [seenState, setSeenState] = useState(state);
  if (state !== seenState) {
    setSeenState(state);
    if (state?.criteria) setRows(state.criteria.map(fromServer));
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const total = rows.reduce((sum, r) => sum + (Number(r.weight) || 0), 0);
  const totalOk = total === 100;

  function update(key: string, patch: Partial<Row>) {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    setRows((prev) => {
      const oldIndex = prev.findIndex((r) => r.key === active.id);
      const newIndex = prev.findIndex((r) => r.key === over.id);
      if (oldIndex < 0 || newIndex < 0) return prev;
      return arrayMove(prev, oldIndex, newIndex);
    });
  }

  const payload = rows.map((r) => ({
    id: r.id,
    name: r.name,
    weight: Number(r.weight) || 0,
    level_1: r.level_1,
    level_2: r.level_2,
    level_3: r.level_3,
    level_4: r.level_4,
    prompt_notes: r.prompt_notes,
  }));

  return (
    <form
      id="rubrik"
      action={action}
      className="flex scroll-mt-20 flex-col gap-3"
    >
      <input type="hidden" name="assignment_id" value={assignmentId} />
      <input type="hidden" name="criteria" value={JSON.stringify(payload)} />

      <div className="flex items-center justify-between gap-4">
        <h2>Rubrik</h2>
        <Button
          type="button"
          onClick={() => setRows((prev) => [...prev, newRow()])}
        >
          <Plus size={16} strokeWidth={1.5} aria-hidden />
          Tambah kriteria
        </Button>
      </div>

      <Card className="overflow-hidden">
        {rows.length === 0 ? (
          <div className="p-4">
            <EmptyState message="Belum ada kriteria rubrik. Tambahkan kriteria pertama." />
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1440px] border-collapse text-[14px]">
                <thead>
                  <tr className="border-b border-border bg-white">
                    <th className="w-9 px-2 py-2.5" />
                    <th className="label px-2.5 py-2.5 text-left">Kriteria</th>
                    <th className="label w-[92px] px-2.5 py-2.5 text-left">Bobot %</th>
                    <th className="label min-w-[210px] px-2.5 py-2.5 text-left">Level 1</th>
                    <th className="label min-w-[210px] px-2.5 py-2.5 text-left">Level 2</th>
                    <th className="label min-w-[210px] px-2.5 py-2.5 text-left">Level 3</th>
                    <th className="label min-w-[210px] px-2.5 py-2.5 text-left">Level 4</th>
                    <th className="label min-w-[210px] px-2.5 py-2.5 text-left">Catatan</th>
                    <th className="w-9 px-2 py-2.5" />
                  </tr>
                </thead>
                <SortableContext
                  items={rows.map((r) => r.key)}
                  strategy={verticalListSortingStrategy}
                >
                  <tbody>
                    {rows.map((row, i) => (
                      <CriterionRow
                        key={row.key}
                        row={row}
                        index={i}
                        onChange={(patch) => update(row.key, patch)}
                        onRemove={() =>
                          setRows((prev) => prev.filter((r) => r.key !== row.key))
                        }
                      />
                    ))}
                  </tbody>
                </SortableContext>
                <tfoot>
                  <tr className="border-t border-border bg-white">
                    <td className="px-2 py-3" />
                    <td colSpan={2} className="px-2 py-3">
                      <span
                        className={`text-[14px] ${totalOk ? "text-muted" : "text-danger"}`}
                      >
                        Total bobot: {total}%
                      </span>
                    </td>
                    <td colSpan={6} className="px-3 py-3 text-right">
                      <Button
                        type="submit"
                        variant="primary"
                        disabled={pending || rows.length === 0 || !totalOk}
                      >
                        {pending ? "Menyimpan..." : "Simpan rubrik"}
                      </Button>
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </DndContext>
        )}
      </Card>

      {state?.error ? <ErrorLine>{state.error}</ErrorLine> : null}
      {state?.info ? <Notice dot="#1d7a3e">{state.info}</Notice> : null}
    </form>
  );
}
