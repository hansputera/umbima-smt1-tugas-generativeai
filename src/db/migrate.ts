import { pool } from "./pool";
import { schemaSql } from "./schema";
import { seedIfEmpty } from "./seed";

let ready = false;

async function hasColumn(
  client: { query: <T>(sql: string, params?: unknown[]) => Promise<{ rows: T[] }> },
  table: string,
  column: string,
): Promise<boolean> {
  const res = await client.query<{ exists: boolean }>(
    `SELECT EXISTS (
       SELECT 1 FROM information_schema.columns
       WHERE table_schema = 'public' AND table_name = $1 AND column_name = $2
     ) AS exists`,
    [table, column],
  );
  return Boolean(res.rows[0]?.exists);
}

async function migrateLegacy(
  client: { query: <T>(sql: string, params?: unknown[]) => Promise<{ rows: T[] }> },
): Promise<void> {
  await client.query(
    "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS answers jsonb NOT NULL DEFAULT '[]'::jsonb",
  );
  await client.query(
    "ALTER TABLE assignments ADD COLUMN IF NOT EXISTS due_at timestamptz",
  );
  await client.query(
    "ALTER TABLE grades ADD COLUMN IF NOT EXISTS published_at timestamptz",
  );
  await client.query(
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash text",
  );
  await client.query(
    "ALTER TABLE courses ADD COLUMN IF NOT EXISTS period_id uuid REFERENCES periods(id)",
  );
  await client.query(
    "ALTER TABLE courses ADD COLUMN IF NOT EXISTS section text NOT NULL DEFAULT 'A'",
  );
  await client.query(
    `INSERT INTO periods (name, is_active)
     SELECT '2025/2026 Ganjil', true
     WHERE NOT EXISTS (SELECT 1 FROM periods)
       AND EXISTS (SELECT 1 FROM courses)`,
  );
  await client.query(
    `UPDATE courses SET period_id = (
       SELECT id FROM periods ORDER BY is_active DESC, created_at ASC, id ASC LIMIT 1
     ) WHERE period_id IS NULL`,
  );
  await client.query(
    "ALTER TABLE courses ALTER COLUMN period_id SET NOT NULL",
  );
  await client.query("ALTER TABLE courses DROP CONSTRAINT IF EXISTS courses_code_key");
  await client.query(`
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'courses_code_period_section_key'
          AND conrelid = 'courses'::regclass
      ) THEN
        ALTER TABLE courses
          ADD CONSTRAINT courses_code_period_section_key UNIQUE (code, period_id, section);
      END IF;
    END $$;
  `);
  await client.query(
    `UPDATE grades SET published_at = created_at WHERE state = 'published' AND published_at IS NULL`,
  );
  if (await hasColumn(client, "assignments", "question")) {
    await client.query(
      `INSERT INTO assignment_questions (assignment_id, position, question, options, answer_key)
       SELECT a.id, 0, a.question, a.options, a.answer_key
       FROM assignments a
       WHERE NOT EXISTS (
         SELECT 1 FROM assignment_questions q WHERE q.assignment_id = a.id
       )`,
    );
    await client.query(
      "ALTER TABLE assignments DROP COLUMN IF EXISTS question, DROP COLUMN IF EXISTS options, DROP COLUMN IF EXISTS answer_key",
    );
    console.log("[db] migrated assignments.question -> assignment_questions");
  }
  if (await hasColumn(client, "submissions", "choice_key")) {
    await client.query(
      `UPDATE submissions s
       SET answers = jsonb_build_array(s.choice_key)
       FROM assignments a
       WHERE a.id = s.assignment_id AND a.type = 'pg'
         AND s.choice_key IS NOT NULL
         AND s.answers = '[]'::jsonb`,
    );
    await client.query("ALTER TABLE submissions DROP COLUMN IF EXISTS choice_key");
    console.log("[db] migrated submissions.choice_key -> answers");
  }
}

export async function migrateAndSeed(): Promise<void> {
  if (ready) return;
  const client = await pool.connect();
  try {
    await client.query("SELECT pg_advisory_lock(727272)");
    await client.query(schemaSql());
    await migrateLegacy(client);
    const seeded = await seedIfEmpty(client);
    if (seeded) console.log("[db] first boot: schema applied, seed inserted");
    ready = true;
  } finally {
    try {
      await client.query("SELECT pg_advisory_unlock(727272)");
    } catch {
      /* connection may be closed */
    }
    client.release();
  }
}
