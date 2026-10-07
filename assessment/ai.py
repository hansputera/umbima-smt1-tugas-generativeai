"""Port of src/lib/grading/call.ts (chat completions + connection test)."""

import json
import socket
import urllib.error
import urllib.request

TIMEOUT = 60


def join_url(base, path):
    return base.rstrip("/") + path


def short_error(err):
    if isinstance(err, (socket.timeout, TimeoutError)):
        return "Waktu tunggu habis."
    if isinstance(err, urllib.error.URLError):
        reason = getattr(err, "reason", None)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return "Waktu tunggu habis."
        # Node fetch wraps network failures in TypeError "fetch failed".
        return "fetch failed"
    if isinstance(err, ConnectionError):
        return "fetch failed"
    return str(err)[:240] or "Gagal terhubung."


def call_chat(settings, messages, temperature, max_tokens):
    url = join_url(settings.base_url, "/chat/completions")
    payload = json.dumps(
        {
            "model": settings.model_name.strip(),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.api_key.strip()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            body = res.read()
            status = res.status
    except urllib.error.HTTPError as err:
        body = err.read() if hasattr(err, "read") else b""
        text = body.decode("utf-8", "replace")
        return {
            "ok": False,
            "message": f"HTTP {err.code}" + (f" — {text[:240]}" if text else ""),
        }
    except Exception as err:  # noqa: BLE001 - mirrors Node shortError mapping
        return {"ok": False, "message": short_error(err)}

    if status != 200:
        text = body.decode("utf-8", "replace")
        return {
            "ok": False,
            "message": f"HTTP {status}" + (f" — {text[:240]}" if text else ""),
        }

    try:
        data = json.loads(body)
    except ValueError:
        return {"ok": False, "message": "Respons server bukan JSON."}

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = None

    if not isinstance(content, str) or not content.strip():
        return {"ok": False, "message": "Respons tidak berisi teks."}

    return {"ok": True, "content": content}


def embed_call(settings, inputs):
    """Port of embedCall (src/lib/grading/call.ts). Raises on failure."""
    url = join_url(settings.emb_base_url, "/embeddings")
    payload = json.dumps(
        {"model": settings.emb_model_name.strip(), "input": inputs}
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.emb_api_key.strip()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            body = res.read()
            status = res.status
    except urllib.error.HTTPError as err:
        body = err.read() if hasattr(err, "read") else b""
        text = body.decode("utf-8", "replace")
        raise RuntimeError(
            f"HTTP {err.code}" + (f" — {text[:240]}" if text else "")
        )
    except Exception as err:  # noqa: BLE001 - mirrors Node shortError mapping
        raise RuntimeError(short_error(err))

    if status != 200:
        text = body.decode("utf-8", "replace")
        raise RuntimeError(
            f"HTTP {status}" + (f" — {text[:240]}" if text else "")
        )

    data = json.loads(body)  # ValueError propagates like Node res.json() throw
    raw_list = data.get("data") if isinstance(data, dict) else None
    items = sorted(
        raw_list or [],
        key=lambda d: (d.get("index") or 0) if isinstance(d, dict) else 0,
    )
    vectors = [d.get("embedding") if isinstance(d, dict) else None for d in items]

    if len(vectors) != len(inputs):
        raise RuntimeError("Jumlah embedding tidak sesuai.")
    for vec in vectors:
        if not isinstance(vec, list) or len(vec) == 0:
            raise RuntimeError("Respons embedding tidak valid.")
    return vectors


def test_connection(settings):
    result = call_chat(
        settings,
        [{"role": "user", "content": "Balas satu kata: siap"}],
        temperature=0,
        max_tokens=8,
    )
    if result["ok"]:
        return {"ok": True, "message": "Koneksi berhasil."}
    return {
        "ok": False,
        "message": f"Koneksi gagal. {result['message']}"[:400],
    }
