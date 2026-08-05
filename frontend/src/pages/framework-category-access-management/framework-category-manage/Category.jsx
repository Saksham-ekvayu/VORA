/* eslint-disable react/prop-types */

import { useState } from "react";
import { toast } from "sonner";
import {
  getAdminFrameworkCategory,
  createFrameworkCategory,
  updateFrameworkCategory,
  deleteFrameworkCategory,
} from "@/services/adminService";
import CategoryModal from "./components/CategoryModal";
import { ConfirmDeleteModal } from "@/components/custom/modal";
import ActionDropdown from "@/components/custom/ActionDropdown";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import GridCardView from "@/components/grid-card/GridCardView";
import FrameworkCategoryCard from "./components/custom/FrameworkCategoryCard";
import { getStatusFilterLabel } from "@/utils/commonUtils";

function Category() {
  const [modalState, setModalState] = useState({
    isOpen: false,
    mode: "create",
    category: null,
  });

  const [deleteModalState, setDeleteModalState] = useState({
    isOpen: false,
    category: null,
  });

  // Use custom hook for table data management
  const {
    data: frameworkCategories,
    loading,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onFilterChange,
    onSearch: handleSearch,
    onSort: handleSort,
    refetch,
  } = useTableData(getAdminFrameworkCategory, {
    defaultLimit: 12,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No framework categories found",
  });

  /* ---------------- HANDLERS ---------------- */
  const handleStatusFilter = (status) => {
    onFilterChange("isActive", status);
  };

  /* ---------------- CRUD ---------------- */
  const handleSaveCategory = async (data) => {
    try {
      if (modalState.mode === "create") {
        const response = await createFrameworkCategory(data);
        toast.success(response.message || "Category created successfully");
      } else {
        const categoryId = modalState.category?._id || modalState.category?.id;
        const response = await updateFrameworkCategory(categoryId, data);
        toast.success(response.message || "Category updated successfully");
      }
      setModalState({ isOpen: false, mode: "create", category: null });
      refetch();
    } catch (e) {
      console.error("Save category error:", e);
      throw e;
    }
  };

  const handleEditCategory = (category) => {
    setModalState({ isOpen: true, mode: "edit", category: category });
  };

  const handleDeleteInitiate = (category) => {
    setDeleteModalState({ isOpen: true, category: category });
  };

  const handleDeleteCategory = async () => {
    try {
      const categoryId =
        deleteModalState.category?._id || deleteModalState.category?.id;

      if (!categoryId) {
        toast.error("Category ID not found. Cannot delete category.");
        console.error("Category object:", deleteModalState.category);
        return;
      }

      const response = await deleteFrameworkCategory(categoryId);
      toast.success(response.message || "Category deleted successfully");
      setDeleteModalState({ isOpen: false, category: null });
      refetch();
    } catch (e) {
      toast.error(e.message || "Failed to delete category");
      console.error("Delete category error:", e);
    }
  };

  /* ---------------- CONFIG ---------------- */
  const renderActions = (row) => {
    const actions = [
      {
        id: `edit-${row._id || row.id}`,
        label: "Edit Category",
        icon: "edit",
        onClick: () => handleEditCategory(row),
      },
      {
        id: `delete-${row._id || row.id}`,
        label: "Delete Category",
        icon: "trash",
        variant: "destructive",
        onClick: () => handleDeleteInitiate(row),
      },
    ];

    return (
      <div className="h-8 w-8 flex items-center justify-center bg-muted/40 rounded border border-border/40 hover:bg-muted/60 transition-colors">
        <ActionDropdown actions={actions} />
      </div>
    );
  };

  const getHeaderActions = () => {
    const urlParams = new URLSearchParams(globalThis.location.search);
    const statusFilter = urlParams.get("isActive") || "";

    return [
      {
        type: "dropdown",
        label: getStatusFilterLabel(statusFilter),
        triggerClassName: "w-fit",
        options: [
          { label: "All Status", onClick: () => handleStatusFilter("") },
          {
            label: "Active",
            onClick: () => handleStatusFilter("true"),
            separatorBefore: true,
          },
          { label: "Inactive", onClick: () => handleStatusFilter("false") },
        ],
      },
      {
        type: "button",
        label: "Add Category",
        icon: "plus",
        onClick: () =>
          setModalState({ isOpen: true, mode: "create", category: null }),
      },
    ].filter(Boolean);
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="my-2">
      <GridCardView
        data={frameworkCategories}
        loading={loading}
        onSearch={handleSearch}
        searchTerm={searchTerm}
        sortOrder={sortConfig.sortOrder}
        onSortChange={() => handleSort(sortConfig.sortBy)}
        pagination={pagination}
        headerActions={getHeaderActions()}
        renderCard={(category) => (
          <FrameworkCategoryCard
            key={category.id || category._id}
            category={category}
            renderActions={renderActions}
            onEdit={handleEditCategory}
            onDelete={handleDeleteInitiate}
          />
        )}
        searchPlaceholder="Search categories by name or code..."
        emptyMessage={emptyMessage}
        gridCols="grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3"
      />

      {modalState.isOpen && (
        <CategoryModal
          mode={modalState.mode}
          category={modalState.category}
          onSave={handleSaveCategory}
          onClose={() =>
            setModalState({ isOpen: false, mode: "create", category: null })
          }
        />
      )}

      {deleteModalState.isOpen && deleteModalState.category && (
        <ConfirmDeleteModal
          open={deleteModalState.isOpen}
          onCancel={() =>
            setDeleteModalState({ isOpen: false, category: null })
          }
          onConfirm={handleDeleteCategory}
          title="Delete Category"
          description="Confirm deletion of framework category. This action cannot be undone."
          bodyText="Are you sure you want to delete this framework category? This action cannot be undone."
          entityIcon="chart"
          entityName={deleteModalState.category.frameworkCategoryName}
          entitySubtitle={`Code: ${deleteModalState.category.code}`}
          badges={[
            {
              text: deleteModalState.category.isActive ? "Active" : "Inactive",
              className: deleteModalState.category.isActive
                ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
            },
          ]}
        >
          {deleteModalState.category.description && (
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              {deleteModalState.category.description}
            </p>
          )}
        </ConfirmDeleteModal>
      )}
    </div>
  );
}

export default Category;
