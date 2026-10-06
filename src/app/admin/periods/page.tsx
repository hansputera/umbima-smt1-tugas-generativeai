import { q } from "@/db/pool";
import { PeriodsClient, type PeriodRow } from "./periods-client";

export const dynamic = "force-dynamic";

export default async function PeriodsPage() {
  const periods = await q<PeriodRow>(
    `SELECT p.id, p.name, p.is_active,
            (SELECT count(*) FROM courses c WHERE c.period_id = p.id)::int AS class_count
     FROM periods p
     ORDER BY p.is_active DESC, p.created_at DESC, p.name`,
  );

  return <PeriodsClient periods={periods} />;
}
