/* eslint-disable react/prop-types */

import { useState } from "react";
import { Helmet } from "react-helmet-async";
import { toast } from "sonner";
import DataTable from "@/components/data-table/DataTable";
import CustomerManageModal from "./components/CustomerManageModal";
import { ConfirmDeleteModal } from "@/components/custom/modal";
import PhoneDisplay from "@/components/custom/PhoneDisplay";
import {
  getAllCustomers,
  createCustomer,
  updateCustomer,
  toggleCustomerStatus,
  deleteCustomer,
} from "@/services/customerService";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import {
  getStatusFilterLabel,
  isAdmin,
  STATUS_LABELS,
  STATUS_ACTIVE,
  STATUS_INACTIVE,
} from "@/utils/commonUtils";
import CustomBadge from "@/components/custom/CustomBadge";
import UserMiniCard from "@/components/custom/UserMiniCard";
import ActionDropdown from "@/components/custom/ActionDropdown";
import { useAuth } from "@/context/authContext/useAuth";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import { useNavigate } from "react-router-dom";

export default function Customers() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [customerModalState, setCustomerModalState] = useState({
    isOpen: false,
    mode: "create",
    customer: null,
  });

  const [deleteModalState, setDeleteModalState] = useState({
    isOpen: false,
    customer: null,
  });

  // Use custom hook for table data management
  const {
    data: customers,
    loading,
    error,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onSearch: handleSearch,
    onSort: handleSort,
    onFilterChange,
    refetch,
  } = useTableData(getAllCustomers, {
    defaultLimit: 10,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No customers found",
  });

  /* ---------------- HANDLERS ---------------- */
  const handleStatusFilter = (status) => {
    onFilterChange("isActive", status);
  };

  /* ---------------- CRUD ---------------- */
  const handleSaveCustomer = async (data) => {
    try {
      if (customerModalState.mode === "create") {
        const response = await createCustomer(data);
        if (!response?.success) {
          throw new Error(response?.message || "Failed to create customer");
        }
        toast.success(response.message || "Customer created successfully");
      } else {
        const customerId =
          customerModalState.customer?.id || customerModalState.customer?._id;
        const response = await updateCustomer(customerId, data);
        if (!response?.success) {
          throw new Error(response?.message || "Failed to update customer");
        }
        toast.success(response.message || "Customer updated successfully");
      }
      setCustomerModalState({ isOpen: false, mode: "create", customer: null });
      refetch();
    } catch (e) {
      console.error("Save customer error:", e);
      throw e;
    }
  };

  const handleDeleteCustomer = async () => {
    try {
      const customerId =
        deleteModalState.customer?.id || deleteModalState.customer?._id;

      if (!customerId) {
        toast.error("Customer ID not found. Cannot delete customer.");
        return;
      }

      const response = await deleteCustomer(customerId);
      if (!response?.success) {
        throw new Error(response?.message || "Failed to delete customer");
      }
      toast.success("Customer deleted successfully");
      setDeleteModalState({ isOpen: false, customer: null });
      refetch();
    } catch (e) {
      toast.error(e.message || "Failed to delete customer");
      console.error("Delete customer error:", e);
      throw e;
    }
  };

  const handleToggleStatus = async (row) => {
    try {
      const customerId = row?.id || row?._id;

      if (!customerId) {
        toast.error("Customer ID not found. Cannot toggle status.");
        return;
      }

      const response = await toggleCustomerStatus(customerId);
      toast.success(response.message || "Customer status updated successfully");
      refetch();
    } catch (e) {
      toast.error(e.message || "Failed to toggle customer status");
      console.error("Toggle status error:", e);
      throw e;
    }
  };

  /* ---------------- TABLE CONFIG ---------------- */
  const columns = [
    {
      key: "name",
      label: "Customer / Organization",
      sortable: true,
      render: (value, row) => (
        <UserMiniCard
          name={value}
          email={row.email}
          avatar={row.avatar}
          link={`/customers/${row.id}`}
        />
      ),
    },
    {
      key: "phone",
      label: "Phone",
      sortable: false,
      render: (value) => <PhoneDisplay value={value} />,
    },
    {
      key: "isActive",
      label: "Status",
      sortable: false,
      render: (v) => <CustomBadge isActive={v} />,
    },
    {
      key: "createdBy",
      label: "Created By",
      sortable: false,
      render: (value, row) => {
        if (row.createdBy === "self" || row.createdBy?.type === "self") {
          return <UserMiniCard isSelf />;
        }

        if (row.createdBy?.user?.id) {
          return (
            <div className="max-w-60">
              <UserMiniCard
                name={row.createdBy.user.name}
                email={row.createdBy.user.email}
                avatar={row.createdBy.user.avatar}
              />
            </div>
          );
        }

        return <span>-</span>;
      },
    },
    {
      key: "createdAt",
      label: "Created On",
      sortable: true,
      render: (value) => (
        <span className="text-sm whitespace-nowrap">
          {formatDateWithMonthNameAndTime(value)}
        </span>
      ),
    },
    {
      key: "updatedAt",
      label: "Updated On",
      sortable: true,
      render: (value) => (
        <span className="text-sm whitespace-nowrap">
          {formatDateWithMonthNameAndTime(value)}
        </span>
      ),
    },
  ];

  const renderActions = (row) => {
    const actions = [
      {
        id: `view-${row.id || row._id}`,
        label: "View Customer Details",
        icon: "eye",
        onClick: () => {
          navigate(`/customers/${row.id}`);
        },
      },
      {
        id: `edit-${row.id || row._id}`,
        label: "Edit Customer",
        icon: "edit",
        disabled: !row.isActive,
        onClick: () => {
          setCustomerModalState({
            isOpen: true,
            mode: "update",
            customer: row,
          });
        },
      },
      {
        id: `toggle-${row.id || row._id}`,
        label: row.isActive ? "Deactivate Customer" : "Activate Customer",
        icon: "power",
        onClick: () => handleToggleStatus(row),
      },
      {
        id: `delete-${row.id || row._id}`,
        label: "Delete Customer",
        icon: "trash",
        variant: "destructive",
        onClick: () => setDeleteModalState({ isOpen: true, customer: row }),
      },
    ];

    return (
      <div className="flex justify-center">
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
            label: STATUS_LABELS[STATUS_ACTIVE],
            onClick: () => handleStatusFilter("true"),
            separatorBefore: true,
          },
          {
            label: STATUS_LABELS[STATUS_INACTIVE],
            onClick: () => handleStatusFilter("false"),
          },
        ],
      },
      isAdmin(user?.role) && {
        type: "button",
        label: "Create Customer",
        icon: "plus",
        onClick: () =>
          setCustomerModalState({
            isOpen: true,
            mode: "create",
            customer: null,
          }),
      },
    ].filter(Boolean);
  };

  return (
    <div className="my-2">
      <Helmet>
        <title>VORA - Customers</title>
      </Helmet>
      {/* Data Table */}
      <DataTable
        entityName="Customers"
        columns={columns}
        data={customers}
        loading={loading}
        onSearch={handleSearch}
        onSort={handleSort}
        sortConfig={sortConfig}
        searchTerm={searchTerm}
        pagination={pagination}
        renderActions={renderActions}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search customers by name, email, phone..."
        emptyMessage={emptyMessage}
        error={error}
      />

      {/* Customer Create/Edit Modal */}
      {customerModalState.isOpen && (
        <CustomerManageModal
          open={customerModalState.isOpen}
          onOpenChange={(open) => {
            if (!open) {
              setCustomerModalState({
                isOpen: false,
                mode: "create",
                customer: null,
              });
            }
          }}
          mode={customerModalState.mode}
          customer={customerModalState.customer}
          onSave={handleSaveCustomer}
        />
      )}

      {/* Delete Customer Modal */}
      {deleteModalState.isOpen && deleteModalState.customer && (
        <ConfirmDeleteModal
          open={deleteModalState.isOpen}
          onCancel={() =>
            setDeleteModalState({ isOpen: false, customer: null })
          }
          onConfirm={handleDeleteCustomer}
          title="Delete Customer"
          description="Are you sure you want to delete this customer organization? This action cannot be undone."
          entityIcon="building"
          entityName={deleteModalState.customer.name}
          entitySubtitle={deleteModalState.customer.email}
          badges={[
            {
              text: deleteModalState.customer.tenantId,
              className: "bg-blue-100 text-blue-800",
            },
            {
              text: deleteModalState.customer.isActive ? "Active" : "Inactive",
              className: deleteModalState.customer.isActive
                ? "bg-green-100 text-green-800"
                : "bg-red-100 text-red-800",
            },
          ]}
        />
      )}
    </div>
  );
}
