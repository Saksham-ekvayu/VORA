# Auditor Dashboard API Functionality & Calculations

This document details the functionality, data sources, and internal calculations for all the APIs used in the Auditor Dashboard (`dashboard-service/app/routers/auditor.py`). It also maps the exact fields returned in the API responses to their respective calculation logic.

---

## 1. Analytics Overview (`GET /analytics`)
**Purpose**: Serves as the main data provider for the high-level Auditor Dashboard summary cards and charts.
**Data Sources**: `DeploymentFramework`, `PackageGapAnalysis` (current & historical), `DeploymentPackageMerge`, `FrameworkAssignment`, `EvidenceOutput`.

**API Response Example:**
```json
{
  "success": true,
  "message": "Auditor dashboard analytics retrieved successfully",
  "data": {
    "overallProtection": 85,
    "criticalGaps": 12,
    "controlPassing": "45/50",
    "extraControls": 5,
    "frameworkHealth": [
      {
        "name": "ISO 27001",
        "version": "2022",
        "health": 80,
        "trendUp": true,
        "trend": 5
      }
    ],
    "activeGaps": [ ... ],
    "liveAuditStreams": [ ... ],
    "deploymentPoints": [
      {
        "name": "ISO 27001",
        "version": "2022",
        "count": 150
      }
    ],
    "aiInsights": [
      {
        "text": "Enable MFA across all users.",
        "priority": "High"
      }
    ]
  }
}
```

**Key Metrics & Calculations mapping**:
- `data.overallProtection`: `(Total Implemented DPs / Total Required DPs) * 100` across all frameworks.
- `data.controlPassing`: String format `"{Passing} / {Total}"`. A control is considered "Passing" if its pass rate `(Implemented DPs / Required DPs)` is $\ge$ `compliance_score_threshold`.
- `data.extraControls`: Count of controls marked as "Extra" (e.g., custom controls via Framework Assignments).
- `data.frameworkHealth[].health`: Average pass rate of all controls within that specific framework.
- `data.activeGaps`: Array of failing controls. Failing percentage is `100 - Pass Rate`.
- `data.deploymentPoints[].count`: Total configured deployment points for that framework extracted from `DeploymentPackageMerge`.

---

## 2. Overall Protection Table (`GET /overall-protection`)
**Purpose**: Provides paginated data for the "Overall Protection" table, showing protection scores per framework.

**API Response Example:**
```json
{
  "success": true,
  "data": {
    "frameworks": [
      {
        "name": "ISO 27001",
        "version": "2022",
        "health": 85,
        "status": "Healthy",
        "trendUp": true,
        "trend": 2,
        "lastRun": "2026-08-20T10:00:00Z"
      }
    ],
    "stats": {
      "score": 85,
      "trend": 2,
      "trendUp": true,
      "frameworksActive": 3,
      "controlsEvaluated": 50,
      "deploymentPoints": 150
    }
  },
  "meta": { "page": 1, "limit": 10, "totalPages": 1, "totalItems": 1 }
}
```

**Calculations Mapping**:
- `data.stats.score`: Calculates `overall_protection` using `(Implemented DPs / Required DPs) * 100` for the latest `PackageGapAnalysis`.
- `data.stats.trend`: Absolute difference between `overall_protection` and `overall_prev_protection` (from historical gap analysis).
- `data.stats.trendUp`: `true` if current score $\ge$ previous score.
- `data.frameworks[].health`: Individual framework's average control pass rate.
- `data.frameworks[].status`: Assigned based on health (e.g., "Healthy" if health $\ge$ threshold).

---

## 3. Critical Gaps (`GET /critical-gaps`)
**Purpose**: Lists specific controls across all frameworks that are falling short of compliance.

**API Response Example:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": "fw-123",
        "frameworkVersion": "2022",
        "frameworkName": "ISO 27001",
        "ctrlNo": "A.5.1",
        "controlName": "Policies for Information Security",
        "instances": 3,
        "failingPct": "20%",
        "failingRaw": 20,
        "severity": "High"
      }
    ],
    "stats": {
      "priorities": { "high": 1, "medium": 0, "low": 0 }
    }
  }
}
```

**Calculations Mapping**:
- `failingRaw` & `failingPct`: `100 - Pass Rate`. The control is a gap if `Pass Rate < compliance_score_threshold`.
- `instances`: The `required_dps` for that specific control from `DeploymentPackageMerge`.
- `severity`: Defaults to "Low" but overridden by LLM insights or hardcoded thresholds during `PackageGapAnalysis` evaluation.

---

## 4. Controls Passing (`GET /controls-passing`)
**Purpose**: Detailed paginated table view of all controls evaluated, their pass rates, and status.

**API Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "id": "fw-123",
      "ctrlId": "A.5.1",
      "control": "Policies for Information Security",
      "frameworkVersion": "2022",
      "frameworkName": "ISO 27001",
      "section": "Organizational Controls",
      "instances": 5,
      "passRate": 100,
      "status": "Passing",
      "lastRun": "2026-08-20T10:00:00Z"
    }
  ]
}
```

**Calculations Mapping**:
- `passRate`: `(min(Implemented DPs, Required DPs) / Required DPs) * 100`.
- `status`:
  - `"Not Evaluated"`: If `Required DPs == 0`.
  - `"Passing"`: If `Pass Rate >= compliance_score_threshold`.
  - `"Failing"`: If `Pass Rate < compliance_score_threshold`.
- `instances`: Total required deployment points.

---

## 5. Extra Controls (`GET /extra-controls`)
**Purpose**: Shows controls added by the organization (custom controls) or that fall outside standard predefined frameworks.

**API Response Example:**
```json
{
  "success": true,
  "data": [
    {
      "id": "fw-123",
      "ctrlId": "CUST.1",
      "control": "Custom Firewall Rule",
      "frameworkVersion": "2022",
      "frameworkName": "ISO 27001",
      "deploymentPoints": 2
    }
  ]
}
```

**Calculations Mapping**:
- `deploymentPoints`: Required DPs mapped.
- Identification: Filtered from `FrameworkAssignment.fileVersions.aiExtraction.controls` where `customization.source == "custom"`.

---

## 6. Framework Details (`GET /framework-details/{id}`)
**Purpose**: Delivers deep dive metrics for a single specific Deployment Framework.

**API Response Example:**
```json
{
  "success": true,
  "data": {
    "id": "1111-2222-3333-4444",
    "frameworkName": "ISO 27001",
    "frameworkVersion": "2022",
    "controls": {
      "subscribed": 93,
      "compliant": 50,
      "nonCompliant": 43,
      "notAssessed": 0
    },
    "coverage": {
      "total": 93,
      "breakdown": [
        {"name": "Pre controls", "value": 92},
        {"name": "Org. Specific", "value": 1}
      ]
    },
    "compliance": {
      "total": 93,
      "breakdown": [
        {"name": "Compliant", "value": 50},
        {"name": "Non-Compliant", "value": 43},
        {"name": "Not Assessed", "value": 0}
      ]
    },
    "auditDashboard": {
      "gapAnalysis": [
        {"id": "A.5.1", "name": "Policies for Info Sec", "value": 8}
      ]
    },
    "nonCompliantControls": [
      {
        "sl": 1,
        "ctrlNo": "A.5.1",
        "name": "Policies for Info Sec",
        "instances": 3,
        "failing": "80%"
      }
    ],
    "notAssessed": []
  }
}
```

**Calculations Mapping**:
- **Filtering (`is_applicable`)**: Reads `is_applicable` flag from `FrameworkAssignment`. Any control where this is `False` is ignored and excluded from all metrics.
- `controls.subscribed`: Incremented for every applicable control found in the comparison result.
- `compliance.breakdown.Compliant` (`compliant`): Incremented if `comparison_score >= compliance_score_threshold`.
- `compliance.breakdown.Non-Compliant` (`nonCompliant`): Incremented if `comparison_score < compliance_score_threshold`.
- `coverage.breakdown.Pre controls` (`pre_count`): Incremented if the control's customization source in `FrameworkAssignment` is **not** `"custom"`.
- `coverage.breakdown.Org. Specific` (`custom_count`): Incremented if the control's customization source in `FrameworkAssignment` **is** `"custom"`.
- `auditDashboard.gapAnalysis[].value`: `round((1 - comparison_score) * 10)`. Maps failing ratio to a 0-10 scale for charts.
- `nonCompliantControls[].failing`: `round((1 - comparison_score) * 100) + "%"`. Represents the percentage gap of the control.
