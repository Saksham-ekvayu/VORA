# Database Context

This folder contains a lightweight snapshot of the `vora` PostgreSQL database.

## Files

- `schema.sql` — Complete database schema, including tables, columns, keys, constraints, and indexes.
- `sample_data.json` — Up to 3 sample rows from each table.
- `export-sample-data.ps1` — Script to generate/update `sample_data.json`.

## Regenerate

From `docs/db-context`:

### Schema

```cmd
"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -h localhost -p 5432 -U postgres -d vora --schema-only --no-owner --no-privileges -f schema.sql
```

### Sample Data

```cmd
powershell -ExecutionPolicy Bypass -File .\export-sample-data.ps1
```

Regenerate all three data files after significant schema or data changes.

> `sample_data.json` contains real database values. Check for secrets or sensitive data before committing or sharing.
