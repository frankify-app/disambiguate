# Canary Signals

Lightweight CI checks that flag checkpoint categories automatically. These produce PR labels or bot comments telling you where to look. None of these block merges — they route attention.

## 1. New dependency detection (ARCH)

Compare dependency manifests against the base branch.

```bash
#!/bin/bash
# canary-deps.sh — detect new dependencies
ADDED_DEPS=""

# Node
if git diff origin/main --name-only | grep -q "package.json"; then
  ADDED_DEPS+=$(diff <(git show origin/main:package.json 2>/dev/null | jq -r '.dependencies // {} | keys[]' 2>/dev/null | sort) \
                     <(jq -r '.dependencies // {} | keys[]' package.json 2>/dev/null | sort) \
                | grep "^>" | sed 's/^> /npm: /')
  ADDED_DEPS+=$'\n'
  ADDED_DEPS+=$(diff <(git show origin/main:package.json 2>/dev/null | jq -r '.devDependencies // {} | keys[]' 2>/dev/null | sort) \
                     <(jq -r '.devDependencies // {} | keys[]' package.json 2>/dev/null | sort) \
                | grep "^>" | sed 's/^> /npm-dev: /')
fi

# Python
if git diff origin/main --name-only | grep -qE "(requirements.*\.txt|pyproject\.toml|setup\.cfg)"; then
  # For requirements.txt
  for f in $(git diff origin/main --name-only | grep "requirements.*\.txt"); do
    ADDED_DEPS+=$(diff <(git show origin/main:"$f" 2>/dev/null | grep -v "^#" | cut -d= -f1 | cut -d'>' -f1 | cut -d'<' -f1 | tr -d ' ' | sort) \
                       <(grep -v "^#" "$f" | cut -d= -f1 | cut -d'>' -f1 | cut -d'<' -f1 | tr -d ' ' | sort) \
                  | grep "^>" | sed 's/^> /pip: /')
  done
fi

if [ -n "$(echo "$ADDED_DEPS" | tr -d '[:space:]')" ]; then
  echo "🏗️ ARCH: New dependencies detected"
  echo "$ADDED_DEPS" | grep -v "^$"
fi
```

## 2. Public API surface diff (IFACE)

Detect changes to exported functions, route definitions, config schemas.

```bash
#!/bin/bash
# canary-iface.sh — detect interface changes
FLAGS=""

# OpenAPI / Swagger changes
if git diff origin/main --name-only | grep -qiE "(openapi|swagger)\.(json|ya?ml)"; then
  FLAGS+="OpenAPI schema modified\n"
fi

# GraphQL schema changes
if git diff origin/main --name-only | grep -qiE "\.graphql$|schema\.gql"; then
  FLAGS+="GraphQL schema modified\n"
fi

# Route file changes (common patterns)
if git diff origin/main -- '*.ts' '*.js' '*.py' | grep -qE "^[+].*(router\.(get|post|put|delete|patch)|@app\.(route|get|post)|FastAPI|express\.Router)"; then
  FLAGS+="HTTP route definitions changed\n"
fi

# Environment variable additions
if git diff origin/main -- '*.ts' '*.js' '*.py' '*.go' '*.rs' | grep -qE "^[+].*process\.env\.|^[+].*os\.environ|^[+].*env::var"; then
  NEW_ENVS=$(git diff origin/main -- '*.ts' '*.js' '*.py' '*.go' '*.rs' \
    | grep -E "^[+].*process\.env\.|^[+].*os\.environ|^[+].*env::var" \
    | grep -oE "(process\.env\.\w+|os\.environ\[.[^\]]+\]|env::var\(.[^)]+\))" | sort -u)
  FLAGS+="New environment variables: $NEW_ENVS\n"
fi

# CLI argument changes
if git diff origin/main -- '*.py' | grep -qE "^[+].*(add_argument|add_option|click\.(option|argument))"; then
  FLAGS+="CLI arguments modified\n"
fi

if [ -n "$FLAGS" ]; then
  echo "🔌 IFACE: Public interface changes detected"
  echo -e "$FLAGS"
fi
```

## 3. Migration and irreversible operation detection (IRREV)

```bash
#!/bin/bash
# canary-irrev.sh — detect irreversible operations
FLAGS=""

# Migration files
MIGRATIONS=$(git diff origin/main --name-only | grep -iE "(migrations?/|alembic/|flyway/|liquibase)" || true)
if [ -n "$MIGRATIONS" ]; then
  FLAGS+="Migration files:\n$MIGRATIONS\n"
fi

# Destructive SQL
if git diff origin/main -- '*.sql' '*.py' '*.ts' '*.js' | grep -qiE "^[+].*(DROP|TRUNCATE|DELETE FROM|ALTER.*DROP)"; then
  FLAGS+="Destructive SQL detected\n"
fi

# File deletion operations
if git diff origin/main -- '*.py' '*.ts' '*.js' '*.go' '*.rs' | grep -qE "^[+].*(os\.remove|os\.unlink|shutil\.rmtree|fs\.unlink|fs\.rm|remove_dir_all)"; then
  FLAGS+="File deletion operations in code\n"
fi

# Deployment config changes
if git diff origin/main --name-only | grep -qiE "(deploy|\.github/workflows|Dockerfile|docker-compose|k8s/|helm/|terraform/)"; then
  DEPLOY_FILES=$(git diff origin/main --name-only | grep -iE "(deploy|\.github/workflows|Dockerfile|docker-compose|k8s/|helm/|terraform/)")
  FLAGS+="Deployment config changes:\n$DEPLOY_FILES\n"
fi

if [ -n "$FLAGS" ]; then
  echo "⚠️ IRREV: Irreversible operations detected"
  echo -e "$FLAGS"
fi
```

## 4. Security-sensitive path detection (SEC)

```bash
#!/bin/bash
# canary-sec.sh — detect security-sensitive changes
FLAGS=""

# Auth-related file changes
AUTH_FILES=$(git diff origin/main --name-only | grep -iE "(auth|login|session|token|credential|secret|password|permission|rbac|acl|oauth|jwt|crypto)" || true)
if [ -n "$AUTH_FILES" ]; then
  FLAGS+="Auth-related files modified:\n$AUTH_FILES\n"
fi

# New network listeners
if git diff origin/main -- '*.py' '*.ts' '*.js' '*.go' '*.rs' | grep -qE "^[+].*(\.listen\(|bind\(|serve\(|createServer|http\.Server|net\.Listen)"; then
  FLAGS+="New network listener\n"
fi

# CORS/CSP changes
if git diff origin/main | grep -qiE "^[+].*(cors|content-security-policy|access-control-allow)"; then
  FLAGS+="CORS/CSP headers modified\n"
fi

# Raw SQL construction (injection risk)
if git diff origin/main -- '*.py' '*.ts' '*.js' | grep -qE "^[+].*(f\".*SELECT|f\".*INSERT|f\".*UPDATE|f\".*DELETE|\`.*\$\{.*SELECT)"; then
  FLAGS+="Potential SQL injection: string-interpolated queries\n"
fi

# Hardcoded secrets (crude but useful)
if git diff origin/main | grep -qE "^[+].*(password|secret|api_key|apikey|token)\s*=\s*['\"][^'\"]{8,}"; then
  FLAGS+="Potential hardcoded secret\n"
fi

if [ -n "$FLAGS" ]; then
  echo "🔒 SEC: Security-sensitive changes detected"
  echo -e "$FLAGS"
fi
```

## 5. Novel file detection (NOVEL)

Detects files added to directories where they have no structural siblings — a sign the agent is inventing a new pattern rather than following an existing one.

```bash
#!/bin/bash
# canary-novel.sh — detect novel patterns
FLAGS=""

# New files in directories with no similar files
for NEW_FILE in $(git diff origin/main --name-only --diff-filter=A); do
  DIR=$(dirname "$NEW_FILE")
  EXT="${NEW_FILE##*.}"

  # Count existing files with same extension in that directory (on main)
  SIBLING_COUNT=$(git ls-tree origin/main "$DIR/" 2>/dev/null | grep -c "\.$EXT$" || echo "0")

  if [ "$SIBLING_COUNT" -eq 0 ]; then
    FLAGS+="Novel file: $NEW_FILE (no .$EXT siblings in $DIR/)\n"
  fi
done

# New framework/library imports not used elsewhere in codebase
for IMPORT in $(git diff origin/main -- '*.py' | grep -E "^[+](import |from )" | sed 's/^+//' | awk '{print $2}' | cut -d. -f1 | sort -u); do
  if ! git grep -q "import $IMPORT\|from $IMPORT" origin/main -- '*.py' 2>/dev/null; then
    FLAGS+="Novel import: $IMPORT (not used elsewhere in codebase)\n"
  fi
done

if [ -n "$FLAGS" ]; then
  echo "🆕 NOVEL: New patterns detected (no existing precedent)"
  echo -e "$FLAGS"
fi
```

## 6. Decision marker summary (all categories)

Collects all `DECISION:` markers from changed files and presents them as the PR review summary.

```bash
#!/bin/bash
# canary-decisions.sh — collect DECISION: markers from changed files
MARKERS=$(git diff origin/main --name-only | xargs grep -Hn "DECISION:" 2>/dev/null || true)

if [ -n "$MARKERS" ]; then
  echo "📋 DECISION MARKERS found in this PR:"
  echo ""
  echo "$MARKERS" | while IFS= read -r line; do
    FILE=$(echo "$line" | cut -d: -f1)
    LINE_NUM=$(echo "$line" | cut -d: -f2)
    CONTENT=$(echo "$line" | cut -d: -f3- | sed 's/^[[:space:]]*//' | sed 's|^//\s*||;s|^#\s*||;s|^--\s*||;s|^\*\s*||')
    echo "  $FILE:$LINE_NUM — $CONTENT"
  done
  echo ""
  echo "Review these decisions before merging."
else
  echo "✅ No DECISION: markers — this PR is routine."
fi
```

## Combining into a single CI step

```bash
#!/bin/bash
# canary-all.sh — run all canary checks
echo "=== Agentic Review Canary Signals ==="
echo ""

bash canary-decisions.sh 2>/dev/null
echo ""
bash canary-deps.sh 2>/dev/null
bash canary-iface.sh 2>/dev/null
bash canary-irrev.sh 2>/dev/null
bash canary-sec.sh 2>/dev/null
bash canary-novel.sh 2>/dev/null

echo ""
echo "=== End Canary Signals ==="
```

## GitHub Actions integration

````yaml
name: Agentic Review Canary
on: pull_request

jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Run canary signals
        id: canary
        run: |
          OUTPUT=$(bash .github/scripts/canary-all.sh)
          echo "$OUTPUT"
          # Post as PR comment
          if [ -n "$OUTPUT" ]; then
            echo "canary_output<<EOF" >> $GITHUB_OUTPUT
            echo "$OUTPUT" >> $GITHUB_OUTPUT
            echo "EOF" >> $GITHUB_OUTPUT
          fi
      - name: Comment on PR
        if: steps.canary.outputs.canary_output
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: '## 🔍 Agentic Review Canary\n\n```\n' +
                    '${{ steps.canary.outputs.canary_output }}' +
                    '\n```\n\nThese are the sections of this PR that need human review. Everything else is routine.'
            })
````

## Adapting to your stack

These scripts are starting points. Tune the file patterns and grep expressions to your project. The important thing is the category mapping — each check should clearly label which of the six categories (ARCH, SCOPE, IFACE, SEC, IRREV, NOVEL) it belongs to, so the reviewer knows why they're looking at something.
