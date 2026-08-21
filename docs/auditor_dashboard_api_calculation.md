# Auditor Dashboard API - Simple Functionality & Calculation Guide

This document explains the **current implementation** of the Auditor Dashboard APIs.

The main purpose is to understand:

- Which table/document is used as input.
- How the latest package is selected.
- How controls and deployment points are counted.
- How each API calculates its response.
- Which calculation is used for each response field.
- How the dashboard tables are built, filtered, sorted and paginated.

> **Important:** This document describes the current code behavior. Some variable names say `deployment_points`, but in a few places the current implementation actually counts **controls** instead of individual deployment points. This is explained below so the code is easier to understand.

---

# 1. Main Data Flow

Almost all Auditor Dashboard APIs follow this flow:

```text
DeploymentFramework
        |
        | packages[]
        v
get_latest_packages()
        |
        +---- latest package
        |
        +---- gapAnalysis ID
        |
        +---- mergeDocument ID
        v
PackageGapAnalysis + DeploymentPackageMerge
        |
        +---- FrameworkAssignment
        |
        +---- deployment_gap_results
        +---- controls_data
        v
process_gap_analyses()
        |
        +---- total controls
        +---- passing controls
        +---- extra controls
        +---- critical gaps
        +---- framework health
        +---- implemented count
        v
API-specific response builder
        |
        +---- Analytics
        +---- Overall Protection table
        +---- Critical Gaps table
        +---- Controls Passing table
        +---- Extra Controls table
        +---- Deployment Points table
        +---- Framework Details
```

The router first loads the data and then the helper functions do most of the calculations.

The router imports these main helper functions:

- `get_latest_packages`
- `process_gap_analyses`
- `build_overall_protection_rows`
- `build_critical_gaps_response`
- `build_controls_passing_response`
- `build_extra_controls_response`
- `process_deployment_points`
- `process_deployment_points_detailed`

---

# 2. Important Tables / Documents

## 2.1 DeploymentFramework

This is the starting point.

The API first gets all deployment frameworks for the current tenant:

```python
select(DeploymentFramework).where(
    DeploymentFramework.tenantId == tenant_id
)
```

Each deployment framework contains `packages`.

Example structure:

```text
DeploymentFramework
|
+-- id
+-- frameworkName
+-- frameworkVersion
+-- assignedFrameworkId
+-- packages[]
      |
      +-- packageVersion
      +-- createdAt
      +-- gapAnalysis
      +-- mergeDocument
      +-- comparison
```

The current database sample also shows package records containing fields such as:

```text
packageVersion = 1.0.0
gapAnalysis = <ID>
mergeDocument = <ID>
```

---

# 3. How the Latest Package Is Selected

Function:

```python
get_latest_packages(dfs)
```

For every DeploymentFramework:

```python
latest_pkg = max(
    df.packages,
    key=lambda p: get_nested(p, "createdAt") or ""
)
```

So the package with the latest `createdAt` is selected.

Example:

```text
Package 1 -> createdAt 10:00
Package 2 -> createdAt 12:00
Package 3 -> createdAt 15:00

Latest package = Package 3
```

From that package the code extracts:

```text
gapAnalysis
mergeDocument
```

These IDs are then used to load:

```text
PackageGapAnalysis
DeploymentPackageMerge
```

---

# 4. Important Input Data Relationship

The calculations mainly use these two documents:

```text
DeploymentPackageMerge
        |
        +-- controls.controls_data[]
                |
                +-- section
                      |
                      +-- controls[]
                            |
                            +-- id
                            +-- name
                            +-- description
                            +-- deployment_points[]

PackageGapAnalysis
        |
        +-- gapAnalysis
              |
              +-- framework_assignment_id
              +-- deployment_framework_id
              +-- deployment_gap_results[]
                    |
                    +-- deployment_framework_control_id
                    +-- implementation_status
                    +-- gap_score
```

### Simple meaning

`DeploymentPackageMerge` tells the system:

> "Which controls are expected and how many deployment points are configured for each control?"

`PackageGapAnalysis` tells the system:

> "What is the current implementation status of those controls/deployment points?"

---

# 5. How Expected Controls Are Created

Function:

```python
extract_expected_controls()
```

The function reads:

```text
mergeDocument.controls.controls_data
```

For every control:

```python
required_dps = len(control["deployment_points"])
```

The result looks like:

```text
Control A
    required_dps = 3

Control B
    required_dps = 5

Control C
    required_dps = 2
```

The expected control object contains:

```text
id
name
description
required_dps
is_extra
```

---

# 6. How Implemented Controls Are Found

Function:

```python
extract_actual_implemented()
```

The function reads:

```text
gapAnalysis.deployment_gap_results[]
```

For every result it checks:

```text
implementation_status
```

The following statuses are treated as implemented:

```text
implemented
compliant
passed
fully implemented
```

If a result has one of these statuses, the implementation count for that control is increased.

Example:

```text
Control A
    result 1 -> implemented
    result 2 -> implemented
    result 3 -> pending

actual_implemented[A] = 2
```

---

# 7. Important Current Logic: Control Is Considered Implemented if Count > 0

The current code uses:

```python
is_implemented = impl_dps > 0
```

This means:

```text
required DPs = 5
implemented DPs = 1
```

The control is still considered:

```text
Implemented / Passing
```

It does **not** require all 5 deployment points to be implemented.

This is important when reading the dashboard numbers.

---

# 8. process_gap_analyses()

This is the main calculation function used by multiple APIs.

It processes every latest framework package.

For each framework it calculates:

```text
total controls
passing controls
extra controls
critical gaps
active gaps
total count used for protection
implemented count used for protection
previous implemented count
framework health
framework trend
framework weight score
```

The main flow is:

```text
latest package
      |
      +-- gapAnalysis
      +-- mergeDocument
      |
      v
expected_controls
      +
actual_implemented
      |
      v
evaluate_controls()
      |
      v
framework metrics
      |
      v
overall metrics
```

---

# 9. evaluate_controls()

For every expected control:

```python
fw_total_controls += 1
```

Then:

```python
req_dps = expected["required_dps"]
impl_dps = actual_implemented.get(ctrl_id, 0)
is_implemented = impl_dps > 0
```

If implemented:

```text
passing controls += 1
implemented count += 1
```

If not implemented:

```text
critical gaps += 1
active gap is created
```

---

# 10. Important Naming Issue in Current Code

Inside `evaluate_controls()` the code currently does:

```python
fw_total_dps += 1
fw_implemented_dps += 1 if is_implemented else 0
```

This happens **once per control**.

Therefore:

```text
fw_total_dps
```

is currently effectively:

```text
number of evaluated controls
```

not:

```text
actual number of deployment points
```

Example:

```text
Control A -> 5 DPs
Control B -> 3 DPs
Control C -> 2 DPs
```

Expected actual DP count:

```text
5 + 3 + 2 = 10
```

But `evaluate_controls()` currently produces:

```text
fw_total_dps = 3
```

because there are 3 controls.

This directly affects:

- framework health
- overall protection
- overall deploymentPoints statistic

So when reading the current code, treat these values as **control-level evaluation counts**, even though the variable names contain `dps`.

---

# 11. Framework Health Calculation

Function:

```python
calculate_fw_health_and_trend()
```

Current formula:

```text
Framework Health =
    implemented_count / total_count * 100
```

Example:

```text
Total evaluated controls = 50
Implemented controls = 40

Health = 40 / 50 * 100
       = 80%
```

The value is rounded.

So:

```text
frameworkHealth = 80
```

---

# 12. Framework Trend Calculation

The code also gets the previous implementation count from historical gap analysis.

Previous gap analysis is selected for the same deployment framework where:

```text
historical.createdAt < current.createdAt
```

Then previous implementation counts are calculated using the same implementation-status logic.

Current health:

```text
current_health =
    current_implemented / current_total * 100
```

Previous health:

```text
previous_health =
    previous_implemented / current_total * 100
```

Trend:

```text
trend = current_health - previous_health
```

The API returns the absolute value:

```text
trend = abs(trend)
```

And:

```text
trendUp = trend >= 0
```

Example:

```text
Current = 85
Previous = 80

trend = 5
trendUp = true
```

---

# 13. Overall Protection Calculation

Used by:

```text
GET /analytics
GET /overall-protection
```

The router gets:

```text
implemented_dps_overall
total_dps_overall
```

Then:

```python
overall_protection = round(
    implemented_dps_overall / total_dps_overall * 100
)
```

If total is zero:

```text
overallProtection = 0
```

### Example

Suppose:

```text
Framework 1 -> 40 evaluated, 35 implemented
Framework 2 -> 20 evaluated, 15 implemented
```

Overall:

```text
total = 40 + 20 = 60
implemented = 35 + 15 = 50

overallProtection =
    50 / 60 * 100
    = 83.33
    = 83
```

Again, because of the current `evaluate_controls()` logic, these counts are control-level counts.

---

# 14. Analytics API

## Endpoint

```text
GET /analytics
```

## Purpose

This API provides the main dashboard cards and charts.

The router loads:

```text
DeploymentFramework
PackageGapAnalysis
DeploymentPackageMerge
FrameworkAssignment
EvidenceOutput
Historical PackageGapAnalysis
```

Then it calls:

```python
process_gap_analyses(...)
```

The response is:

```json
{
  "overallProtection": 85,
  "criticalGaps": 12,
  "controlPassing": "45/50",
  "extraControls": 5,
  "frameworkHealth": [],
  "activeGaps": [],
  "liveAuditStreams": [],
  "deploymentPoints": [],
  "aiInsights": []
}
```

---

## 14.1 `overallProtection`

Source:

```text
process_gap_analyses()
    |
    +-- implemented_dps_overall
    +-- total_dps_overall
```

Formula:

```text
implemented_dps_overall
----------------------- × 100
total_dps_overall
```

---

## 14.2 `criticalGaps`

Source:

```text
process_gap_analyses()
    |
    +-- fw_critical_gaps
```

For every control where:

```text
is_implemented = false
```

the critical gap count increases by 1.

So:

```text
criticalGaps =
    number of controls without any implemented result
```

---

## 14.3 `controlPassing`

Source:

```text
passing_controls_overall
total_controls_overall
```

Response:

```text
"{passing_controls_overall}/{total_controls_overall}"
```

Example:

```text
45/50
```

---

## 14.4 `extraControls`

A control is considered extra when its customization source is:

```text
custom
```

The code checks the FrameworkAssignment file version and its AI extraction.

Then:

```text
extraControls += 1
```

for each custom control.

---

## 14.5 `frameworkHealth`

Each framework gets:

```text
id
name
version
readiness
weight_score
trend
trendUp
```

`readiness` is the framework health percentage.

---

## 14.6 `activeGaps`

For every non-implemented control an active gap object is created.

Example:

```json
{
  "id": "A.5.1",
  "framework": "ISO 27001",
  "control": "Policies for Information Security",
  "instances": 3,
  "failing": 100,
  "severity": "High"
}
```

---

## 14.7 `deploymentPoints`

This field is calculated differently from `process_gap_analyses()`.

Function:

```python
process_deployment_points()
```

It reads:

```text
DeploymentPackageMerge.controls.controls_data
```

and counts actual deployment points:

```python
dp_count += len(control["deployment_points"])
```

So this calculation is a real DP count.

Example:

```text
Control A -> 3 DPs
Control B -> 2 DPs
Control C -> 5 DPs

deploymentPoints = 10
```

---

## 14.8 `liveAuditStreams`

Source:

```text
EvidenceOutput
```

The code processes evidence records and returns live audit stream data.

---

## 14.9 `aiInsights`

Source:

```text
EvidenceOutput
    |
    +-- llm_analysis
          |
          +-- recommendation
          +-- confidence
```

Priority is taken from confidence:

```text
High
Medium
Low
```

If confidence is not one of these, priority becomes:

```text
Low
```

---

# 15. Overall Protection API

## Endpoint

```text
GET /overall-protection
```

## Purpose

This API provides the **Overall Protection framework table**.

It first runs the same main calculation:

```text
process_gap_analyses()
```

Then:

```text
build_overall_protection_rows()
```

Then:

```text
filter_and_sort_rows()
```

Then pagination.

---

# 16. Overall Protection Table Columns

The table rows contain:

| Response Field | Meaning | Calculation |
|---|---|---|
| `id` | Deployment Framework ID | `DeploymentFramework.id` |
| `version` | Framework version | `DeploymentFramework.frameworkVersion` |
| `framework` | Framework name | `DeploymentFramework.frameworkName` |
| `weight` | Framework contribution weight | Dynamic weight calculation |
| `rawScore` | Framework readiness | Framework health |
| `contribution` | Weighted score contribution | `weight * rawScore / 100` |
| `trend` | Health change | Current health - previous health |
| `trendUp` | Trend direction | `trend >= 0` |
| `status` | Framework status | Based on readiness thresholds |

---

# 17. Framework Weight Calculation

Each framework has:

```text
weight_score
```

The total is:

```text
total_weight_score =
    sum(all framework weight_score)
```

If total weight score is greater than zero:

```text
framework weight =
    framework weight_score
    ---------------------- × 100
    total weight_score
```

The final framework receives the remaining percentage so that total weight becomes exactly:

```text
100
```

If there is no weight score:

```text
100
```

is distributed equally among frameworks.

---

# 18. Overall Protection `contribution`

Formula:

```text
contribution =
    weight × readiness / 100
```

Example:

```text
weight = 40
readiness = 80

contribution =
    40 × 80 / 100
    = 32
```

---

# 19. Overall Protection Status

Function:

```python
get_framework_status()
```

The current code uses configured compliance thresholds.

Logic:

```text
readiness < low threshold
    -> At Risk

readiness <= medium threshold
    -> Needs Attention

otherwise
    -> On Track
```

The exact threshold values come from application settings.

---

# 20. Overall Protection Stats

The API returns:

```json
{
  "score": 85,
  "trend": 2,
  "trendUp": true,
  "frameworksActive": 3,
  "controlsEvaluated": 50,
  "deploymentPoints": 150
}
```

### `score`

```text
overallProtection
```

### `trend`

```text
abs(currentProtection - previousProtection)
```

### `trendUp`

```text
currentProtection - previousProtection >= 0
```

### `frameworksActive`

```text
len(framework_health)
```

### `controlsEvaluated`

```text
total_controls_overall
```

### `deploymentPoints`

Current code uses:

```text
total_dps_overall
```

But remember:

> `total_dps_overall` is currently incremented once per control inside `evaluate_controls()`. Therefore this value is effectively the number of evaluated controls, not the real sum of deployment points.

---

# 21. Overall Protection Pagination

After filtering and sorting:

```python
start = (page - 1) * limit
end = start + limit
rows[start:end]
```

Example:

```text
page = 2
limit = 10

start = (2 - 1) * 10 = 10
end = 20

rows[10:20]
```

---

# 22. Critical Gaps API

## Endpoint

```text
GET /critical-gaps
```

## Purpose

Shows controls that are currently not implemented.

The API gets:

```text
active_gaps
```

from:

```python
process_gap_analyses()
```

Then:

```python
build_critical_gaps_response()
```

formats them for the table.

---

# 23. Critical Gaps Table

The response contains:

| Field | Source |
|---|---|
| `id` | Framework ID |
| `frameworkVersion` | Framework version |
| `frameworkName` | Framework name |
| `ctrlNo` | Control ID |
| `controlName` | Control name |
| `instances` | Required deployment points for the control |
| `failingPct` | Calculated failing percentage |
| `failingRaw` | Numeric failing percentage |
| `severity` | Severity calculated from failing percentage |

---

# 24. Critical Gap Failing Percentage

For an active gap:

```text
required DPs = req_dps
implemented DPs = impl_dps
```

Formula:

```text
failing percentage =
    (req_dps - impl_dps)
    -------------------- × 100
          req_dps
```

However, there is an important current behavior.

Inside `evaluate_controls()` a control is only put into the active gap list when:

```text
is_implemented == false
```

For an active gap:

```text
impl_dps = 0
```

Therefore the current active-gap calculation normally becomes:

```text
(req_dps - 0) / req_dps * 100
= 100%
```

So current active gaps generally show:

```text
failing = 100
```

when `req_dps > 0`.

---

# 25. Critical Gap Severity

Function:

```python
calculate_gap_severity()
```

Uses application settings.

Logic:

```text
if failing_percentage > high threshold
    -> High

else if failing_percentage > medium threshold
    -> Medium

else
    -> Low
```

The thresholds are calculated from:

```text
compliance_score_low
compliance_score_medium
```

Example concept:

```text
Very high failing % -> High
Medium failing %    -> Medium
Lower failing %     -> Low
```

---

# 26. Critical Gap Trend

For historical comparison, the code finds the previous gap analysis for the same deployment framework.

Current failing percentage is compared with previous failing percentage.

Logic:

```text
current failing > previous failing
    -> down

current failing < previous failing
    -> up

same
    -> flat
```

If previous data does not exist:

```text
flat
```

---

# 27. Critical Gaps Priority Stats

The response also returns:

```json
"stats": {
  "priorities": {
    "high": 1,
    "medium": 2,
    "low": 3
  }
}
```

The counters are created by checking every active gap:

```text
severity == High
severity == Medium
severity == Low
```

---

# 28. Critical Gaps Filtering and Sorting

Supported filters:

```text
search
severityFilter
sortBy
sortOrder
```

Search checks:

```text
ctrlNo
controlName
frameworkName
```

For:

```text
sortBy = failingPct
```

the code actually sorts by:

```text
failingRaw
```

because `failingPct` is a string such as:

```text
"100%"
```

---

# 29. Controls Passing API

## Endpoint

```text
GET /controls-passing
```

## Purpose

Provides the detailed controls table.

The API uses:

```python
build_controls_passing_response()
```

---

# 30. Controls Passing Data Flow

```text
latest package
      |
      +-- gapAnalysis
      +-- mergeDocument
      |
      v
expected controls
      +
actual implementation
      |
      v
_process_package_controls()
      |
      v
Controls Passing table
```

---

# 31. Controls Passing Table

Each row contains:

| Field | Meaning |
|---|---|
| `id` | Deployment Framework ID |
| `ctrlId` | Control ID |
| `control` | Control name |
| `frameworkVersion` | Framework version |
| `frameworkName` | Framework name |
| `section` | Control section |
| `instances` | Required DP count |
| `passRate` | Current pass rate |
| `status` | Passing / Failing |
| `lastRun` | Gap analysis creation time |

---

# 32. Controls Passing Status

The current `_process_package_controls()` uses:

```python
is_implemented = actual_implemented.get(ctrl_id, 0) > 0
```

If true:

```text
passRate = 100
status = Passing
```

Otherwise:

```text
passRate = 0
status = Failing
```

Therefore the current Controls Passing table is effectively:

```text
At least one implemented result
    -> 100% / Passing

No implemented result
    -> 0% / Failing
```

The `Warning` helper exists in the code, but this specific response builder currently does not use it.

---

# 33. Controls Passing Stats

The response calculates:

```text
passing
failing
warning
notEvaluated
passRate
failingOrEvidence
```

Overall pass rate:

```text
passing / total × 100
```

Example:

```text
passing = 45
total = 50

passRate = 45 / 50 × 100
         = 90%
```

Current `failingOrEvidence`:

```text
failing + warning
```

---

# 34. Controls Passing Search

Search is applied to:

```text
ctrlId
control
frameworkName
```

Status filter checks:

```text
Passing
Failing
```

Sorting uses the requested field and order.

Pagination uses:

```text
start = (page - 1) * limit
end = start + limit
```

---

# 35. Extra Controls API

## Endpoint

```text
GET /extra-controls
```

## Purpose

Shows organization-specific/custom controls.

The source of truth is the FrameworkAssignment AI extraction.

A control is marked extra when:

```text
control.customization.source == "custom"
```

---

# 36. Extra Controls Table

Each extra control contains:

| Field | Meaning |
|---|---|
| `id` | Deployment Framework ID |
| `ctrlId` | Control ID |
| `control` | Control name |
| `frameworkVersion` | Framework version |
| `frameworkName` | Framework name |
| `deploymentPoints` | Number of DPs configured for the control |

`deploymentPoints` is:

```text
len(control.deployment_points)
```

---

# 37. Extra Controls Search / Sorting

Search checks:

```text
ctrlId
control
frameworkName
```

Sorting uses:

```text
sortBy
sortOrder
```

Pagination:

```text
start = (page - 1) * limit
end = start + limit
```

---

# 38. Deployment Points API

## Endpoint

```text
GET /deployment-points
```

## Purpose

Provides detailed deployment point information for each framework.

Unlike the overall protection calculation, this API uses the actual deployment point list.

---

# 39. Deployment Points Calculation

Function:

```python
process_deployment_points_detailed()
```

For every latest package:

```text
mergeDocument.controls.controls_data
```

is used to build expected controls.

For every control:

```python
req_dps = len(control["deployment_points"])
```

Then:

```python
total_dps += req_dps
```

This is a real deployment-point count.

---

# 40. Deployment Point Control Percentage

For each control:

```python
impl_dps = actual_implemented.get(ctrl_id, 0)
```

Then:

```python
is_implemented = impl_dps > 0
```

Current percentage:

```text
implemented > 0 -> 100%
implemented = 0 -> 0%
```

Example:

```text
Control A
required DPs = 5
implemented DPs = 2

Current result:
100%
```

Again, this is not:

```text
2 / 5 * 100 = 40%
```

The current implementation only checks whether at least one implementation exists.

---

# 41. Deployment Points Response

Example structure:

```json
{
  "results": [
    {
      "id": "framework-id",
      "frameworkName": "ISO 27001",
      "frameworkVersion": "2022",
      "instances": 10,
      "controls": [
        {
          "name": "Control A",
          "pct": 100
        },
        {
          "name": "Control B",
          "pct": 0
        }
      ]
    }
  ],
  "totalInstances": 10
}
```

### `instances`

```text
sum of deployment_points across all controls
```

### `totalInstances`

```text
sum(instances of filtered frameworks)
```

---

# 42. Deployment Point Filters

Search:

```text
frameworkName
```

Framework filter:

```text
frameworkVersion
```

Pagination is applied after filtering.

---

# 43. Framework Details API

## Endpoint

```text
GET /framework-details/{deployment_framework_id}
```

This API is different from the other dashboard APIs.

It directly calls:

```python
get_auditor_framework_details_helper()
```

The helper loads:

```text
DeploymentFramework
latest package
PackageComparison
PackageGapAnalysis
FrameworkAssignment
```

---

# 44. Framework Details Data Flow

```text
DeploymentFramework
       |
       v
latest package
       |
       +-- comparison ID
       +-- gapAnalysis ID
       |
       v
PackageComparison + PackageGapAnalysis
       |
       v
FrameworkAssignment maps
       |
       +-- source
       +-- is_applicable
       |
       v
_calculate_auditor_metrics()
       |
       v
Framework Details response
```

---

# 45. Applicable Controls

FrameworkAssignment creates two maps:

```text
source_map
applicable_map
```

For every AI-extracted control:

```text
customization.source
customization.is_applicable
```

are read.

If:

```text
is_applicable = false
```

the control is skipped from the framework details calculation.

If the field is missing:

```text
is_applicable = true
```

is used.

---

# 46. Framework Details Comparison Score

The helper reads:

```text
PackageComparison.comparison["comparison_result"]
```

For every applicable control:

```text
comparison_score
```

is checked against:

```text
comp_threshold
```

If:

```text
comparison_score >= comp_threshold
```

then:

```text
compliant += 1
```

Otherwise:

```text
non_compliant += 1
```

Every evaluated control increases:

```text
subscribed += 1
```

---

# 47. Framework Details Controls

Response:

```json
"controls": {
  "subscribed": 93,
  "compliant": 50,
  "nonCompliant": 43,
  "notAssessed": 0
}
```

Current formulas:

```text
subscribed =
    number of applicable controls in comparison result

compliant =
    controls where comparison_score >= threshold

nonCompliant =
    controls where comparison_score < threshold

notAssessed =
    0
```

Important:

> The current implementation always returns `notAssessed = 0` for Framework Details.

---

# 48. Framework Details Coverage

Coverage is based on control source.

The code counts:

```text
source == "custom"
    -> custom_count

otherwise
    -> pre_count
```

Response:

```json
"coverage": {
  "total": 93,
  "breakdown": [
    {
      "name": "Pre controls",
      "value": 92
    },
    {
      "name": "Org. Specific",
      "value": 1
    }
  ]
}
```

Formula:

```text
coverage.total =
    pre_count + custom_count
```

---

# 49. Framework Details Compliance

Formula:

```text
compliance.total =
    compliant + nonCompliant
```

Breakdown:

```text
Compliant
Non-Compliant
Not Assessed
```

Current:

```text
Not Assessed = 0
```

---

# 50. Framework Details Gap Analysis Chart

The helper creates:

```text
auditDashboard.gapAnalysis[]
```

For every control:

If a `gap_score` exists:

```text
value = round(gap_score * 10)
```

Otherwise:

```text
value = round((1 - comparison_score) * 10)
```

Example:

```text
gap_score = 0.8

value = 0.8 * 10
      = 8
```

---

# 51. Framework Details Non-Compliant Controls

For every control where:

```text
comparison_score < comp_threshold
```

a row is created.

Fields:

```text
sl
ctrlNo
name
instances
failing
```

`instances`:

```text
len(deployment_framework_deployment_points)
```

`failing`:

```text
(1 - comparison_score) * 100
```

Example:

```text
comparison_score = 0.20

failing =
    (1 - 0.20) * 100
    = 80%
```

---

# 52. Main Calculation Difference You Should Remember

There are **two different DP-related calculations** in the current code.

## A. Auditor Analytics / Overall Protection

Uses:

```python
evaluate_controls()
```

Current behavior:

```text
1 control = 1 counted evaluation unit
```

So:

```text
total_dps_overall
implemented_dps_overall
```

are effectively control counts.

---

## B. Deployment Points API

Uses:

```python
len(control["deployment_points"])
```

So this is a real deployment-point count.

Example:

```text
Control A -> 5 DPs
Control B -> 3 DPs

Real DP count = 8
```

Deployment Points API:

```text
instances = 8
```

But Overall Protection:

```text
total_dps_overall = 2
```

because there are 2 controls.

This difference is important when comparing dashboard numbers.

---

# 53. Another Important Difference: Passing Logic

There are two concepts.

## Auditor Dashboard / Controls Passing

Current logic:

```text
implemented count > 0
    -> Passing
```

Example:

```text
5 required DPs
1 implemented DP

Result:
Passing
100%
```

## Framework Details

Uses:

```text
comparison_score >= compliance_score_threshold
```

So Framework Details uses the comparison score, not the same `implemented > 0` rule.

---

# 54. Database Sample Reference

The provided sample database contains deployment framework packages with:

```text
packageVersion
documents[]
fileVersion
fileHash
originalFileName
comparison
gapAnalysis
mergeDocument
```

For example, package records contain:

```text
packageVersion = 1.0.0
fileVersion = 1.0.0
gapAnalysis = <ID>
mergeDocument = <ID>
```

The sample also shows later packages with different package versions such as:

```text
2.0.0
3.0.0
```

This confirms that the Auditor Dashboard reads the package references from `DeploymentFramework.packages`.

---

# 55. Common Helper Functions

## `get_nested()`

Safely reads a value from either:

```text
dict
```

or:

```text
object attribute
```

Example:

```python
get_nested(pkg, "gapAnalysis")
```

---

## `filter_and_sort_rows()`

Used for Overall Protection.

Search:

```text
framework
version
```

Status filter:

```text
status
```

Sorting:

```text
sortBy
sortOrder
```

---

## Pagination

Common formula:

```text
start = (page - 1) * limit
end = start + limit
```

The page and limit are also clamped using:

```text
clamp_page()
clamp_limit()
```

---

# 56. API Summary Table

| API | Main Source | Main Calculation | Used For |
|---|---|---|---|
| `/analytics` | Gap Analysis + Merge + Evidence | Overall dashboard metrics | Dashboard cards/charts |
| `/overall-protection` | Gap Analysis + Merge | Framework health + weight | Overall Protection table |
| `/critical-gaps` | Gap Analysis + Merge | Non-implemented controls | Critical Gaps table |
| `/controls-passing` | Gap Analysis + Merge | Implemented > 0 | Controls table |
| `/extra-controls` | Framework Assignment + Merge | `source == custom` | Extra Controls table |
| `/deployment-points` | Merge + Gap Analysis | `len(deployment_points)` | Deployment Point table |
| `/framework-details/{id}` | Comparison + Gap Analysis + Assignment | Comparison score | Framework detail page |

---

# 57. Quick Example

Suppose a framework has:

```text
3 controls

Control A -> 5 DPs -> 2 implemented
Control B -> 3 DPs -> 0 implemented
Control C -> 2 DPs -> 1 implemented
```

## Expected real DPs

```text
5 + 3 + 2 = 10
```

## Current `evaluate_controls()` count

```text
3 controls = 3 evaluation units
```

## Passing controls

```text
A -> Passing
B -> Failing
C -> Passing

Passing = 2
Total = 3

controlPassing = "2/3"
```

## Current framework health

```text
implemented evaluation units = 2
total evaluation units = 3

health = 2 / 3 * 100
      = 67%
```

## Critical gaps

Only Control B is not implemented:

```text
criticalGaps = 1
```

For Control B:

```text
required DPs = 3
implemented DPs used by active-gap logic = 0

failing =
    (3 - 0) / 3 * 100
    = 100%
```

## Deployment Points API

Real count:

```text
5 + 3 + 2 = 10
```

So Deployment Points API returns:

```text
instances = 10
```

This example shows why the Overall Protection and Deployment Points APIs can show different DP totals.

---

# 58. Final Mental Model

If you need to understand the code quickly, remember this:

```text
DeploymentFramework
    |
    +-- select latest package
    |
    +-- PackageGapAnalysis
    |       |
    |       +-- implementation_status
    |
    +-- DeploymentPackageMerge
    |       |
    |       +-- controls
    |       +-- deployment_points
    |
    +-- FrameworkAssignment
            |
            +-- custom / standard
            +-- applicable / not applicable
```

Then:

```text
Gap Analysis
    +
Merge Document
    |
    v
Control Evaluation
    |
    +-- Passing Controls
    +-- Critical Gaps
    +-- Framework Health
    +-- Overall Protection
```

And separately:

```text
Merge Document
    +
Deployment Points
    |
    v
Deployment Points API
```

And:

```text
Package Comparison
    +
Framework Assignment
    |
    v
Framework Details API
```

---

# 59. Important Current-Code Notes

1. **`evaluate_controls()` counts one unit per control**, even though the variable is called `fw_total_dps`.

2. **A control is Passing if at least one implementation result exists.** It does not require every configured DP to be implemented.

3. **Controls Passing currently returns only 100% or 0% pass rate.**

4. **Active critical gaps normally become 100% failing** when a control has at least one required DP, because non-implemented controls pass `impl_dps = 0`.

5. **Deployment Points API counts actual deployment points** using `len(deployment_points)`.

6. **Framework Details uses comparison score**, which is a different calculation from the Auditor Dashboard control implementation logic.

7. **Framework Details currently returns `notAssessed = 0`.**

8. **Extra controls are identified from `customization.source == "custom"`.**

9. **Historical gap analysis is used for trend calculations.**

10. **Pagination happens after filtering and sorting.**

11. **The exact compliance thresholds come from application settings**, not hard-coded values in these helper functions.

---

# 60. Code-to-Response Reference

Use this section when debugging a response field.

| Response Field | Code Function |
|---|---|
| `overallProtection` | `process_gap_analyses()` + router formula |
| `criticalGaps` | `process_gap_analyses()` |
| `controlPassing` | `process_gap_analyses()` |
| `extraControls` | `process_gap_analyses()` |
| `frameworkHealth` | `process_gap_analyses()` |
| `activeGaps` | `process_gap_analyses()` |
| `liveAuditStreams` | `process_live_streams()` |
| `aiInsights` | `process_ai_insights()` |
| Overall Protection rows | `build_overall_protection_rows()` |
| Critical Gaps rows | `build_critical_gaps_response()` |
| Controls Passing rows | `build_controls_passing_response()` |
| Extra Controls rows | `build_extra_controls_response()` |
| Deployment Point summary | `process_deployment_points()` |
| Deployment Point detailed rows | `process_deployment_points_detailed()` |
| Framework Details | `get_auditor_framework_details_helper()` |

---

# 61. One-Line Summary

```text
Latest Package
    -> Merge Document gives expected controls/DPs
    -> Gap Analysis gives implementation status
    -> Framework Assignment gives custom/applicable information
    -> Helper functions calculate dashboard metrics
    -> API-specific builders create the final table/response
```

This is the current functionality implemented in the provided `auditor.py` and `helpers.py`.
