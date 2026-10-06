export type ExtractResult =
  | { ok: true; text: string }
  | { ok: false; message: string };

export async function extractFileText(file: File): Promise<ExtractResult> {
  const name = file.name.toLowerCase();
  const bytes = new Uint8Array(await file.arrayBuffer());

  try {
    if (name.endsWith(".pdf")) {
      const { extractText, getDocumentProxy } = await import("unpdf");
      const pdf = await getDocumentProxy(bytes);
      const { text } = await extractText(pdf, { mergePages: true });
      const clean = (text ?? "").trim();
      if (!clean) return { ok: false, message: "Teks tidak terbaca." };
      return { ok: true, text: clean };
    }

    if (name.endsWith(".docx")) {
      const mammoth = await import("mammoth");
      const buffer = Buffer.from(bytes);
      const result = await mammoth.extractRawText({ buffer });
      const clean = (result.value ?? "").trim();
      if (!clean) return { ok: false, message: "Teks tidak terbaca." };
      return { ok: true, text: clean };
    }

    return { ok: false, message: "Teks tidak terbaca." };
  } catch {
    return { ok: false, message: "Teks tidak terbaca." };
  }
}
