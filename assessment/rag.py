"""Port of src/lib/grading/rag.ts (chunking + pgvector retrieval)."""

import re

from django.conf import settings as dj_settings
from django.db import transaction

from .ai import embed_call
from .models import DocumentChunk


def chunk_text(text):
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]

    units = []
    for paragraph in paragraphs:
        if len(paragraph) <= 1200:
            units.append(paragraph)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        buffer = ""
        for sentence in sentences:
            if buffer and len(buffer) + len(sentence) + 1 > 1200:
                units.append(buffer)
                buffer = sentence
            else:
                buffer = f"{buffer} {sentence}" if buffer else sentence
        if buffer:
            units.append(buffer)

    chunks = []
    current = ""
    for unit in units:
        if current and len(current) + len(unit) + 1 > 1400:
            chunks.append(current)
            current = current[-200:] + " " + unit
        else:
            current = f"{current}\n{unit}" if current else unit
    if current:
        chunks.append(current)
    return chunks if chunks else [text[:1400]]


def ensure_chunks(submission_id, text, settings):
    if DocumentChunk.objects.filter(submission_id=submission_id).count() > 0:
        return

    chunks = chunk_text(text)
    vectors = embed_call(settings, chunks)

    with transaction.atomic():
        for i, chunk in enumerate(chunks):
            DocumentChunk.objects.create(
                submission_id=submission_id,
                position=i,
                content=chunk,
                embedding=vectors[i],
            )


def retrieve_excerpts(submission_id, query, settings):
    from django.db import connection

    query_vector = embed_call(settings, [query])[0]
    vector_literal = "[" + ",".join(str(float(v)) for v in query_vector) + "]"
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT content FROM document_chunks "
            "WHERE submission_id = %s "
            "ORDER BY embedding <=> %s::vector "
            "LIMIT %s",
            [str(submission_id), vector_literal, dj_settings.EMBEDDING_TOP_K],
        )
        return [row[0] for row in cursor.fetchall()]
