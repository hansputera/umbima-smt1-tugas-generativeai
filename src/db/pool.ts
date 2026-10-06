import { Pool, type PoolClient } from "pg";

const globalForDb = globalThis as unknown as { dbPool?: Pool };

export const pool =
  globalForDb.dbPool ??
  new Pool({
    connectionString:
      process.env.DATABASE_URL ??
      "postgresql://nilai:nilai@localhost:5432/nilai",
    max: 10,
  });

if (process.env.NODE_ENV !== "production") globalForDb.dbPool = pool;

export async function q<T = Record<string, unknown>>(
  text: string,
  params: unknown[] = [],
): Promise<T[]> {
  const res = await pool.query(text, params);
  return res.rows as T[];
}

export async function q1<T = Record<string, unknown>>(
  text: string,
  params: unknown[] = [],
): Promise<T | null> {
  const rows = await q<T>(text, params);
  return rows[0] ?? null;
}

export async function tx<T>(fn: (c: PoolClient) => Promise<T>): Promise<T> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

export function embeddingDim(): number {
  const raw = Number(process.env.EMBEDDING_DIM ?? 1536);
  return Number.isInteger(raw) && raw > 0 && raw <= 4096 ? raw : 1536;
}

export function embeddingTopK(): number {
  const raw = Number(process.env.EMBEDDING_TOP_K ?? 6);
  return Number.isInteger(raw) && raw > 0 && raw <= 50 ? raw : 6;
}
