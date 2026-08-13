# Deployment Document Extraction - Complete Implementation

## Overview
Deployment Document के लिए **AI Extraction** और **Evidence Generation** integrate किया गया है।

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ MCP Service (Team)                                      │
│ → Sends data to Deployment Document                     │
└──────────────────────┬──────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ Extract-Controls-Service                                │
│ • Extracts controls from document                       │
│ • Generates evidence automatically                      │
│ • Stores in deployment_documents table                  │
└──────────────────────┬──────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ Deployment Document (PostgreSQL)                        │
│ ├── document: file info (fileId, fileUrl, etc.)        │
│ ├── aiExtraction: extracted controls                    │
│ └── evidence: compliant/non-compliant status           │
└─────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### 1. Start Extraction
```
POST /deployment-document/{dd_id}/ai-extract

Request:
  - dd_id: Deployment Document ID (no need to specify file_id)
  
Response:
  {
    "data": {
      "dd_id": "...",
      "file_hash": "...",
      "extraction_id": "...",
      "status": "processing"
    }
  }
```

### 2. Get Deployment Document
```
GET /deployment-document/{dd_id}

Response includes:
  - Document info
  - aiExtraction (extracted controls)
  - evidence (compliant/non-compliant status)
```

### 3. Get Compliance Status (NEW)
```
GET /deployment-document/{dd_id}/compliance

Response:
  {
    "overall_status": "compliant" | "non-compliant",
    "total_controls": int,
    "compliant_count": int,
    "non_compliant_count": int,
    "compliance_percentage": float
  }
```

---

## Evidence Format

Evidence automatically generated और deployment document में store होता है:

```json
{
  "deployment_document_id": "dd_id",
  "file_id": "file_id",
  "framework_name": "ISO 27001",
  "framework_code": "ISO27001",
  "framework_version": "2022",
  "fileVersions": [
    {
      "fileVersion": "1.0",
      "status": "compliant" | "non-compliant",
      "processed_at": "2024-01-01T00:00:00Z",
      "data": {
        "control-id": {
          "control_id": "control-id",
          "name": "Control Name",
          "description": "Description",
          "section": "Section Name",
          "status": "compliant" | "non-compliant",
          "deployment_points_configured": 5
        }
      },
      "summary": {
        "total_controls": 50,
        "compliant_count": 45,
        "non_compliant_count": 5,
        "overall_status": "compliant"
      }
    }
  ]
}
```

---

## Extraction Flow

### Step 1: API Call
```
POST /deployment-document/{dd_id}/ai-extract
```
- Deployment Document ID देना है
- File automatically deployment document से fetch होती है
- Processing status return होता है

### Step 2: Background Processing
1. File load करना (PDF, DOCX, etc.)
2. Chunks में divide करना
3. AI से controls extract करना
4. Section structure बनाना

### Step 3: Evidence Generation
- Controls से compliance status calculate करना
- **Compliant**: अगर control के deployment_points configured हों
- **Non-compliant**: अगर deployment_points empty हों
- Overall status: सभी controls compliant = compliant, else = non-compliant

### Step 4: Save
- `deployment_documents.document.evidence` में save करना
- `document_extractions` table में भी save करना
- Database update करना

---

## Compliance Logic

### Control Status Determination
```python
# Compliant if:
- deployment_points list exists AND
- कम से कम एक deployment_point में path या configuration है

# Non-compliant if:
- deployment_points empty है OR
- सभी deployment_points में path/configuration नहीं है
```

### Overall Status
```python
overall_status = "compliant"  if all_controls_compliant else "non-compliant"
```

---

## Integration Points

### 1. Extract-Controls-Service
- ✅ Deployment document extraction endpoint
- ✅ Evidence generation function
- ✅ Compliance endpoints

### 2. PostgreSQL Database
- ✅ `deployment_documents` table (with evidence field)
- ✅ `document_extractions` table (cache)
- ✅ `evidence_output` table (optional, for compliance agent)

### 3. No Changes Needed
- ✅ Compliance-Agent-Service (सिर्फ read-only)
- ✅ Framework Service (existing logic unchanged)

---

## Testing Endpoints

```bash
# 1. Start extraction
curl -X POST http://localhost:8007/deployment-document/{dd_id}/ai-extract

# 2. Get document with evidence
curl http://localhost:8007/deployment-document/{dd_id}

# 3. Get compliance status
curl http://localhost:8007/deployment-document/{dd_id}/compliance
```

---

## Data Flow Summary

```
Deployment Document Upload
  ↓
MCP adds data (via file upload)
  ↓
Extract-Controls-Service processes
  ├── Extracts controls
  ├── Generates evidence
  └── Updates document with evidence
  ↓
Evidence stored in deployment_documents.document.evidence
  ↓
Compliance status available via API
  ├── Overall: compliant/non-compliant
  ├── Per-control: compliant/non-compliant
  └── Metrics: total, compliant, non-compliant counts
```

---

## Live Data Updates

- ✅ Extraction हो जाने के बाद तुरंत evidence generate हो जाता है
- ✅ Evidence live data से आता है (deployment document से)
- ✅ Data real-time update होता है
- ✅ No separate pipeline needed
- ✅ Compliance status instantly available

---

## Status: ✅ COMPLETE

- ✅ Extraction logic
- ✅ Evidence generation
- ✅ Compliance calculation
- ✅ API endpoints
- ✅ Database integration
- ✅ No breaking changes
