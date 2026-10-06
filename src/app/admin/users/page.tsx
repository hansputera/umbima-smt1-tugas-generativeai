import { q } from "@/db/pool";
import { UsersClient, type UserRow } from "./users-client";

export const dynamic = "force-dynamic";

export default async function UsersPage() {
  const users = await q<UserRow>(
    `SELECT id, name, email, role, status FROM users
     ORDER BY CASE role WHEN 'admin' THEN 0 WHEN 'lecturer' THEN 1 ELSE 2 END, name`,
  );

  return <UsersClient users={users} />;
}
