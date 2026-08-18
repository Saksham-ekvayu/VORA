# Auditor Dashboard: Database Analysis Report

This report analyzes whether the existing VORA database schema supports the data requirements for the `AuditorDashboard.jsx` frontend component.

## Overview
The VORA database architecture heavily utilizes PostgreSQL `JSONB` columns, meaning much of the granular compliance data is stored flexibly within JSON objects rather than strictly typed tables. Because of this, **almost all of the data needed for the Auditor Dashboard can be extracted from the current schema.**

---

## 🟢 Fully Supported (Data is available to aggregate)

### 1. Control Passing & Overall Protection
- **Required Data:** Overall compliance health percentage and the ratio of passing controls vs total controls.
- **Relevant Tables:** `deployment_frameworks`, `package_gap_analyses`, `deployment_package_merges`, `evidence_output`.
- **Extraction Method:** You must filter the `deployment_frameworks` table for packages where `status` is `"live"` and `type` is `"deploy"`. From those specific live deployment packages, you can calculate the total vs passing controls by aggregating their associated `gapAnalysis` data or cross-referencing `evidence_output`.

### 2. Framework Health
- **Required Data:** A list of compliance frameworks (like ISO-27001, NIST-CSF) paired with a percentage progress bar showing their "readiness" score.
- **Relevant Tables:** `deployment_frameworks`, `package_gap_analyses`.
- **Extraction Method:** You must calculate readiness specifically from `deployment_frameworks` packages that have `status` set to `"live"` and `type` set to `"deploy"`. The framework's overall health score will be derived from the control gap analyses tied to those live deployment packages.

### 3. Live Audit Streams
- **Required Data:** A scrolling feed of real-time audit checks (e.g., "Password Complexity Check • AWS IAM") showing if they Passed, Warned, or Failed.
- **Relevant Tables:** `evidence_output`.
- **Extraction Method:** You can simply query the `evidence_output` table, ordered by `createdAt` descending, to get a live feed of the most recent automated checks from the various deployment points.

### 4. Active Gaps
- **Required Data:** A table of currently failing controls, including the framework, control ID, description, number of failing instances, percentage failing, and the date of the last Non-Compliance (NC).
- **Relevant Tables:** `deployment_frameworks`, `package_gap_analyses`, `deployment_package_merges`.
- **Extraction Method:** You must first filter the `deployment_frameworks` table for packages where `status` is `"live"` and `type` is `"deploy"`. Then, the `gapAnalysis` JSON from those specific packages will contain the failing controls, which can be aggregated to count instances, calculate failing percentages, and find the last NC date.

### 5. Deployment Points
- **Required Data:** A list showing how many deployment/monitoring points are configured per framework.
- **Relevant Tables:** `deployment_frameworks`, `deployment_package_merges`.
- **Extraction Method:** You can join `deployment_frameworks` (filtered for live/deploy packages) with `deployment_package_merges` to count the deployment points associated with the live framework configurations.

---

## 🟡 Supported, but depends on JSON Structure

### 1. AI Insights
- **Required Data:** A list of actionable text recommendations tagged with a Priority level (High, Medium, Low) to help bridge gaps.
- **Relevant Tables:** `document_extractions` (`aiExtraction` JSON), `package_gap_analyses`, and `agent_prompts`.
- **Extraction Method:** As long as the AI generation backend saves its recommendations into the `gapAnalysis` JSON or `aiExtraction`, you can surface these insights.

### 2. Extra Controls (Above Standards)
- **Required Data:** The number of controls implemented that go "Above Standards".
- **Extraction Method:** Can be calculated if the JSON schema inside `package_gap_analyses` clearly flags custom/additional controls versus baseline controls.

---

## 🔴 Missing / Needs Verification

### 1. Risk by Status (Accepted, Reduced, Transferred, Mitigated)
- **Required Data:** A table that categorizes risks and breaks down exactly how many High, Medium, and Low risks fall into each bucket.
- **Current Status:** **Missing.** There is no dedicated `risks` or `risk_exceptions` table in the SQL schema.
- **Workaround:** Unless these risk decisions (e.g., "We accept the risk for control AC-2.1") are specifically stored inside the `assignment` JSONB field of the `framework_assignments` table, you might need to create a new table or standardize the JSON structure to track user-defined risk decisions.

---

## Conclusion
You are in a great position. You won't need major database overhauls to build this dashboard; you will mostly just need to write the backend API queries to aggregate the data out of the `JSONB` columns!
