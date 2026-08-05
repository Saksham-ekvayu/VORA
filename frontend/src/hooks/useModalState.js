import { useState } from "react";

/**
 * Custom hook for managing modal state
 * Eliminates duplication across 30+ modal components
 */
export function useModalState(initialMode = "create") {
  const [isOpen, setIsOpen] = useState(false);
  const [mode, setMode] = useState(initialMode);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const openModal = (modalMode = "create", modalData = null) => {
    setMode(modalMode);
    setData(modalData);
    setErrors({});
    setIsOpen(true);
  };

  const closeModal = () => {
    setIsOpen(false);
    setMode(initialMode);
    setData(null);
    setErrors({});
    setLoading(false);
  };

  const resetForm = () => {
    setData(null);
    setErrors({});
    setLoading(false);
  };

  return {
    isOpen,
    setIsOpen,
    mode,
    setMode,
    data,
    setData,
    loading,
    setLoading,
    errors,
    setErrors,
    openModal,
    closeModal,
    resetForm,
  };
}
