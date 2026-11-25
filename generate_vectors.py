#!/usr/bin/env python3
"""Write vectors.json: signed webhook inputs that every SDK runner verifies.

Timestamps are relative to the moment this runs, because the SDKs read the clock themselves.
Run the runners within a few minutes of generating (run.sh does both in one go).
"""

import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

SECRET = "wsec_conformance_0123456789abcdef"
OTHER_SECRET = "wsec_someone_else_000000000000000"
BODY = json.dumps({"type": "post_call_transcription", "data": {"conversation_id": "conv_conformance"}},
                  separators=(",", ":"))


def digest(timestamp: str, body: str, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()


def header(timestamp: str, body: str = BODY, secret: str = SECRET) -> str:
    return f"t={timestamp},v0={digest(timestamp, body, secret)}"


def vectors(now: int):
    t = str(now)
    sig = digest(t, BODY)
    wrong = digest(t, BODY, OTHER_SECRET)
    unicode_body = json.dumps({"type": "post_call_transcription", "data": {"summary": "Één klant zei: “merci” 👍"}},
                              ensure_ascii=False, separators=(",", ":"))
    v = []

    def add(group, vid, description, hdr, body=BODY, secret=SECRET):
        v.append({"group": group, "id": vid, "description": description, "header": hdr, "body": body,
                  "secret": secret})

    add("baseline", "valid", "Correctly signed, current timestamp", header(t))
    add("baseline", "valid_parts_reversed", "v0 part before the t part", f"v0={sig},t={t}")
    add("baseline", "valid_unicode_body", "Body with multi-byte UTF-8 (accents, curly quotes, emoji)",
        header(t, unicode_body), body=unicode_body)
    add("baseline", "future_timestamp", "Timestamp one hour in the future", header(str(now + 3600)))
    add("baseline", "inside_window", "Timestamp 29 minutes old", header(str(now - 29 * 60)))

    add("missing", "missing_header", "Empty signature header", "")
    add("missing", "missing_secret", "Empty secret", header(t), secret="")
    add("missing", "no_timestamp", "Header without a t= part", f"v0={sig}")
    add("missing", "no_signature", "Header without a v0= part", f"t={t}")
    add("missing", "empty_timestamp", "t= with no value", f"t=,v0={sig}")
    add("missing", "only_v1_scheme", "Signature under an unknown v1 scheme", f"t={t},v1={sig}")

    add("replay", "stale_timestamp", "Timestamp 31 minutes old, correctly signed", header(str(now - 31 * 60)))
    for vid, ts, what in [
        ("ts_non_numeric", "abc", "Non-numeric timestamp"),
        ("ts_exponent", "1e12", "Exponent notation (1e12 seconds is far in the future)"),
        ("ts_fraction", f"{now}.5", "Fractional seconds"),
        ("ts_plus_sign", f"+{now}", "Leading plus sign"),
        ("ts_leading_space", f" {now}", "Leading space"),
        ("ts_trailing_garbage", f"{now}abc", "Digits followed by letters"),
    ]:
        add("replay", vid, f"{what}, correctly signed over that exact string", header(ts))

    add("signature", "wrong_secret", "Signed with another secret", f"t={t},v0={wrong}")
    add("signature", "tampered_body", "Body changed after signing", header(t),
        body=BODY.replace("conv_conformance", "conv_tampered"))
    add("signature", "uppercase_hex", "Correct digest in uppercase hex", f"t={t},v0={sig.upper()}")
    add("signature", "truncated_hex", "Digest missing its last two characters", f"t={t},v0={sig[:-2]}")
    add("signature", "non_ascii_signature", "Non-ASCII characters in the v0 value", f"t={t},v0=ünïcödé")
    add("signature", "two_v0_wrong_first", "Two v0 parts, wrong one first (key rotation)",
        f"t={t},v0={wrong},v0={sig}")
    add("signature", "two_v0_right_first", "Two v0 parts, right one first (key rotation)",
        f"t={t},v0={sig},v0={wrong}")

    add("format", "space_after_comma", "Space after the comma", f"t={t}, v0={sig}")
    add("format", "two_timestamps", "Two t parts; the signature covers the first",
        f"t={t},t={now - 31 * 60},v0={sig}")

    add("payload", "invalid_json", "Correctly signed body that is not JSON", header(t, "not json"), body="not json")
    add("payload", "json_array", "Correctly signed JSON array instead of an object", header(t, "[1,2]"),
        body="[1,2]")
    add("payload", "json_trailing_data", "Correctly signed JSON object followed by more data",
        header(t, BODY + "x"), body=BODY + "x")
    return v


def main() -> int:
    now = int(time.time())
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "vectors.json")
    out.write_text(json.dumps({"generated_at": now, "vectors": vectors(now)}, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {out} with {len(vectors(now))} vectors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
