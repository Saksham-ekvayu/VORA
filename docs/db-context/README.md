# Database Context

This folder contains a lightweight snapshot of the `vora` PostgreSQL database.

## Files

- `schema.sql` — Complete database schema, including tables, columns, keys, constraints, and indexes.
- `relationships.sql` — Foreign-key relationships between tables.
- `sample_data.json` — Up to 3 sample rows from each table.
- `export-sample-data.ps1` — Script to generate/update `sample_data.json`.

## Regenerate

From `docs/db-context`:

### Schema

```cmd
"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -h localhost -p 5432 -U postgres -d vora --schema-only --no-owner --no-privileges -f schema.sql
```

### Relationships

```cmd
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -p 5432 -U postgres -d vora -c "SELECT tc.table_schema, tc.table_name, kcu.column_name, ccu.table_schema AS foreign_table_schema, ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name, tc.constraint_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema WHERE tc.constraint_type = 'FOREIGN KEY' ORDER BY tc.table_schema, tc.table_name, tc.constraint_name;" > relationships.sql
```

### Sample Data

```cmd
powershell -ExecutionPolicy Bypass -File .\export-sample-data.ps1
```

Regenerate all three data files after significant schema or data changes.

> `sample_data.json` contains real database values. Check for secrets or sensitive data before committing or sharing.
