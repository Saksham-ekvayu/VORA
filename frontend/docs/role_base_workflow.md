# VORA Frontend Role & Workflow Report

This report defines the system roles, access privileges, and the current compliance workflow of the VORA platform based on the current implementation.

---

## 1. Compliance & Audit Workflow Sequence

The system operates in a sequential flow across roles to upload, assign, configure, and analyze compliance frameworks:

```mermaid
sequenceDiagram
  autonumber
  actor Admin
  actor Expert
  actor CustAdmin as Customer Admin
  actor Auditor

  Note over Admin, Expert: Phase 1: Framework Prep
  Expert->>Admin: Request Framework Category Access
  Admin->>Expert: Approve Category Access
  Expert->>Expert: Upload Industry Framework + Trigger AI Extraction
  Expert->>Expert: Manage Controls (CRUD) & Review
  Expert->>Expert: Finalize & Freeze Industry Framework

  Note over Admin, CustAdmin: Phase 2: Customer Assignment
  Admin->>Admin: Assign Finalized Industry Framework to Customer
  CustAdmin->>CustAdmin: View Assigned Frameworks (Read-Only)

  Note over Auditor: Phase 3: Setup & Analysis
  Auditor->>Auditor: Manage Assigned Framework (Add Org-Specific Controls)
  Auditor->>Auditor: Mark Controls Applicable / Not Applicable
  Auditor->>Auditor: Finalize Assigned Framework
  Auditor->>Auditor: Upload Deployment Doc Packages + Run AI Extraction
  Auditor->>Auditor: Manage Major/Minor Patches
  Auditor->>Auditor: Run Control Comparison & DP Gap Analysis
```

---

## 2. Role and Functionality Matrix

The following matrix maps each role to its exact capabilities in the system:

| Role                | Key Capabilities & Functionalities                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| :------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **System Admin**    | • **User & Customer Management:** Onboard users and organizations.<br>• **Framework Category Management:** CRUD operations on categories.<br>• **Category Access Controls:** Approve, reject, or revoke framework category access for experts.<br>• **Framework Assignment:** Assign finalized industry frameworks to customers; revoke assignments.                                                                                                                                                                                                                                                                                                                                                   |
| **Expert**          | • **Access Request:** Request access to specific framework categories.<br>• **Industry Framework Upload:** Upload new industry frameworks.<br>• **AI Extraction:** Execute AI extraction on uploaded frameworks.<br>• **Control CRUD:** Create, read, update, and delete controls on industry frameworks.<br>• **Finalization:** Review, finalize, and freeze industry frameworks.                                                                                                                                                                                                                                                                                                                     |
| **Customer Admin**  | • **Read-Only View:** View assigned frameworks belonging only to their customer organization.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **Auditor**         | • **Assigned Framework Management:** Manage, review, and finalize assigned frameworks.<br>• **Organization Customization:** Add organization-specific controls to the assigned framework.<br>• **Applicability Controls:** Mark controls as applicable or not applicable.<br>• **Deployment Management:** Upload deployment framework document packages.<br>• **Patch Management:** Perform minor patches (carry documents forward) or major patches (clean slate) on packages.<br>• **Document AI Extraction:** Run AI extraction on uploaded document packages.<br>• **Analysis Execution:** Run comparison of controls and gap analysis of deployment points (DPs) against the finalized framework. |
| **User**            | • (Member of the Customer organization with basic access as defined by customer scope).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **Internal Expert** | • (Customer organization role aligned with audit/review operations).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
