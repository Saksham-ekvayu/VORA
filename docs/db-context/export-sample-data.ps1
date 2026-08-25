$Psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$Output = "sample_data.json"

if (-not $env:PGPASSWORD) {
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

$allTables = $tables | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

Write-Host "========================================="
Write-Host "             Available Tables            "
Write-Host "========================================="
Write-Host "0. All Tables"
for ($i = 0; $i -lt $allTables.Count; $i++) {
    Write-Host "$($i + 1). $($allTables[$i])"
}
Write-Host "========================================="

$selection = Read-Host "Enter table numbers separated by comma (e.g. 1,3,4) or 0 for all"

$selectedTables = @()
if ([string]::IsNullOrWhiteSpace($selection) -or $selection.Trim() -eq "0") {
    $selectedTables = $allTables
} else {
    $indices = $selection.Split(',') | ForEach-Object { $_.Trim() }
    foreach ($idx in $indices) {
        if ([int]::TryParse($idx, [ref]$null)) {
            $i = [int]$idx
            if ($i -gt 0 -and $i -le $allTables.Count) {
                $selectedTables += $allTables[$i - 1]
            }
        }
    }
}

if ($selectedTables.Count -eq 0) {
    Write-Host "No valid tables selected. Exiting."
    exit
}

$limitInput = Read-Host "Enter row limit for sample data (default 3)"
$Limit = 3
if (-not [string]::IsNullOrWhiteSpace($limitInput)) {
    if ([int]::TryParse($limitInput.Trim(), [ref]$null)) {
        $Limit = [int]$limitInput.Trim()
    }
}

$result = [ordered]@{}

foreach ($table in $selectedTables) {
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
    LIMIT $Limit
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
