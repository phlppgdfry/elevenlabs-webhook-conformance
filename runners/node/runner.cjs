// Usage: SDK_DIR=<built elevenlabs-js checkout> node runner.cjs vectors.json
const fs = require("node:fs");
const path = require("node:path");
const { ElevenLabsClient } = require(path.join(process.env.SDK_DIR, "dist", "index.js"));

(async () => {
    const { vectors } = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
    const webhooks = new ElevenLabsClient({ apiKey: "conformance" }).webhooks;
    const results = {};
    for (const v of vectors) {
        try {
            await webhooks.constructEvent(v.body, v.header, v.secret);
            results[v.id] = { ok: true };
        } catch (e) {
            results[v.id] = { ok: false, error: e?.constructor?.name ?? typeof e, message: String(e?.message ?? e) };
        }
    }
    process.stdout.write(JSON.stringify(results));
})();
