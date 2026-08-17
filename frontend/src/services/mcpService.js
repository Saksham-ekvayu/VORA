import { apiRequest } from "./apiService";

/**
 * Start the MCP Scheduler
 * @param {Object} payload
 * @returns {Promise}
 */
export async function startMcpScheduler(payload) {
  return apiRequest(
    "/mcp/scheduler/start",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    true
  );
}

/**
 * Stop the MCP Scheduler
 * @returns {Promise}
 */
export async function stopMcpScheduler() {
  return apiRequest("/mcp/scheduler/stop", true);
}

/**
 * Get the current MCP Scheduler status
 * @returns {Promise}
 */
export async function getMcpSchedulerStatus() {
  return apiRequest("/mcp/scheduler/status", true);
}

/**
 * Get the current MCP Scheduler live logs
 * @returns {Promise}
 */
// Responce formate
// {
//   "status": true,
//   "total_logs": 33,
//   "logs": [
//     "LIVE package found: 1.0.0",
//     "Source paths: ['C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT']",
//     "Total files fetched: 4",
//     "LIVE package found: 1.0.0",
//     "Source paths: ['C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT']",
//     "Total files fetched: 4",
//     "LIVE package found: 1.0.0",
//     "Source paths: ['C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT', 'C:\\\\EKVAYU\\\\VORA\\\\docs\\\\ISO-27001-2022-DEPLOYMENT']",
//     "Total files fetched: 4",
//   ]
// }
export async function getMcpSchedulerLiveLogs() {
  return apiRequest("/mcp/scheduler/live-logs", true);
}
