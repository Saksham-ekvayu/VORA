import { useEffect } from "react";

/**
 * Reusable hook to set a dynamic breadcrumb/header label for a specific ID/segment.
 *
 * @param {string} id - The URL segment (ID) to replace (e.g. "69cb9...")
 * @param {string} label - The friendly name to display in breadcrumbs/header title
 */
export function usePageTitle(id, label) {
  useEffect(() => {
    if (!id || !label) return;

    // Update global registry
    globalThis.__VORA_BREADCRUMB_LABELS__ = {
      ...globalThis.__VORA_BREADCRUMB_LABELS__,
      [id]: label,
    };

    // Dispatch event to notify Layout to re-render
    globalThis.dispatchEvent(new CustomEvent("vora:title-update"));
  }, [id, label]);
}
