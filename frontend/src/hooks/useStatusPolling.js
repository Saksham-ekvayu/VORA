/* eslint-disable no-console */
import { useEffect, useRef, useState } from "react";

// Stepped polling intervals:
// - First 2 calls at 5-second intervals (first 10 seconds total)
// - Then 10-second intervals to complete 1 minute (60 seconds total)
// - Then 30-second intervals up to a maximum duration of 5 minutes total
// - Stop polling after 5 minutes total duration
const DEFAULT_INTERVALS = [
  5000, // Call #1 after 5s
  5000, // Call #2 after 5s (Total 10s)
  10000, // Call #3 after 10s (Total 20s)
  10000, // Call #4 after 10s (Total 30s)
  10000, // Call #5 after 10s (Total 40s)
  10000, // Call #6 after 10s (Total 50s)
  10000, // Call #7 after 10s (Total 1 minute)
  30000, // Call #8 after 30s (Total 1m 30s)
  30000, // Call #9 after 30s (Total 2 minutes)
  30000, // Call #10 after 30s (Total 2m 30s)
  30000, // Call #11 after 30s (Total 3 minutes)
  30000, // Call #12 after 30s (Total 3m 30s)
  30000, // Call #13 after 30s (Total 4 minutes)
  30000, // Call #14 after 30s (Total 4m 30s)
  30000, // Call #15 after 30s (Total 5 minutes)
];

/**
 * Module-level scheduler — never nested inside the hook, satisfies
 * sonarjs/no-nested-functions (max 4 levels deep).
 *
 * @param {object} ctx - plain object with all mutable state
 */
function scheduleNext(ctx) {
  if (!ctx.active) return;
  if (ctx.pollCount >= ctx.intervals.length) {
    console.log(
      "[useStatusPolling] Maximum polling limit of 5 minutes reached. Stopping polling."
    );
    return;
  }
  const delay = ctx.intervals[ctx.pollCount];
  console.log(
    `[useStatusPolling] Scheduling next poll (Session: ${ctx.activeSessionId}, Count: ${ctx.pollCount}) in ${delay}ms`
  );
  ctx.timerId = setTimeout(ctx.runTick, delay);
}

/**
 * A reusable hook for polling status with stepped backoff.
 *
 * @param {Object}   options
 * @param {boolean}  options.shouldPoll      - Start/stop polling
 * @param {Function} options.onPoll          - Async fn; should return latest framework
 *                                             data so the hook can self-stop on terminal status
 * @param {number[]} options.intervalDelays  - Stepped delay array (ms)
 * @param {string}   options.id              - Record ID for path verification
 * @param {string}   options.pathPattern     - Path pattern to verify current page
 * @param {Array}    options.dependencies    - Unused, retained for backward compatibility
 */
export const useStatusPolling = ({
  shouldPoll,
  onPoll,
  intervalDelays = DEFAULT_INTERVALS,
  id,
  pathPattern,
  dependencies = [], // eslint-disable-line no-unused-vars
  refreshTrigger,
}) => {
  const [isPolling, setIsPolling] = useState(false);
  const [isTimedOut, setIsTimedOut] = useState(false);

  // A single stable ref holds a plain mutable context object.
  // The effect captures `ctx` (not `ctxRef.current`) so the cleanup rule is satisfied.
  const ctxRef = useRef(null);

  if (!ctxRef.current) {
    ctxRef.current = {
      active: false,
      timerId: null,
      pollCount: 0,
      activeSessionId: 0,
      // latest values — updated every render via the block below
      onPoll,
      intervals: intervalDelays,
      id,
      pathPattern,
      runTick: null, // assigned below
      setIsPolling: null,
      setIsTimedOut: null,
    };
  }

  // Keep latest values in sync without triggering re-renders
  const ctx = ctxRef.current;
  ctx.onPoll = onPoll;
  ctx.intervals = intervalDelays;
  ctx.id = id;
  ctx.pathPattern = pathPattern;
  ctx.setIsPolling = setIsPolling;
  ctx.setIsTimedOut = setIsTimedOut;

  // runTick is a plain function assigned to ctx — not nested inside useEffect
  ctx.runTick = async function runTick() {
    const { id: pid, pathPattern: ppath, activeSessionId } = ctx;
    const stillOnPage =
      !ppath || !pid || globalThis.location.pathname.includes(`${ppath}${pid}`);

    if (!ctx.active || !stillOnPage) {
      console.log(
        `[useStatusPolling] Skipping tick (Session: ${activeSessionId}): active=${ctx.active}, stillOnPage=${stillOnPage}`
      );
      return;
    }

    console.log(
      `[useStatusPolling] Executing poll request (Session: ${activeSessionId}, Count: ${ctx.pollCount})`
    );

    try {
      const result = await ctx.onPoll();

      // If the session changed during the async onPoll call, ignore the result.
      if (ctx.activeSessionId !== activeSessionId) {
        console.log(
          `[useStatusPolling] Discarding stale poll result (Session: ${activeSessionId}, Current Session: ${ctx.activeSessionId})`
        );
        return;
      }

      ctx.pollCount += 1;

      const versions = result?.fileVersions ?? [];
      const inProgress = versions.filter((v) =>
        ["uploaded", "processing"].includes(v.aiExtraction?.status)
      );
      // Stop polling once all versions have reached a terminal status
      if (inProgress.length === 0 && versions.length > 0) {
        console.log(
          "[useStatusPolling] Terminal status reached (no active files). Stopping polling loop."
        );
        ctx.active = false;
        ctx.setIsPolling(false);
        ctx.setIsTimedOut(false);
        return;
      }
    } catch (err) {
      if (ctx.activeSessionId !== activeSessionId) {
        console.log(
          `[useStatusPolling] Discarding stale poll error (Session: ${activeSessionId}, Current Session: ${ctx.activeSessionId})`
        );
        return;
      }
      ctx.pollCount += 1; // continue on transient network errors
      console.error(
        `[useStatusPolling] Poll request failed (Session: ${activeSessionId}, Count: ${ctx.pollCount}):`,
        err
      );
    }

    scheduleNext(ctx);
  };

  useEffect(() => {
    // Capture ctx in a local variable — satisfies react-hooks/exhaustive-deps
    const localCtx = ctxRef.current;

    const isCorrectPage =
      !pathPattern ||
      !id ||
      globalThis.location.pathname.includes(`${pathPattern}${id}`);

    if (!shouldPoll || !isCorrectPage) {
      if (localCtx.active) {
        console.log(
          `[useStatusPolling] Polling stopped (shouldPoll=${shouldPoll}, isCorrectPage=${isCorrectPage})`
        );
        localCtx.active = false;
        clearTimeout(localCtx.timerId);
        setIsPolling(false);
        setIsTimedOut(false);
      }
      return;
    }

    localCtx.active = true;
    localCtx.pollCount = 0;
    localCtx.activeSessionId += 1;
    setIsPolling(true);
    setIsTimedOut(false);

    console.log(
      `[useStatusPolling] Starting new polling session: ${localCtx.activeSessionId} for id: ${id} on path: ${pathPattern}`
    );

    scheduleNext(localCtx);

    return () => {
      console.log(
        `[useStatusPolling] Cleaning up polling session: ${localCtx.activeSessionId}`
      );
      localCtx.active = false;
      clearTimeout(localCtx.timerId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shouldPoll, id, pathPattern, refreshTrigger]);

  return { isPolling, isTimedOut };
};
