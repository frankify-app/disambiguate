# Decision Marker Examples

## Format

```text
// DECISION:<TAG> — <explanation>
```

Tag on same line as `DECISION:` prefix. Explanation can wrap to subsequent comment lines. Use language-native comment syntax.

## Examples

```typescript
// DECISION:ARCH — Using SQLite instead of PostgreSQL. Single-node cache,
// not shared state. Migrate to Postgres if this goes multi-node.
const db = new Database("./cache.sqlite");
```

```python
# DECISION:SEC — No rate limiting. Internal-only behind Tailscale.
# Add rate limiting before any public exposure.
@app.route("/internal/sync", methods=["POST"])
```

```python
# DECISION:NOVEL — No stream processing pattern in this repo.
# Adapted consumer pattern from Kafka docs.
async def consume_events(topic: str):
```

```typescript
// DECISION:IFACE — Changed /api/users from array to paginated envelope
// { data: [], cursor: string }. All frontend callers need update.
export async function listUsers(cursor?: string): Promise<PaginatedResponse<User>> {
```

```python
# DECISION:IRREV — Drops legacy_roles column. Data already migrated
# to roles table (migration 002). Not reversible.
def upgrade():
    op.drop_column('users', 'legacy_roles')
```

```python
# DECISION:SCOPE — Issue #142 says "add user filtering" without specifying
# fields. Implementing name + email only (fields in list view).
```
