$Psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$Output = "sample_data.json"

$env:PGPASSWORD = Read-Host "Enter PostgreSQL password" -AsSecureString |
    ForEach-Object {
        $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($_)
        try {
            [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        }
        finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        }
    }

# Get all non-system tables.
$tableQuery = @"
SELECT schemaname || '.' || tablename
FROM pg_catalog.pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;
"@

$tables = & $Psql `
    -h localhost `
    -p 5432 `
    -U postgres `
    -d vora `
    -At `
    -c $tableQuery

$result = [ordered]@{}

foreach ($table in $tables) {
    if ([string]::IsNullOrWhiteSpace($table)) {
        continue
    }

    $parts = $table.Split('.', 2)
    $schema = $parts[0]
    $tableName = $parts[1]

    Write-Host "Exporting: $table"

    # PostgreSQL identifiers are safely quoted by replacing double quotes.
    $safeSchema = $schema.Replace('"', '""')
    $safeTable = $tableName.Replace('"', '""')

    $query = @"
SELECT COALESCE(
    jsonb_agg(row_to_json(t)),
    '[]'::jsonb
)
FROM (
    SELECT *
    FROM "$safeSchema"."$safeTable"
    LIMIT 3
) t;
"@

    $json = & $Psql `
        -h localhost `
        -p 5432 `
        -U postgres `
        -d vora `
        -At `
        -c $query 2>$null

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($json)) {
        $result[$table] = @()
        continue
    }

    try {
        $parsed = $json | ConvertFrom-Json
        $result[$table] = $parsed
    }
    catch {
        $result[$table] = @()
    }
}

$result | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $Output

Write-Host ""
Write-Host "Done!"
Write-Host "Created: $Output"
