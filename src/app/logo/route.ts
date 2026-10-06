import { q1 } from "@/db/pool";

export async function GET(): Promise<Response> {
  const row = await q1<{ logo: Buffer | null; logo_type: string | null }>(
    "SELECT logo, logo_type FROM app_settings WHERE id = 1",
  );
  if (!row || !row.logo || !row.logo_type) {
    return new Response("Logo tidak tersedia", { status: 404 });
  }
  return new Response(new Uint8Array(row.logo), {
    headers: {
      "Content-Type": row.logo_type,
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  });
}
