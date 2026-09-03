import { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import Icon from "@/components/custom/Icon";
import CustomBadge from "@/components/custom/CustomBadge";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import McpSchedulerModal from "./components/McpSchedulerModal";
import {
  getMcpSchedulerStatus,
  getMcpSchedulerLiveLogs,
  stopMcpScheduler,
} from "@/services/mcpService";

export default function McpMonitoring() {
  usePageTitle("monitoring", "MCP Monitoring");
  const navigate = useNavigate();

  const [isSchedulerModalOpen, setIsSchedulerModalOpen] = useState(false);
  const [mcpStatus, setMcpStatus] = useState(null);
  const [isFetchingMcpStatus, setIsFetchingMcpStatus] = useState(false);

  const [logs, setLogs] = useState([]);
  const [isPolling, setIsPolling] = useState(true);
  const [isFetchingLogs, setIsFetchingLogs] = useState(false);
  const [isDownloadingLogs, setIsDownloadingLogs] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const scrollRef = useRef(null);

  // Fetch Status
  const fetchMcpStatus = useCallback(async () => {
    setIsFetchingMcpStatus(true);
    try {
      const res = await getMcpSchedulerStatus();
      setMcpStatus(res);
    } catch {
      setMcpStatus({ running: false });
    } finally {
      setIsFetchingMcpStatus(false);
    }
  }, []);

  useEffect(() => {
    fetchMcpStatus();
  }, [fetchMcpStatus]);

  // Fetch Live Logs (Polling)
  const fetchLiveLogs = useCallback(async () => {
    setIsFetchingLogs(true);
    try {
      const res = await getMcpSchedulerLiveLogs();
      if (res?.status && Array.isArray(res.logs)) {
        setLogs(res.logs);
      }
    } catch (error) {
      console.error("Failed to fetch live logs", error);
    } finally {
      setIsFetchingLogs(false);
    }
  }, []);

  const handleDownloadLogs = async () => {
    if (logs.length === 0 || isDownloadingLogs) return;

    setIsDownloadingLogs(true);
    await new Promise((resolve) => {
      requestAnimationFrame(resolve);
    });

    try {
      const logContent = logs
        .map((log, index) => `[${String(index + 1).padStart(3, "0")}] ${log}`)
        .join("\n");
      const blob = new Blob([logContent], { type: "text/plain;charset=utf-8" });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const timestamp = new Date().toISOString().replace(/[.:]/g, "-");

      link.href = downloadUrl;
      link.download = `mcp-logs-${timestamp}.txt`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
    } finally {
      setIsDownloadingLogs(false);
    }
  };

  const handleStop = async () => {
    setIsStopping(true);
    try {
      const res = await stopMcpScheduler();
      toast.success(res.message || "MCP Scheduler stopped successfully");
      fetchMcpStatus(); // refresh status
    } catch (error) {
      toast.error(error.message || "Failed to stop MCP Scheduler");
    } finally {
      setIsStopping(false);
    }
  };

  useEffect(() => {
    // Initial fetch of logs only if it might be running
    if (mcpStatus?.running) {
      fetchLiveLogs();
    }

    let intervalId;
    // Only set up the polling interval if polling is unpaused AND the server is running
    if (isPolling && mcpStatus?.running) {
      intervalId = setInterval(() => {
        fetchLiveLogs(); // Fetch live logs
      }, 5000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isPolling, fetchLiveLogs, fetchMcpStatus, mcpStatus?.running]);

  // Auto-scroll to bottom of logs
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  let mcpStatusColor = "gray";
  if (isFetchingMcpStatus) {
    mcpStatusColor = "yellow";
  } else if (mcpStatus?.running) {
    mcpStatusColor = "emerald";
  }

  let mcpStatusLabel = "Stopped";
  if (isFetchingMcpStatus) {
    mcpStatusLabel = "Checking...";
  } else if (mcpStatus?.running) {
    mcpStatusLabel = "Running";
  }

  return (
    <div className="space-y-4 my-2">
      {/* Header */}
      <div className="border border-border rounded bg-card p-2 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded bg-primary/10 flex items-center justify-center">
            <Icon name="activity" size="24px" className="text-primary" />
          </div>
          <div className="flex flex-col">
            <h2 className="text-sm font-semibold text-foreground">
              MCP Monitoring
            </h2>
            <p className="text-xs text-muted-foreground">
              Live monitoring and logs for the MCP Scheduler.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <CustomBadge
            label={mcpStatusLabel}
            color={mcpStatusColor}
            size="md"
            animateDot={mcpStatus?.running && !isFetchingMcpStatus}
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSchedulerModalOpen(true)}
            className="text-xs font-medium border-border bg-accent hover:border-primary hover:bg-primary/10"
          >
            <Icon name="clock" size="14px" className="mr-1" /> MCP Scheduler
          </Button>

          {mcpStatus?.running && (
            <Button
              variant="default"
              size="sm"
              onClick={handleStop}
              disabled={isStopping}
              className="text-xs font-medium bg-red-600 hover:bg-red-700 text-white min-w-25"
            >
              <Icon
                name="close"
                size="14px"
                className={cn("mr-1.5", isStopping && "animate-spin")}
              />
              {isStopping ? "Stopping..." : "Stop Server"}
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/mcp-server/monitoring-setup")}
            className="text-xs font-medium border-border bg-accent hover:border-primary hover:bg-primary/10"
          >
            <Icon name="settings" size="14px" className="mr-1" /> Monitoring
            Setup
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <Card className="border-border shadow-sm p-0 gap-0">
        <CardHeader className="flex flex-row items-center justify-between py-3 border-b border-border bg-accent/30">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Icon name="list" size="16px" className="text-primary" />
            Live Logs
          </CardTitle>
          <div className="flex items-center gap-2">
            {mcpStatus?.running && (
              <Button
                variant="outline"
                size="sm"
                className={cn(
                  "h-7 text-xs font-medium",
                  isPolling
                    ? "text-red-500 hover:text-red-600 hover:bg-red-50"
                    : "text-green-600 hover:text-green-700 hover:bg-green-50"
                )}
                onClick={() => setIsPolling(!isPolling)}
              >
                {isPolling ? "Pause Polling" : "Resume Polling"}
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs font-medium min-w-21.25"
              onClick={fetchLiveLogs}
              disabled={isFetchingLogs}
            >
              <Icon
                name="refresh"
                size="12px"
                className={cn("mr-1", isFetchingLogs && "animate-spin")}
              />
              {isFetchingLogs ? "Refreshing..." : "Refresh"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs font-medium"
              onClick={handleDownloadLogs}
              disabled={logs.length === 0 || isDownloadingLogs}
              title="Download all logs as a text file"
            >
              <Icon
                name="download"
                size="12px"
                className={cn("mr-1", isDownloadingLogs && "animate-spin")}
              />
              {isDownloadingLogs ? "Preparing..." : "Download Logs"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea
            className={cn(
              "w-full bg-muted/20 transition-all duration-300",
              logs.length === 0 ? "h-32" : "h-[65vh] min-h-50"
            )}
          >
            {logs.length === 0 ? (
              <div className="h-32 flex items-center justify-center text-muted-foreground italic font-mono text-base">
                No logs available.
              </div>
            ) : (
              <div className="p-4 font-mono text-[13px] flex flex-col gap-1.5">
                {logs.map((log, idx) => {
                  let textColor = "text-foreground/85";
                  if (
                    log.toLowerCase().includes("error") ||
                    log.toLowerCase().includes("failed")
                  )
                    textColor = "text-red-500 font-medium";
                  else if (log.toLowerCase().includes("success"))
                    textColor = "text-emerald-500 font-medium";
                  else if (log.includes("LIVE package found"))
                    textColor = "text-blue-500 font-medium";
                  else if (log.includes("Source paths:"))
                    textColor = "text-amber-600";

                  return (
                    <div
                      key={idx + 1}
                      className={cn(
                        "py-0.5 border-b border-border/40 wrap-break-word leading-relaxed",
                        textColor
                      )}
                    >
                      <span className="text-muted-foreground/60 mr-3 select-none">
                        [{String(idx + 1).padStart(3, "0")}]
                      </span>
                      {log}
                    </div>
                  );
                })}
                <div ref={scrollRef} />
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      {isSchedulerModalOpen && (
        <McpSchedulerModal
          isOpen={isSchedulerModalOpen}
          onClose={() => setIsSchedulerModalOpen(false)}
          onStatusChange={fetchMcpStatus}
          initialConfig={mcpStatus?.config}
        />
      )}
    </div>
  );
}
