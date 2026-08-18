# Auditor Dashboard API - Data Calculation Report

This report explains exactly how the data in your JSON response is calculated and where each specific value comes from in the database, based on the code in `auditor.py`.

## Core Logic (The Foundation)
Before calculating any metrics, the API first identifies what data is "Live":
1. It fetches all `DeploymentFramework` records for the current `tenant`.
2. It loops through their `packages` array.
3. It only selects packages where `"status": "live"` and `"type": "deployed"`.
4. From these live packages, it extracts the unique IDs for their associated **`gapAnalysis`** and **`mergeDocument`**.

Everything calculated below is based **only** on these live packages.

---

## 1. Overall Protection, Control Passing & Critical Gaps
**Source File:** `auditor.py` -> `_process_gap_analyses()`
**Database Table:** `PackageGapAnalysis` AND `DeploymentPackageMerge`

### Calculation:
The API uses a strict double-verification method to ensure no gaps are hidden:
1. It reads the `DeploymentPackageMerge` (the framework configuration) to find the exact list of expected controls and exactly how many deployment points are required for each control to pass.
2. It then reads the `PackageGapAnalysis` and counts how many of those deployment points are actually marked as `"implemented"`, `"compliant"`, or `"passed"`.
- **`total_controls_overall`** (e.g., `93`): The exact count of controls required by the framework configuration (`mergeDocument`).
- **`passing_controls_overall`** (e.g., `0`): The count of controls where the number of `"implemented"` deployment points is **greater than or equal to** the number of required deployment points. If even one deployment point is not implemented, the control fails.
- **`criticalGaps`** (e.g., `93`): The count of controls that fail this strict check.

### JSON Output Formatting:
- **`controlPassing`**: A simple text join: `"{passing_controls_overall}/{total_controls_overall}"` (Result: `"0/93"`).
- **`overallProtection`**: A percentage calculation representing the total health across all frameworks at a granular Deployment Point level: `(total_implemented_dps_across_all_frameworks / total_required_dps_across_all_frameworks) * 100`, rounded to the nearest whole number.

---

## 2. Extra Controls (Above Standards)
**Source File:** `auditor.py` -> `_process_gap_analyses()`
**Database Table:** `DeploymentPackageMerge`

### Calculation:
The API parses the `mergeDocument` linked to the live packages to find controls that are marked as organization-specific.
- **`extraControls`**: It iterates through the expected controls in the framework configuration and checks the `customization` dictionary on each control. If `customization["source"] == "custom"`, the counter is incremented by 1.

---

## 3. Framework Health
**Source File:** `auditor.py` -> `_process_gap_analyses()`
**Database Table:** `PackageGapAnalysis` AND `DeploymentPackageMerge`

### Calculation:
This calculates the health of the framework at a granular Deployment Point level (rather than strict control level). 
- **`readiness`** (e.g., `45`): Calculates the percentage of total implemented deployment points out of all required deployment points for the specific framework: `(fw_implemented_dps / fw_total_dps) * 100`, rounded to the nearest whole number. This provides a fair health score even if few controls are fully passing.
- **`name` & `version`**: Extracted directly from the parent `DeploymentFramework` linked to this gap analysis.

---

## 4. Active Gaps
**Source File:** `auditor.py` -> `_process_gap_analyses()`
**Database Table:** `PackageGapAnalysis`

### Calculation:
Whenever a control fails the check above (its `implementation_status` is NOT "implemented"), it is added to the `activeGaps` list.
- **`id`**: Taken from `"assigned_framework_control_id"` (e.g., `"A.5.1"`).
- **`control`**: Taken from `"assigned_framework_control_name"`.
- **`description`**: Taken from `"assigned_framework_control_description"`.
- **`instances`**: The API groups the `deployment_gap_results` by `assigned_framework_control_id`. It counts how many deployment points map to this specific control.
- **`failing`**: It calculates the percentage by dividing the number of non-implemented instances by the total `instances` for that control.
- **`trend`**: Calculates whether the gap is improving or worsening by comparing the current failure percentage against the *previous* `PackageGapAnalysis` record for the same framework. (Returns `"up"`, `"down"`, or `"flat"`).
- **`lastNC`**: The `createdAt` timestamp of the `PackageGapAnalysis` record.

---

## 4. Live Audit Streams
**Source File:** `auditor.py` -> `_process_live_streams()`
**Database Table:** `EvidenceOutput` (Top 50 most recent records)

### Calculation:
The API fetches the 50 most recent `EvidenceOutput` rows and parses their highly nested `output` JSON block: `fileVersions[] -> data -> records[]`.
- It loops through the `records` array.
- **`status`**: It checks the `"compliance_status"` string inside the record.
  - If the string contains `"not compliant"`, status = `"fail"`.
  - If the string contains `"compliant"`, status = `"pass"`.
  - Otherwise, status defaults to `"warn"`.
- **`description`**: It extracts the `"deployment_point"` string from the record.
- **`timestamp`**: The `createdAt` timestamp of the `EvidenceOutput` record.

---

## 5. Deployment Points
**Source File:** `auditor.py` -> `_process_deployment_points()`
**Database Table:** `DeploymentPackageMerge` (Filtered by live `mergeDocument` IDs)

### Calculation:
The API extracts the `controls_data` array from the `controls` JSON column of the merge document.
- It iterates deeply into the JSON structure: `sections -> controls -> deployment_points`.
- **`count`** (e.g., `330`): It calculates the exact length (`len()`) of the `"deployment_points"` array attached to every control inside the merge document, and sums them all together.
- **`name` & `version`**: Extracted directly from the parent `DeploymentFramework` linked to this merge document.
