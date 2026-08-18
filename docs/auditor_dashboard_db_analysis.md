# Auditor Dashboard: Database Analysis Report

This report analyzes whether the existing VORA database schema supports the data requirements for the `AuditorDashboard.jsx` frontend component.

## Overview
The VORA database architecture heavily utilizes PostgreSQL `JSONB` columns, meaning much of the granular compliance data is stored flexibly within JSON objects rather than strictly typed tables. Because of this, **almost all of the data needed for the Auditor Dashboard can be extracted from the current schema.**

---

## 🟢 Fully Implemented [DONE]

### 1. Control Passing & Overall Protection [DONE]
- **Required Data:** Overall compliance health percentage and the ratio of passing controls vs total controls.
- **Relevant Tables:** `deployment_frameworks`, `package_gap_analyses`, `deployment_package_merges`
- **Implementation:** The API dynamically filters `deployment_frameworks` for `"live"` / `"deployed"` packages. It calculates `overallProtection` by measuring total implemented deployment points vs total required deployment points globally. `controlPassing` is calculated using strict logic where every single required deployment point for a control must be fully implemented for the control to pass.

### 2. Framework Health [DONE]
- **Required Data:** A list of compliance frameworks paired with a percentage progress bar showing their "readiness" score.
- **Relevant Tables:** `deployment_frameworks`, `package_gap_analyses`, `deployment_package_merges`
- **Implementation**: The API calculates this by aggregating the exact count of implemented deployment points out of all required deployment points for each specific framework. This gives a granular health score (`readiness`) for every active framework.

### 3. Live Audit Streams [DONE]
- **Required Data:** A feed of real-time audit checks showing if they Passed, Warned, or Failed, along with reason, confidence, and `dp_id`.
- **Relevant Tables:** `evidence_output`
- **Implementation:** The API queries the 50 most recent `evidence_output` records, drills down into their `fileVersions` -> `data` -> `records` JSON structure using a Python generator, and extracts the deployment point descriptions, status (pass/fail), LLM analysis reasons, confidence scores, and specific `dp_id`s.

### 4. Active Gaps [DONE]
- **Required Data:** A table of currently failing controls, including the framework, control ID, description, number of failing instances, percentage failing, and the trend.
- **Relevant Tables:** `package_gap_analyses`, `deployment_package_merges`
- **Implementation:** The API isolates any control that fails to have 100% of its required deployment points implemented. It dynamically compares the current gap analysis with historical gap analyses to calculate the failure `trend` (up/down/flat) and returns the percentage of failing instances per control.

### 5. Deployment Points [DONE]
- **Required Data:** A list showing how many deployment/monitoring points are configured per framework.
- **Relevant Tables:** `deployment_package_merges`
- **Implementation:** The API iterates deeply into the `controls_data` structure of each active `mergeDocument` (sections -> controls -> deployment_points) and aggregates the total count of required deployment points configured for the framework.

### 6. Extra Controls (Above Standards) [DONE]
- **Required Data:** The number of controls implemented that go "Above Standards".
- **Relevant Tables:** `framework_assignments`
- **Implementation:** The API specifically queries the `framework_assignments` table associated with the live packages. It traverses into `fileVersions[-1]["aiExtraction"]` to identify controls where `customization.source == "custom"`, counting them towards the `extraControls` metric.

---

## 🟡 Pending / Needs Implementation [PENDING]

### 1. AI Insights [PENDING]
- **Required Data:** A list of actionable text recommendations tagged with a Priority level (High, Medium, Low) to help bridge gaps.
- **Relevant Tables:** `document_extractions` (`aiExtraction` JSON), `package_gap_analyses`, and `agent_prompts`.
- **Current Status:** Not yet included in the dashboard API payload. The implementation will require extracting these recommendations from the AI generation backend's saved outputs in the `gapAnalysis` JSON.

---

## 🔴 Missing / Needs Database Changes [MISSING]

### 1. Risk by Status (Accepted, Reduced, Transferred, Mitigated) [MISSING]
- **Required Data:** A table that categorizes risks and breaks down exactly how many High, Medium, and Low risks fall into each bucket.
- **Current Status:** There is no dedicated `risks` or `risk_exceptions` table in the SQL schema.
- **Workaround:** Unless these risk decisions (e.g., "We accept the risk for control AC-2.1") are specifically stored inside the `assignment` JSONB field of the `framework_assignments` table, a new table or standardized JSON structure is needed to track user-defined risk decisions.

---

## Conclusion
The core metrics of the Auditor Dashboard have been successfully implemented! All primary metrics (Overall Protection, Active Gaps, Framework Health, Extra Controls, and Live Audit Streams) are fully driven by live database data using the strict deployment point calculations.
