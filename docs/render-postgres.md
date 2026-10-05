# Switching Render to PostgreSQL

The cloud demo uses SQLite on Render's temporary disk, so **every deploy or
restart erases all data** (sessions, attendance, Edge events). The app also
runs on PostgreSQL: set `DATABASE_URL` to a Postgres URL and it uses the
`psycopg` driver automatically. Tables are created on startup.

## Steps (Render dashboard)

1. **New → PostgreSQL**. Use the same region as the web service (Singapore).
   Note the plan's limits: free databases expire after a set period.
2. When it is ready, copy its **Internal Database URL**.
3. Update `render.yaml` so Blueprint syncs do not reset the URL to SQLite.
   Replace the `DATABASE_URL` entry with:

   ```yaml
   - key: DATABASE_URL
     fromDatabase:
       name: <your-database-name>
       property: connectionString
   ```

   Or delete the `DATABASE_URL` entry from `render.yaml` and set it in
   **Environment** on the web service instead.
4. Deploy. The first start creates the tables and seeds the demo data.

## Check

- `/health` returns 200.
- **System Health** shows "Postgresql database connection is working."
- Run the Edge Agent, then redeploy: the attendance record is still there.

## Testing locally against PostgreSQL

```powershell
$env:TEST_DATABASE_URL = "postgresql://user@127.0.0.1:5432/empty_test_db"
backend\.venv\Scripts\python.exe -m pytest
```

Use an empty database; the tests write demo data into it.
