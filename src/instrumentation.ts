export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { migrateAndSeed } = await import("./db/migrate");
    try {
      await migrateAndSeed();
    } catch (err) {
      console.error("[db] init failed:", err);
    }
  }
}
