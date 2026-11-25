# ElevenLabs webhook verification: cross-SDK conformance

ElevenLabs signs every webhook with an `ElevenLabs-Signature: t=<unix seconds>,v0=<hex HMAC-SHA256>` header. Each official SDK verifies it with its own **hand-written** function, because Fern's generated verifier can't parse that compound header:

| SDK | Function |
|---|---|
| TypeScript | `client.webhooks.constructEvent` |
| Python | `client.webhooks.construct_event` |
| Go | `webhooks.ConstructEvent` |
| .NET | `WebhookVerifier.ConstructEvent` |
| Java | `WebhookVerifier.constructEvent` |
| Ruby | `Elevenlabs::Webhooks::Verifier.construct_event` |
| Rust | `webhooks::construct_event` |
| PHP | `WebhookVerifier::constructEvent` |

That makes eight independent implementations of one security check. This repository runs all of them against the **same signed inputs** and shows where they agree and where they don't.

> Unofficial. Not affiliated with or endorsed by ElevenLabs. It only reads the public SDK source code, uses a made-up secret and calls no API.

**→ [RESULTS.md](RESULTS.md)** has the full matrix.

## Findings

Run of 25 November 2026: 30 vectors against the 8 released SDKs, plus the two open fix PRs. The released SDKs give the same answer on **20 of the 30 vectors**. These are the other 10:

1. **TypeScript lets a non-numeric timestamp skip the replay window.** `Number("abc")` is `NaN`, and `NaN < tolerance` is `false`, so `t=abc`, `t=1e12`, `t=<now>.5` and `t=<now>abc` are all accepted. The other seven reject at least `abc`. Fixed in elevenlabs/elevenlabs-js#509.
2. **Python crashes on the same inputs.** `int(timestamp)` raises `ValueError` instead of the documented `BadRequestError`, so a typical handler returns a 500. Fixed in elevenlabs/elevenlabs-python#947.
3. **The SDKs fall into three timestamp-parsing families:**

   | Input (correctly signed) | Strict digits (.NET) | Integer parse (Go, Java, Rust) | Leading-digits cast (Ruby, PHP) |
   |---|---|---|---|
   | `+<now>` | reject | accept | accept |
   | ` <now>` | reject | reject | accept |
   | `<now>.5` | reject | reject | accept |
   | `<now>abc` | reject | reject | accept |
   | `1e12` | reject | reject | Ruby rejects, PHP accepts (`(int)"1e12"` is 10¹², far in the future) |

   The two fix PRs follow .NET (whole number of seconds, digits only).
4. **TypeScript reads duplicate header parts the other way round.** It takes the *first* `t=` and the *first* `v0=` (`Array.find`). The other seven take the *last* (a loop that overwrites). The same header `t=…,v0=<wrong>,v0=<right>` is rejected by TypeScript and accepted by everyone else, and the reverse order flips both answers. ElevenLabs sends one of each today. It would matter if signatures are ever sent twice, for example during secret rotation.
5. **Go and .NET reject a body that is a JSON array**, because they return a JSON object type. The others return whatever JSON was sent.

What they all agree on: the missing-field errors, the stale (31-minute) and boundary (29-minute) timestamps, future timestamps (accepted), wrong secrets, tampered bodies, uppercase/truncated/non-ASCII signatures (rejected), a space after the comma (rejected as "no t/v0"), invalid JSON and trailing data.

**Side finding:** the Rust SDK's `main` (`28bb069`) does not compile. Three SDK regenerations between 20 and 23 November renamed generated types that the hand-written `agent_builder`, `agent_tools` and `flows` modules use (12 errors). The repository's CI did not start between 20 and 24 November (`startup_failure`), so it went unnoticed until the regeneration PR of 25 November failed. The suite pins Rust to `2490866`, the last commit that builds. Its `src/webhooks` is identical.

## How it works

```
generate_vectors.py ──► vectors.json ──► runners/<language>/ ──► results/<sdk>.json ──► report.py ──► RESULTS.md
                      (30 signed inputs)   (calls the real SDK      (outcome per vector)    (matrix +
                                            function, pinned)                                divergences)
```

- **`sdks.json`** pins each SDK to an exact commit. The suite builds that commit from source, so the result is reproducible and every cell links to the exact code that produced it. The TypeScript and Python rows also run the open fix PRs, so you can see what the fix changes.
- **`generate_vectors.py`** signs every input with a real HMAC, including the malformed ones, so a rejection always comes from the check under test, never from a broken signature.
- **The runners** are about 30 lines each. They call the SDK's public function and record `ok` or the error. Every SDK reports the same error messages ("Timestamp outside the tolerance zone", ...), so outcomes can be compared directly across languages.
- **`report.py`** takes the most common outcome among the released SDKs as the consensus and marks every cell that differs. ⚠ means an exception that is none of the documented outcomes: a crash, not a rejection.

## Run it

Needs Node 20+, [uv](https://docs.astral.sh/uv/), Go, .NET 10, Java 21 + Maven, Ruby + Bundler, Rust and Docker (for PHP).

```sh
./run.sh               # every SDK, about 10 minutes the first time, seconds after that
./run.sh go python     # only some runners
python3 update_pins.py # move every pin to the latest commit, then ./run.sh
```

A [weekly workflow](.github/workflows/conformance.yml) moves the pins to the latest commits and publishes the matrix in the job summary, so a regression in any SDK shows up within a week.

## Why the differences are (mostly) not vulnerabilities

Every vector here is correctly signed, so an attacker without the secret can't produce any of them. The divergences matter for other reasons:

- **Crashes** (⚠): an unexpected exception type turns into a 500 in a typical webhook handler instead of the documented 400.
- **Replay window**: a timestamp that the parser can't read must not skip the 30-minute window.
- **Consistency**: the same header should give the same answer in every SDK. Otherwise a team that verifies in one language and re-verifies or tests in another gets different results.

The one property with direct security impact, comparing the signature in constant time, is not testable from outside. It was checked by reading the code: all SDKs except TypeScript and Python used a constant-time compare. elevenlabs/elevenlabs-js#509 and elevenlabs/elevenlabs-python#947 fix those two.

## License

MIT
