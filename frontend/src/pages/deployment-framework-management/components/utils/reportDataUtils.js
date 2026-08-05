/* eslint-disable react/prop-types */

import { STATUS_PENDING } from "@/utils/commonUtils";

/**
 * reportDataUtils.js
 *
 * Transforms the raw API/JSON payload into the four data
 * constants that DeploymentFrameworkReport expects:
 *   CONTROLS  – array of control summary objects
 *   DP_DATA   – map of controlId → array of DP detail rows
 *   ACTIONS   – map of controlId → recommended action string
 *   DOCS      – array of document objects
 *
 * Expected JSON shape:
 * {
 *   success, message,
 *   data: {
 *     frameworkName, frameworkVersion, tenantId, uploadedBy, createdAt,
 *     packages: [{
 *       packageVersion, type, status, trigger,
 *       documents: [...],
 *       comparison: {
 *         status, comparison_result: [{
 *           id, name,
 *           controls: [{
 *             deployment_framework_control_id,
 *             deployment_framework_control_name,
 *             deployment_framework_control_description,
 *             deployment_framework_deployment_points: [{ id, point }],
 *             assigned_framework_control_id,
 *             assigned_framework_control_name,
 *             assigned_framework_control_description,
 *             assigned_framework_deployment_points: [{ id, point }],
 *             comparison_score   // 0–1 float
 *           }]
 *         }]
 *       },
 *       gapAnalysis: {
 *         status, deployment_gap_results: [{
 *           id, name,
 *           controls: [{
 *             "A.5.6": [{
 *               assigned_framework_control_id,
 *               assigned_framework_control_name,
 *               assigned_framework_deployment_points: { id, point },
 *               deployment_framework_control_id,
 *               deployment_framework_control_name,
 *               deployment_framework_deployment_points: { id, point },
 *               similarity_score,        // 0–100
 *               implementation_status    // lowercase string
 *             }]
 *           }]
 *         }]
 *       },
 *       expertReview: { status, assignedExpert, comments, ... }
 *     }]
 *   }
 * }
 */

/* ─── STATUS CONSTANTS (mirror the component) ─────────────── */
const IMPLEMENTED = "Implemented";
const PARTIALLY_IMPLEMENTED = "Partially Implemented";
const NOT_IMPLEMENTED = "Not Implemented";
const HIGH = "High";
const MEDIUM = "Medium";
const LOW = "Low";

/* ─── HELPERS ─────────────────────────────────────────────── */

function normaliseMatch(score) {
  if (score >= 80) return HIGH;
  if (score >= 60) return MEDIUM;
  return LOW;
}

function normaliseStatus(raw = "") {
  const s = String(raw).trim().toLowerCase();
  if (s === "implemented") return IMPLEMENTED;
  if (s === "not implemented" || s.includes("not impl")) return NOT_IMPLEMENTED;
  return PARTIALLY_IMPLEMENTED;
}

function formatSize(bytes) {
  if (!bytes || Number.isNaN(bytes)) return "—";
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(2)} MB`;
  if (bytes >= 1_024) return `${(bytes / 1_024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function formatStatusLabel(status) {
  if (!status) return "Pending";
  return String(status)
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

/* ─── DP ROW MAPPER ────────────────────────────────────────── */

/**
 * Map a single raw gap-analysis row into a DP_DATA entry.
 * New shape: { assigned_framework_deployment_points: { id, point },
 *              deployment_framework_deployment_points: { id, point },
 *              similarity_score, implementation_status }
 */
function mapDpRow(row, idx) {
  return {
    no: row.assigned_framework_deployment_points?.id ?? idx + 1,
    assigned_framework_control_id: row.assigned_framework_control_id ?? "",
    assigned_framework_control_name: row.assigned_framework_control_name ?? "",
    assigned_dp_id: row.assigned_framework_deployment_points?.id ?? null,
    clientDp: row.assigned_framework_deployment_points?.point ?? "",

    deployment_framework_control_id: row.deployment_framework_control_id ?? "",
    deployment_framework_control_name:
      row.deployment_framework_control_name ?? "",
    deployment_dp_id: row.deployment_framework_deployment_points?.id ?? null,
    matchedFp: row.deployment_framework_deployment_points?.point ?? "",

    sim: Number(row.similarity_score ?? 0),
    status: normaliseStatus(row.implementation_status),
  };
}

/* ─── DP_DATA BUILDER ──────────────────────────────────────── */

/**
 * Flatten gapAnalysis.deployment_gap_results into a plain map:
 *   { "A.5.6": [ rows ], "A.5.7": [ rows ], … }
 *
 * Each section has:
 *   { id, name, controls: [ { "A.5.6": [...rows] } ] }
 */
function buildDpData(gapResults) {
  const DP_DATA = {};
  for (const section of gapResults) {
    for (const controlObj of section.controls ?? []) {
      for (const [controlId, dpRows] of Object.entries(controlObj)) {
        for (const row of dpRows) {
          const depId = row.deployment_framework_control_id || controlId;
          if (!DP_DATA[depId]) {
            DP_DATA[depId] = [];
          }
          DP_DATA[depId].push(mapDpRow(row, DP_DATA[depId].length));
        }
      }
    }
  }
  return DP_DATA;
}

/* ─── IMPL COUNT HELPERS ───────────────────────────────────── */

function countFromDpRows(dpRows) {
  let impl = 0,
    partial = 0,
    notImpl = 0;
  for (const dp of dpRows) {
    if (dp.status === IMPLEMENTED) impl++;
    else if (dp.status === PARTIALLY_IMPLEMENTED) partial++;
    else notImpl++;
  }
  return { impl, partial, notImpl };
}

function resolveImplCounts(controlId, DP_DATA) {
  const dpRows = DP_DATA[controlId] ?? [];
  return countFromDpRows(dpRows);
}

/* ─── AVERAGE SIMILARITY ───────────────────────────────────── */

function avgSim(dpRows) {
  if (!dpRows?.length) return 0;
  return dpRows.reduce((acc, d) => acc + d.sim, 0) / dpRows.length;
}

function syncControlMetrics(CONTROLS, DP_DATA) {
  for (const ctrl of CONTROLS) {
    const dpRows = DP_DATA[ctrl.id] ?? [];
    const { impl, partial, notImpl } = countFromDpRows(dpRows);
    ctrl.impl = impl;
    ctrl.partial = partial;
    ctrl.notImpl = notImpl;
    ctrl.sim = +avgSim(dpRows).toFixed(1);
  }
}

/* ─── MAIN BUILDER ─────────────────────────────────────────── */

/**
 * @param {object} json  – the raw response object
 *                         Pass either the full response ({ success, data: {...} })
 *                         or the data object directly.
 * @returns {{ CONTROLS, DP_DATA, ACTIONS, DOCS, META }}
 */
export function buildReportData(json) {
  /* Support both { success, data: {...} } and the data object directly */
  const root = json?.data ?? json;

  /* ── 1. Find the package matching currentPackageVersion ─── */
  const currentVersion = root?.currentPackageVersion;
  const pkg =
    root?.packages?.find((p) => p.packageVersion === currentVersion) ??
    root?.packages?.[0] ??
    {};

  /* ── 2. Build DOCS ──────────────────────────────────────── */
  const DOCS = (pkg.documents ?? []).map((doc) => ({
    name: doc.originalFileName ?? doc.fileId ?? "Unknown",
    type: (doc.fileType ?? "pdf").toUpperCase(),
    size: formatSize(doc.fileSize),
    rep: doc.replicated ?? false,
    aiStatus: doc.aiExtraction?.status ?? STATUS_PENDING,
    aiStatusLabel: formatStatusLabel(
      doc.aiExtraction?.status ?? STATUS_PENDING
    ),
    fileUrl: doc.fileUrl ?? "",
    fileId: doc.fileId ?? "",
  }));

  /* ── 3. Build DP_DATA from gapAnalysis ──────────────────── */
  const gapResults = pkg.gapAnalysis?.deployment_gap_results ?? [];
  const DP_DATA = buildDpData(gapResults);

  /* ── 4. Build CONTROLS & ACTIONS from comparison_result ─── */
  const CONTROLS = [];
  const ACTIONS = {};

  for (const section of pkg.comparison?.comparison_result ?? []) {
    for (const ctrl of section.controls ?? []) {
      // Use deployment_framework_control_id as the primary key
      const controlId =
        ctrl.deployment_framework_control_id ||
        ctrl.assigned_framework_control_id ||
        "";
      const rawScore = ctrl.comparison_score ?? 0;
      // comparison_score is 0–1 float; convert to 0–100
      const score = Math.round(rawScore * 100);

      const { impl, partial, notImpl } = resolveImplCounts(controlId, DP_DATA);
      const sim = avgSim(DP_DATA[controlId] ?? []);

      CONTROLS.push({
        id: controlId,
        name:
          ctrl.assigned_framework_control_name ||
          ctrl.deployment_framework_control_name ||
          controlId,
        assigned_id: ctrl.assigned_framework_control_id || "",
        assigned_name: ctrl.assigned_framework_control_name || "",
        assigned_description: ctrl.assigned_framework_control_description || "",
        deployment_id: ctrl.deployment_framework_control_id || "",
        deployment_name: ctrl.deployment_framework_control_name || "",
        deployment_description:
          ctrl.deployment_framework_control_description || "",
        score,
        match: normaliseMatch(score),
        impl,
        partial,
        notImpl,
        sim: +sim.toFixed(1),
      });

      ACTIONS[controlId] = "";
    }
  }

  /* ── 5. Sync metrics from DP_DATA ───────────────────────── */
  syncControlMetrics(CONTROLS, DP_DATA);

  /* ── 6. Build META for hero section ─────────────────────── */
  const expertReview = pkg.expertReview ?? {};
  const uploadedBy = root?.uploadedBy ?? {};
  const assignedFramework = root?.assignedFramework ?? {};

  const META = {
    frameworkName:
      root?.frameworkName ??
      assignedFramework?.frameworkName ??
      "Framework Report",
    frameworkVersion:
      root?.frameworkVersion ?? assignedFramework?.frameworkVersion ?? "",
    frameworkCode:
      root?.frameworkCode ?? assignedFramework?.frameworkCode ?? "",
    frameworkId: root?.frameworkId ?? assignedFramework?.id ?? "",
    packageVersion: pkg.packageVersion ?? "",
    packageType: pkg.type ?? "",
    packageStatus: pkg.status ?? "",
    trigger: pkg.trigger ?? "",
    totalDp: gapResults.reduce(
      (acc, sec) =>
        acc +
        (sec.controls ?? []).reduce(
          (a, cObj) =>
            a + Object.values(cObj).reduce((s, rows) => s + rows.length, 0),
          0
        ),
      0
    ),
    totalControls: CONTROLS.length,
    tenantId: root?.tenantId ?? "",
    uploadedBy: {
      id: uploadedBy?.id ?? "",
      name: uploadedBy?.name ?? "",
      email: uploadedBy?.email ?? "",
      role: uploadedBy?.role ?? "",
      avatar: uploadedBy?.avatar ?? null,
    },
    createdAt: root?.createdAt ?? "",
    updatedAt: root?.updatedAt ?? "",
    expertReview: {
      status: expertReview.status ?? STATUS_PENDING,
      statusLabel: formatStatusLabel(expertReview.status ?? STATUS_PENDING),
      assignedExpert: expertReview.assignedExpert ?? null,
      requestedAt: expertReview.requestedAt ?? null,
      reviewedAt: expertReview.reviewedAt ?? null,
      comments: expertReview.comments ?? null,
    },
    gapAnalysisStatus: pkg.gapAnalysis?.status ?? STATUS_PENDING,
    comparisonStatus: pkg.comparison?.status ?? STATUS_PENDING,
  };

  return { CONTROLS, DP_DATA, ACTIONS, DOCS, META };
}
