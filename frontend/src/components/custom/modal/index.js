// ── Confirm / alert shell ────────────────────────────────────────────────────
export { default as ConfirmModal } from "./ConfirmModal";
export {
  default as ConfirmDeleteModal,
  DeleteUserModal,
  DeleteFrameworkModal,
  DeleteDeploymentFrameworkModal,
} from "./ConfirmDeleteModal";

// ── Alert / info boxes ───────────────────────────────────────────────────────
export { default as WarningBox } from "./WarningBox";

// ── Picker-modal table helpers ───────────────────────────────────────────────
export {
  ModalTableBody,
  ModalTablePagination,
  ModalSearchInput,
} from "./ModalTable";

// ── Hook: paginated list state for dual-table picker modals ──────────────────
export { default as useModalPaginatedList } from "./hooks/useModalPaginatedList";
export { default as DualSelectionModal } from "./DualSelectionModal";
export { default as RecordTimelineViewModal } from "./RecordTimelineViewModal";

// ── Fetch helpers: stable API wrappers for picker modals ─────────────────────
export {
  fetchUsersFn,
  fetchCustomersFn,
  fetchApprovedFrameworksFn,
  fetchFrameworkCategoriesFn,
} from "./helpers/modalFetchHelpers";

// ── Re-export shared modal primitives so consumers use one import path ────────
export { default as ModalHeader } from "./ModalHeader";
export { default as ModalFooter } from "./ModalFooter";
export { default as ControlModal } from "./ControlModal";
