/* eslint-disable react/prop-types */

import { useEffect, useRef, useState } from "react";
import { apiRequest } from "@/services/apiService";
import {
  Dialog,
  DialogContent,
  DialogClose,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

const IFRAME_TYPES = new Set([
  "pdf",
  "png",
  "jpg",
  "jpeg",
  "gif",
  "webp",
  "svg",
  "txt",
]);
const DOCX_TYPES = new Set(["docx", "doc"]);

function getExtension(fileName = "") {
  return fileName.split(".").pop()?.toLowerCase() || "";
}

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

const CloseIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-5 w-5"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
  >
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>
);

const DownloadIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-4 w-4"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

async function loadDocx(blob, containerRef, cancelled) {
  const { renderAsync } = await import("docx-preview");
  await delay(50);
  if (cancelled() || !containerRef.current) return false;

  await renderAsync(blob, containerRef.current, null, {
    className: "docx-preview",
    inWrapper: true,
    ignoreWidth: true, // Change to true to respect original document width
    ignoreHeight: false,
    ignoreFonts: false,
    breakPages: true,
    useBase64URL: true,
  });
  return true;
}

/**
 * FilePreviewModal
 * - PDF / images / txt  → blob URL in iframe (native browser rendering)
 * - docx / doc          → docx-preview (original Word formatting)
 * - other types         → unsupported message
 *
 * @param {Object} props
 * @param {string} props.fileId - File ID
 * @param {string} props.fileName - File name
 * @param {boolean} props.open - Modal open state
 * @param {Function} props.onClose - Close callback
 * @param {Function} props.onDownload - Download callback
 * @param {string} props.serviceType - Service type: 'framework', 'deployment-framework', 'deployment-document'
 * @param {string} props.frameworkId - Required for deployment-framework
 */
const FilePreviewModal = ({
  fileId,
  fileName,
  open,
  onClose,
  onDownload,
  serviceType = "framework",
  frameworkId,
}) => {
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [blobUrl, setBlobUrl] = useState(null);

  const containerRef = useRef(null);
  const blobUrlRef = useRef(null);
  const cancelledRef = useRef(false);

  const ext = getExtension(fileName);

  const getPreviewEndpoint = (fileId, serviceType, frameworkId) => {
    switch (serviceType) {
      case "deployment-framework":
        return `/deployment-frameworks/${frameworkId}/files/${fileId}/preview`;
      case "deployment-document":
        return `/deployment-documents/${frameworkId}/files/${fileId}/preview`;
      case "framework":
        return `/framework/${frameworkId}/files/${fileId}/preview`;
      default:
        return `/framework/${frameworkId}/files/${fileId}/preview`;
    }
  };

  const handleDocxPreview = async (blob) => {
    const rendered = await loadDocx(
      blob,
      containerRef,
      () => cancelledRef.current
    );
    if (!cancelledRef.current && rendered) setStatus("ready");
  };

  const handleIframePreview = async (blob) => {
    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    const url = URL.createObjectURL(blob);
    blobUrlRef.current = url;
    if (!cancelledRef.current) {
      setBlobUrl(url);
      setStatus("ready");
    }
  };

  // Load file when modal opens
  useEffect(() => {
    if (!open || !fileId) return;

    const isDocx = DOCX_TYPES.has(ext);
    const isIframe = IFRAME_TYPES.has(ext);

    cancelledRef.current = false;
    setStatus("loading");
    setError(null);
    setBlobUrl(null);

    const load = async () => {
      try {
        const endpoint = getPreviewEndpoint(fileId, serviceType, frameworkId);
        const blob = await apiRequest(
          endpoint,
          { method: "GET", responseType: "blob" },
          true
        );

        if (cancelledRef.current) return;

        if (isDocx) {
          await handleDocxPreview(blob);
        } else if (isIframe) {
          await handleIframePreview(blob);
        } else if (!cancelledRef.current) {
          setStatus("unsupported");
        }
      } catch (err) {
        if (!cancelledRef.current) {
          setError(err?.message || "Failed to load file");
          setStatus("error");
        }
      }
    };

    load();

    return () => {
      cancelledRef.current = true;
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, [open, fileId, ext, serviceType, frameworkId]);

  // Cleanup on close (clear docx container)
  useEffect(() => {
    if (!open) {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
      setBlobUrl(null);
      setStatus("idle");
      setError(null);
      if (containerRef.current) containerRef.current.innerHTML = "";
    }
  }, [open]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    };
  }, []);

  const isDocx = DOCX_TYPES.has(ext);
  const isIframe = IFRAME_TYPES.has(ext);

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="min-w-[60vw] h-[90vh] max-w-none p-0 overflow-hidden"
        showCloseButton={false}
      >
        <DialogTitle className="sr-only">
          {fileName || "File Preview"}
        </DialogTitle>
        <DialogDescription className="sr-only">File preview</DialogDescription>
        {status === "loading" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-gray-500 bg-white z-10">
            <svg
              className="animate-spin h-8 w-8"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8z"
              />
            </svg>
            <span className="text-sm">Loading preview…</span>
          </div>
        )}

        {status === "error" && (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 text-center px-6">
            <p className="font-medium text-red-500">Could not load preview</p>
            <p className="text-sm text-gray-500">{error}</p>
          </div>
        )}

        {status === "unsupported" && (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
            Preview not available for .{ext} files
          </div>
        )}

        {isIframe && blobUrl && (
          <iframe
            src={ext === "pdf" ? `${blobUrl}#toolbar=0` : blobUrl}
            title={fileName || "File preview"}
            className="flex-1 w-full h-full border-0"
            allow="fullscreen"
          />
        )}

        {isDocx && (
          <div
            ref={containerRef}
            className="flex-1 overflow-auto w-full h-full"
          />
        )}

        <DialogClose asChild>
          <button
            type="button"
            className="absolute top-4 right-5 text-white bg-black/50 rounded-full p-2 hover:bg-black/80 transition cursor-pointer z-10"
            aria-label="Close preview"
            title="Close preview"
          >
            <CloseIcon />
          </button>
        </DialogClose>

        {onDownload && (
          <button
            type="button"
            className="absolute top-15 right-5 text-white bg-black/50 rounded-full p-2.5 hover:bg-black/80 transition cursor-pointer z-10 flex items-center gap-1.5 text-sm font-medium"
            onClick={onDownload}
            aria-label="Download file"
            title="Download file"
          >
            <DownloadIcon />
          </button>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default FilePreviewModal;
