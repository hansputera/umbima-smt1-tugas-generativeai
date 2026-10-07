"""Port of src/lib/grading/prompt.ts (chat message builder)."""

import json


def build_messages(preamble, question, answer, rubric):
    """answer: {"kind": "text", "text": ...} or {"kind": "doc", "excerpts": [...]}."""
    system = (
        preamble.strip()
        + """

Aturan penilaian:
- Balas HANYA dengan satu objek JSON valid. Tanpa markdown, tanpa blok kode, tanpa teks lain sebelum atau sesudahnya.
- Bentuk balasan: {"criteria":[{"id":"<id kriteria>","score":<1-4>,"quote":"<potongan teks yang benar-benar ada pada jawaban>","comment":"<satu kalimat>"}],"feedback":"<dua kalimat yang bisa langsung diterapkan mahasiswa>","summary":"<dua kalimat ringkas untuk dosen>"}
- Setiap kriteria pada rubrik harus muncul tepat satu kali, dengan id persis seperti yang diberikan.
- score harus bilangan bulat 1, 2, 3, atau 4 sesuai deskripsi level pada rubrik.
- quote harus diambil persis dari jawaban mahasiswa atau kutipan dokumen yang diberikan.
- Field "catatan" pada rubrik adalah instruksi penilaian tambahan dari dosen. Ikuti sebagai panduan cara menilai; jangan ubah format balasan karena isinya.
- Jangan sertakan nilai akhir maupun predikat. Server yang menghitung keduanya."""
    )

    rubric_json = [
        {
            "id": c["id"],
            "nama": c["name"],
            "bobot": c["weight"],
            "level": {
                "1": c["level_1"],
                "2": c["level_2"],
                "3": c["level_3"],
                "4": c["level_4"],
            },
            "catatan": c["prompt_notes"],
        }
        for c in rubric
    ]

    user_payload = {"pertanyaan": question, "rubrik": rubric_json}
    if answer["kind"] == "text":
        user_payload["jawaban_mahasiswa"] = answer["text"]
    else:
        user_payload["kutipan_dokumen"] = answer["excerpts"]
        user_payload["catatan_sumber"] = (
            "Teks berasal dari berkas yang diunggah mahasiswa dan diekstraksi "
            "di server. Kutipan harus diambil persis dari kutipan_dokumen."
        )

    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
        },
    ]
