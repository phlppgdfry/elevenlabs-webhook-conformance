#!/usr/bin/env bash
# Fetch every SDK at the commit pinned in sdks.json, build what its runner needs, generate fresh
# signed vectors, run all runners, and write results/*.json plus RESULTS.md.
#
#   ./run.sh                 all SDKs
#   ./run.sh go ruby         only these runners (by runner name)
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$PWD
CACHE=$ROOT/.cache
mkdir -p "$CACHE" results
ONLY=" ${*:-} "

slug() { echo "$1" | tr 'A-Z' 'a-z' | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g'; }

# name|runner|repo|ref, one per line
SDKS=$(python3 -c 'import json; [print("|".join((s["name"], s["runner"], s["repo"], s["ref"]))) for s in json.load(open("sdks.json"))]')

fetch() { # dir repo ref
  local dir=$1 repo=$2 ref=$3
  if [ "$(git -C "$dir" rev-parse HEAD 2>/dev/null || true)" != "$ref" ]; then
    rm -rf "$dir" && git init -q "$dir"
    git -C "$dir" fetch -q --depth 1 "https://github.com/$repo.git" "$ref"
    git -C "$dir" checkout -q FETCH_HEAD
  fi
}

build() { # runner dir
  local runner=$1 dir=$2
  case $runner in
    node) (cd "$dir" && [ -f dist/index.js ] || { yarn install --frozen-lockfile --ignore-scripts --silent && yarn -s build; }) ;;
    python) [ -x "$dir/.venv/bin/python" ] || { uv venv -q -p 3.12 "$dir/.venv" && uv pip install -q -p "$dir/.venv" "$dir"; } ;;
    go) (cd runners/go && go mod tidy >/dev/null 2>&1 && go build -o "$CACHE/go-runner" .) ;;
    dotnet) dotnet build -c Release -v quiet -nologo runners/dotnet/Runner.csproj -o "$CACHE/dotnet-runner" >/dev/null ;;
    java)
      mvn -q -f runners/java/pom.xml dependency:build-classpath -Dmdep.outputFile="$CACHE/java.cp" >/dev/null
      javac -nowarn -cp "$(cat "$CACHE/java.cp")" -sourcepath "$dir/src/main/java" -d "$CACHE/java-out" runners/java/Runner.java ;;
    ruby) (cd "$dir" && bundle config set --local path "$CACHE/ruby-gems" >/dev/null && bundle install --quiet >/dev/null) ;;
    rust) CARGO_TARGET_DIR=$CACHE/rust-target cargo build -q --release --manifest-path runners/rust/Cargo.toml ;;
    php) docker run --rm -v "$dir":/sdk -w /sdk composer:2 composer install -q --no-dev --no-interaction --ignore-platform-reqs >/dev/null ;;
  esac
}

run() { # runner dir vectors
  local runner=$1 dir=$2 vec=$3
  case $runner in
    node) SDK_DIR=$dir node runners/node/runner.cjs "$vec" ;;
    python) "$dir/.venv/bin/python" -I runners/python/runner.py "$vec" ;;
    go) "$CACHE/go-runner" "$vec" ;;
    dotnet) "$CACHE/dotnet-runner/Runner" "$vec" ;;
    java) java -cp "$CACHE/java-out:$(cat "$CACHE/java.cp")" Runner "$vec" ;;
    ruby) (cd "$dir" && BUNDLE_GEMFILE=$dir/Gemfile bundle exec ruby -I lib "$ROOT/runners/ruby/runner.rb" "$vec") ;;
    rust) "$CACHE/rust-target/release/conformance-runner" "$vec" ;;
    php) docker run --rm -v "$dir":/sdk -v "$ROOT":/w composer:2 php /w/runners/php/runner.php /sdk/vendor/autoload.php "/w/${vec#"$ROOT"/}" ;;
  esac
}

selected() { [ "$ONLY" = "  " ] || [[ "$ONLY" == *" $1 "* ]]; }

echo "== fetch and build"
while IFS='|' read -r name runner repo ref; do
  selected "$runner" || continue
  dir=$CACHE/$(slug "$name")
  # The Go, Rust and .NET runners reference fixed checkout paths.
  case $runner in go|rust|dotnet) dir=$CACHE/$runner ;; esac
  echo "   $name @ ${ref:0:7}"
  fetch "$dir" "$repo" "$ref"
  failed=results/$(slug "$name").build-failed
  rm -f "$failed"
  # A broken build is a finding too: record it and keep going.
  if ! build "$runner" "$dir" > "$CACHE/build.log" 2>&1; then
    echo "   $name: BUILD FAILED"; tail -40 "$CACHE/build.log" > "$failed"
  fi
done <<< "$SDKS"

echo "== generate vectors"
python3 generate_vectors.py "$ROOT/vectors.json"

echo "== run"
while IFS='|' read -r name runner repo ref; do
  selected "$runner" || continue
  dir=$CACHE/$(slug "$name")
  case $runner in go|rust|dotnet) dir=$CACHE/$runner ;; esac
  out=results/$(slug "$name").json
  if [ -f "results/$(slug "$name").build-failed" ]; then rm -f "$out"; continue; fi
  if run "$runner" "$dir" "$ROOT/vectors.json" > "$out.tmp" 2> "$out.err"; then
    mv "$out.tmp" "$out" && rm -f "$out.err" && echo "   $name: ok"
  else
    echo "   $name: RUNNER FAILED (see $out.err)"; rm -f "$out.tmp"
  fi
done <<< "$SDKS"

python3 report.py
