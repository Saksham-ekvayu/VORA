/* eslint-disable react/prop-types */

import { useState } from "react";
import { toast } from "sonner";
import DataTable from "@/components/data-table/DataTable";
import UserModal from "./components/UserModal";
import ExpertModal from "./components/ExpertModal";
import { DeleteUserModal } from "@/components/custom/modal";
import PhoneDisplay from "@/components/custom/PhoneDisplay";
import {
  getAllUsers,
  createUser,
  deleteUser,
  updateUserByAdmin,
  toggleUserStatus,
} from "@/services/userService";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import {
  getRoleFilterLabel,
  getStatusFilterLabel,
  getRoleLabel,
  isAdmin,
  isExpert,
  isCustomerAdmin,
  ROLE_USER,
  ROLE_AUDITOR,
  ROLE_INTERNAL_EXPERT,
  ROLE_EXPERT,
  ROLE_LABELS,
  STATUS_LABELS,
  STATUS_ACTIVE,
  STATUS_INACTIVE,
} from "@/utils/commonUtils";
import CustomBadge from "@/components/custom/CustomBadge";
import UserMiniCard from "@/components/custom/UserMiniCard";
import ActionDropdown from "@/components/custom/ActionDropdown";
import { useAuth } from "@/context/authContext/useAuth";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import CustomerAdminModal from "../customer-management/components/CustomerUserModal";
import { useNavigate } from "react-router-dom";

function Profiles() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [modalState, setModalState] = useState({
    isOpen: false,
    mode: "view",
    user: null,
  });

  const [expertModalState, setExpertModalState] = useState({
    isOpen: false,
    mode: "create",
    expert: null,
  });

  const [customerModalAdminState, setCustomerModalAdminState] = useState({
    isOpen: false,
    mode: "create",
    customer: null,
  });

  const [deleteModalState, setDeleteModalState] = useState({
    isOpen: false,
    user: null,
  });

  // Use custom hook for table data management
  const {
    data: users,
    loading,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onSearch: handleSearch,
    onSort: handleSort,
    onFilterChange,
    refetch,
  } = useTableData(getAllUsers, {
    defaultLimit: 10,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No users found",
  });

  /* ---------------- HANDLERS ---------------- */
  const handleRoleFilter = (role) => {
    onFilterChange("role", role);
  };

  const handleStatusFilter = (status) => {
    onFilterChange("isActive", status);
  };

  /* ---------------- CRUD ---------------- */
  const handleSaveUser = async (data) => {
    try {
      if (modalState.mode === "create") {
        const response = await createUser(data);
        if (!response?.success) {
          throw new Error(response?.message);
        }
        toast.success(response.message);
      } else {
        const userId = modalState.user?.id || modalState.user?._id;
        const response = await updateUserByAdmin(userId, data);
        if (!response?.success) {
          throw new Error(response?.message);
        }
        toast.success(response.message);
      }
      setModalState({ isOpen: false, mode: "view", user: null });
      refetch();
    } catch (e) {
      console.error("Save user error:", e);
      throw e;
    }
  };

  const handleSaveExpert = async (data) => {
    try {
      if (expertModalState.mode === "create") {
        const response = await createUser(data);
        if (!response?.success) {
          throw new Error(response?.message);
        }
        toast.success(response.message);
      } else {
        const expertId =
          expertModalState.expert?.id || expertModalState.expert?._id;
        const response = await updateUserByAdmin(expertId, data);
        if (!response?.success) {
          throw new Error(response?.message);
        }
        toast.success(response.message);
      }
      setExpertModalState({ isOpen: false, mode: "create", expert: null });
      refetch();
    } catch (e) {
      console.error("Save expert error:", e);
      throw e;
    }
  };

  const handleSaveCustomerAdmin = async (data) => {
    try {
      if (customerModalAdminState.mode === "create") {
        const response = await createUser(data);
        if (!response?.success) {
          throw new Error(response?.message);
        }
        toast.success(response.message);
      } else {
        const customerId =
          customerModalAdminState.customer?.id ||
          customerModalAdminState.customer?._id;
        const response = await updateUserByAdmin(customerId, data);
        if (!response?.success) {
          throw new Error(response?.message);
        }
        toast.success(response.message);
      }
      setCustomerModalAdminState({
        isOpen: false,
        mode: "create",
        customer: null,
      });
      refetch();
    } catch (e) {
      console.error("Save customer admin error:", e);
      throw e;
    }
  };

  const handleDeleteUser = async () => {
    try {
      const userId = deleteModalState.user?.id || deleteModalState.user?._id;

      if (!userId) {
        toast.error("User ID not found. Cannot delete user.");
        console.error("User object:", deleteModalState.user);
        return;
      }

      const response = await deleteUser(userId);
      if (!response?.success) {
        throw new Error(response?.message);
      }
      toast.success("User deleted successfully");
      setDeleteModalState({ isOpen: false, user: null });
      refetch();
    } catch (e) {
      toast.error(e.message);
      console.error("Delete user error:", e);
      throw e;
    }
  };

  const handleToggleStatus = async (row) => {
    try {
      const userId = row?.id || row?._id;

      if (!userId) {
        toast.error("User ID not found. Cannot toggle status.");
        return;
      }

      const response = await toggleUserStatus(userId);
      toast.success(response.message);
      refetch();
    } catch (e) {
      toast.error(e.message);
      console.error("Toggle status error:", e);
      throw e;
    }
  };

  /* ---------------- TABLE CONFIG ---------------- */
  const columns = [
    {
      key: "name",
      label: "Name",
      sortable: true,
      render: (value, row) => (
        <div className="max-w-60">
          <UserMiniCard
            name={value}
            email={row.email}
            avatar={row.avatar}
            isEmailVerified={row.isEmailVerified}
          />
        </div>
      ),
    },
    {
      key: "phone",
      label: "Phone",
      sortable: false,
      render: (value) => <PhoneDisplay value={value} />,
    },
    {
      key: "role",
      label: "Role",
      sortable: true,
      render: (v) => <CustomBadge role={v} />,
    },
    isCustomerAdmin(user.role) && {
      key: "designation",
      label: "Designation",
      sortable: true,
      render: (v) => <CustomBadge role={v} label={v} />,
    },
    {
      key: "isActive",
      label: "Status",
      sortable: false,
      render: (v) => <CustomBadge isActive={v} />,
    },
    (isAdmin(user.role) || isCustomerAdmin(user.role)) && {
      key: "createdBy",
      label: "Created By",
      sortable: false,
      render: (value, row) => {
        if (row.createdBy.type === "self") {
          return <UserMiniCard isSelf />;
        }

        if (row.createdBy?.user) {
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
  ].filter(Boolean);

  const renderActions = (row) => {
    const roleLabel = getRoleLabel(row.role);

    const actions = [
      isAdmin(user.role) && {
        id: `view-${row.id || row._id}`,
        label: `View ${roleLabel}`,
        icon: "eye",
        onClick: () => navigate(`/profiles/${row.id || row._id}`),
      },
      {
        id: `edit-${row.id || row._id}`,
        label: `Edit ${roleLabel}`,
        icon: "edit",
        disabled: !row.isActive,
        onClick: () => {
          if (isExpert(row.role)) {
            setExpertModalState({ isOpen: true, mode: "update", expert: row });
          } else if (isCustomerAdmin(row.role)) {
            setCustomerModalAdminState({
              isOpen: true,
              mode: "update",
              customer: row,
            });
          } else {
            setModalState({ isOpen: true, mode: "edit", user: row });
          }
        },
      },
      {
        id: `toggle-${row.id || row._id}`,
        label: row.isActive
          ? `Deactivate ${roleLabel}`
          : `Activate ${roleLabel}`,
        icon: "power",
        onClick: () => handleToggleStatus(row),
      },

      {
        id: `delete-${row.id || row._id}`,
        label: `Delete ${roleLabel}`,
        icon: "trash",
        variant: "destructive",
        onClick: () => setDeleteModalState({ isOpen: true, user: row }),
      },
    ].filter(Boolean);

    return (
      <div className="flex justify-center">
        <ActionDropdown actions={actions} />
      </div>
    );
  };

  const getHeaderActions = () => {
    const urlParams = new URLSearchParams(globalThis.location.search);
    const roleFilter = urlParams.get("role") || "";
    const statusFilter = urlParams.get("isActive") || "";

    return [
      isCustomerAdmin(user.role) && {
        type: "dropdown",
        label: getRoleFilterLabel(roleFilter),
        triggerClassName: "w-fit",
        options: [
          { label: "All Roles", onClick: () => handleRoleFilter("") },
          {
            label: ROLE_LABELS[ROLE_INTERNAL_EXPERT],
            onClick: () => handleRoleFilter(ROLE_INTERNAL_EXPERT),
            separatorBefore: true,
          },
          {
            label: ROLE_LABELS[ROLE_USER],
            onClick: () => handleRoleFilter(ROLE_USER),
          },
          {
            label: ROLE_LABELS[ROLE_AUDITOR],
            onClick: () => handleRoleFilter(ROLE_AUDITOR),
          },
        ],
      },
      isAdmin(user.role) && {
        type: "dropdown",
        label: getRoleFilterLabel(roleFilter),
        triggerClassName: "w-fit",
        options: [
          { label: "All Roles", onClick: () => handleRoleFilter("") },
          {
            label: ROLE_LABELS[ROLE_INTERNAL_EXPERT],
            onClick: () => handleRoleFilter(ROLE_INTERNAL_EXPERT),
            separatorBefore: true,
          },
          {
            label: ROLE_LABELS[ROLE_USER],
            onClick: () => handleRoleFilter(ROLE_USER),
          },
          {
            label: ROLE_LABELS[ROLE_AUDITOR],
            onClick: () => handleRoleFilter(ROLE_AUDITOR),
          },
          {
            label: ROLE_LABELS[ROLE_EXPERT],
            onClick: () => handleRoleFilter(ROLE_EXPERT),
          },
        ],
      },
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
      isAdmin(user.role) && [
        {
          type: "button",
          label: "Create Expert",
          icon: "plus",
          onClick: () =>
            setExpertModalState({
              isOpen: true,
              mode: "create",
              expert: null,
            }),
        },
      ],
      isCustomerAdmin(user.role) && {
        type: "button",
        label: "Add Profile",
        icon: "plus",
        onClick: () =>
          setModalState({ isOpen: true, mode: "create", user: null }),
      },
    ]
      .flat()
      .filter(Boolean);
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="my-2">
      {/* Data Table */}
      <DataTable
        entityName="Users"
        columns={columns}
        data={users}
        loading={loading}
        onSearch={handleSearch}
        onSort={handleSort}
        sortConfig={sortConfig}
        searchTerm={searchTerm}
        pagination={pagination}
        renderActions={renderActions}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search users by name, email, or phone..."
        emptyMessage={emptyMessage}
      />

      {/* User Modal */}
      {modalState.isOpen && (
        <UserModal
          open={modalState.isOpen}
          onOpenChange={(open) => {
            if (!open) {
              setModalState({ isOpen: false, mode: "view", user: null });
            }
          }}
          mode={modalState.mode}
          user={modalState.user}
          onSave={handleSaveUser}
        />
      )}

      {/* Expert Modal */}
      {expertModalState.isOpen && (
        <ExpertModal
          open={expertModalState.isOpen}
          onOpenChange={(open) => {
            if (!open) {
              setExpertModalState({
                isOpen: false,
                mode: "create",
                expert: null,
              });
            }
          }}
          mode={expertModalState.mode}
          expert={expertModalState.expert}
          onSave={handleSaveExpert}
        />
      )}

      {/* Customer Modal */}
      {customerModalAdminState.isOpen && (
        <CustomerAdminModal
          open={customerModalAdminState.isOpen}
          onOpenChange={(open) => {
            if (!open) {
              setCustomerModalAdminState({
                isOpen: false,
                mode: "create",
                customer: null,
              });
            }
          }}
          mode={customerModalAdminState.mode}
          customer={customerModalAdminState.customer}
          onSave={handleSaveCustomerAdmin}
        />
      )}

      {/* Delete User Modal */}
      {deleteModalState.isOpen && deleteModalState.user && (
        <DeleteUserModal
          open={deleteModalState.isOpen}
          onCancel={() => setDeleteModalState({ isOpen: false, user: null })}
          onConfirm={handleDeleteUser}
          user={deleteModalState.user}
        />
      )}
    </div>
  );
}

export default Profiles;
