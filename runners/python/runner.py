"""Usage: python runner.py vectors.json  (with the elevenlabs package under test installed)"""
import json
import sys

from elevenlabs.client import ElevenLabs

vectors = json.load(open(sys.argv[1], encoding="utf-8"))["vectors"]
webhooks = ElevenLabs(api_key="conformance").webhooks
results = {}
for v in vectors:
    try:
        webhooks.construct_event(v["body"], v["header"], v["secret"])
        results[v["id"]] = {"ok": True}
    except Exception as e:  # noqa: BLE001 - every outcome is data here
        body = getattr(e, "body", None)
        message = getattr(body, "error", None) or str(e)
        results[v["id"]] = {"ok": False, "error": type(e).__name__, "message": str(message)}
sys.stdout.write(json.dumps(results))
