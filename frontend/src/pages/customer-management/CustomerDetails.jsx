import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import CustomBadge from "@/components/custom/CustomBadge";
import UserMiniCard from "@/components/custom/UserMiniCard";
import PhoneDisplay from "@/components/custom/PhoneDisplay";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import { Button } from "@/components/ui/button";
import {
  getCustomerById,
  updateCustomer,
  toggleCustomerStatus,
} from "@/services/customerService";
import {
  createUser,
  deleteUser,
  uploadCustomerAvatarById,
} from "@/services/userService";
import CustomerUserModal from "@/pages/customer-management/components/CustomerUserModal";
import CustomerManageModal from "@/pages/customer-management/components/CustomerManageModal";
import { DeleteUserModal } from "@/components/custom/modal";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import { usePageTitle } from "@/hooks/usePageTitle";
import DataTable from "@/components/data-table/DataTable";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import UserAvatar from "@/components/custom/UserAvatar";
import { isAdmin } from "@/utils/commonUtils";
import { useAuth } from "@/context/authContext/useAuth";

const renderAddressField = (value) => value || "N/A";

export default function CustomerDetails() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [customer, setCustomer] = useState(null);
  const [error, setError] = useState(null);
  const [createAdminOpen, setCreateAdminOpen] = useState(false);
  const [updateCustomerOpen, setUpdateCustomerOpen] = useState(false);
  const [deleteModalState, setDeleteModalState] = useState({
    isOpen: false,
    user: null,
  });

  // Reusable hook to handle the dynamic breadcrumb/header title
  usePageTitle(id, "Customer Details");

  const fetchCustomerAndUsers = useCallback(
    async (params) => {
      const response = await getCustomerById(id, params);
      if (response?.success) {
        setCustomer(response.data);
        setError(null);
        return {
          data: response.data.users?.data || [],
          pagination: response.data.users?.pagination || {},
          message: response.message,
        };
      }
      throw new Error(response?.message || "Failed to load customer details.");
    },
    [id]
  );

  const handleError = useCallback((err) => {
    setError(
      err?.message || "An error occurred while fetching customer details."
    );
  }, []);

  const {
    data: usersData,
    loading,
    error: tableError,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onSearch: handleSearch,
    onSort: handleSort,
    refetch: fetchCustomerDetails,
  } = useTableData(fetchCustomerAndUsers, {
    defaultLimit: 5,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No users found",
    onError: handleError,
  });

  const handleCopyTenantId = (tenantId) => {
    if (!tenantId) return;
    navigator.clipboard.writeText(tenantId);
    toast.success("Tenant ID copied to clipboard!");
  };

  const handleSaveCustomerUser = async (data) => {
    try {
      const response = await createUser(data);
      if (!response?.success) {
        throw new Error(response?.message || "Failed to create user");
      }
      toast.success(response.message || "User created successfully");
      setCreateAdminOpen(false);
      fetchCustomerDetails();
    } catch (e) {
      console.error("Save user error:", e);
      throw e;
    }
  };

  const handleDeleteUser = async () => {
    try {
      const userId = deleteModalState.user?.id || deleteModalState.user?._id;

      if (!userId) {
        toast.error("User ID not found. Cannot delete user.");
        return;
      }

      const response = await deleteUser(userId);
      if (!response?.success) {
        throw new Error(response?.message || "Failed to delete user");
      }
      toast.success("User deleted successfully");
      setDeleteModalState({ isOpen: false, user: null });
      fetchCustomerDetails();
    } catch (e) {
      toast.error(e.message || "Failed to delete user");
      console.error("Delete user error:", e);
      throw e;
    }
  };

  const handleUpdateCustomer = async (data) => {
    try {
      const response = await updateCustomer(id, data);
      if (!response?.success) {
        throw new Error(response?.message || "Failed to update customer");
      }
      toast.success(response.message || "Customer updated successfully");
      setUpdateCustomerOpen(false);
      fetchCustomerDetails();
    } catch (e) {
      console.error("Update customer error:", e);
      throw e;
    }
  };

  const handleToggleStatus = async () => {
    try {
      const response = await toggleCustomerStatus(id);
      toast.success(response.message || "Customer status updated successfully");
      fetchCustomerDetails();
    } catch (e) {
      toast.error(e.message || "Failed to toggle customer status");
      console.error("Toggle status error:", e);
    }
  };

  if (loading && !customer) {
    return <LoadingSpinner className="min-h-[calc(100vh-150px)]" />;
  }

  if (error || !customer) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-150px)]">
        <div className="text-center p-8 rounded border border-border bg-card shadow-2xl max-w-md w-full">
          <div className="w-16 h-16 bg-red-500/10 rounded flex items-center justify-center mx-auto mb-4">
            <Icon name="error" size="36px" className="text-red-500" />
          </div>
          <h2 className="text-lg font-bold mb-2">Error Loading Details</h2>
          <p className="text-sm text-muted-foreground mb-6">
            {error || "We couldn't retrieve the details for this customer."}
          </p>
          <div className="flex gap-3">
            <Button
              onClick={() => navigate("/customers")}
              variant="outline"
              className="flex-1 gap-2"
            >
              <Icon name="arrow-left" size="16px" />
              Back
            </Button>
            <Button
              onClick={fetchCustomerDetails}
              variant="primary"
              className="flex-1 gap-2"
            >
              <Icon name="refresh" size="16px" />
              Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const columns = [
    {
      key: "name",
      label: "User",
      sortable: true,
      render: (value, row) => (
        <UserMiniCard
          name={value}
          email={row.email}
          avatar={row.avatar}
          isEmailVerified={row.isEmailVerified}
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
      key: "role",
      label: "Role",
      sortable: false,
      render: (v) => <CustomBadge role={v} />,
    },
    {
      key: "isActive",
      label: "Status",
      sortable: false,
      render: (v) => <CustomBadge isActive={v} />,
    },
    {
      key: "createdAt",
      label: "Created On",
      sortable: true,
      render: (v) => formatDateWithMonthNameAndTime(v),
    },
  ];

  const renderActions = (row) => (
    <div className="flex justify-center">
      <Button
        variant="ghost"
        size="icon"
        disabled={!customer.isActive}
        onClick={() => setDeleteModalState({ isOpen: true, user: row })}
        className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
        title={
          customer.isActive
            ? "Delete User"
            : "Cannot delete user of inactive customer"
        }
      >
        <Icon name="trash" size="14px" />
      </Button>
    </div>
  );

  const getHeaderActions = () => {
    return [
      {
        type: "button",
        label: "Create User",
        icon: "plus",
        disabled: !customer.isActive,
        onClick: () => setCreateAdminOpen(true),
      },
    ].filter(Boolean);
  };

  return (
    <div className="space-y-4 my-2">
      {/* Customer Header Card */}
      <div className="relative group">
        <div className="absolute -inset-1 bg-linear-to-r from-primary/20 to-primary/10 rounded blur-xl opacity-20 group-hover:opacity-30 transition"></div>
        <div className="relative rounded border border-border bg-card shadow-xl overflow-hidden">
          {/* Header Band with Buttons */}
          <div className="h-24 bg-linear-to-r from-primary to-primary/80 relative overflow-hidden">
            {/* Abstract design elements */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded -translate-y-1/2 translate-x-1/2 blur-3xl"></div>
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-black/10 rounded translate-y-1/2 -translate-x-1/2 blur-2xl"></div>

            <div className="absolute inset-0 bg-linear-to-b from-transparent to-black/30"></div>

            {/* Action Buttons on Header */}
            <div className="absolute top-4 right-4 flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setUpdateCustomerOpen(true)}
                disabled={!customer.isActive}
                className="gap-2 text-white hover:text-primary bg-white/10"
              >
                <Icon name="edit" size="16px" className="mr-1" />
                Update Customer
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleToggleStatus}
                className="gap-2 text-white hover:text-primary bg-white/10"
              >
                <Icon name="power" size="16px" className="mr-1" />
                {customer.isActive ? "Deactivate" : "Activate"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => navigate("/customers")}
                className="gap-2 text-white hover:text-primary bg-white/10"
              >
                <Icon name="arrow-left" size="16px" className="mr-1" />
                Back
              </Button>
            </div>
          </div>

          {/* Profile Core Info Row */}
          <div className="px-6 pb-6">
            <div className="relative flex flex-col md:flex-row md:items-end gap-4 -mt-10">
              {/* Avatar with border */}
              <div className="relative p-1.5 bg-card rounded shadow-xl border border-border/50">
                <UserAvatar
                  user={customer}
                  size="4xl"
                  className="rounded"
                  editable={isAdmin(user?.role)}
                  uploadFn={
                    isAdmin(user?.role)
                      ? (file) => uploadCustomerAvatarById(file, id)
                      : undefined
                  }
                  onUploaded={
                    isAdmin(user?.role) ? fetchCustomerAndUsers : undefined
                  }
                />
              </div>

              <div className="flex-1 pb-1">
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <h1 className="text-2xl font-extrabold text-foreground tracking-tight">
                    {customer.name}
                  </h1>
                  <CustomBadge isActive={customer.isActive} />
                </div>

                <div className="flex flex-wrap gap-y-1.5 gap-x-4 text-sm">
                  <span className="flex items-center gap-2 text-muted-foreground font-medium">
                    <Icon name="mail" size="14px" className="text-primary/70" />
                    {customer.email}
                  </span>
                  <span className="flex items-center gap-2 text-muted-foreground font-medium">
                    <Icon
                      name="phone"
                      size="14px"
                      className="text-primary/70"
                    />
                    <PhoneDisplay value={customer.phone} />
                  </span>
                  <span className="flex items-center gap-2 text-muted-foreground font-medium">
                    <Icon
                      name="calendar"
                      size="14px"
                      className="text-primary/70"
                    />
                    Registered{" "}
                    {formatDateWithMonthNameAndTime(
                      customer.createdAt,
                      "MMM YYYY"
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left column: Address & Users */}
        <div className="lg:col-span-2 space-y-4">
          {/* Addresses Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Permanent Address */}
            <div className="p-4 rounded border border-border bg-card shadow-lg relative overflow-hidden border-l-4 border-l-primary/80">
              <div className="flex items-center gap-2 mb-4 pb-2 border-b border-border/40">
                <div className="p-1 rounded bg-primary/10 text-primary flex items-center justify-center">
                  <Icon name="home" size="16px" />
                </div>
                <h3 className="font-bold text-foreground">Permanent Address</h3>
              </div>
              <div className="space-y-2.5 text-sm">
                <div>
                  <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                    Locality
                  </span>
                  <span className="font-semibold text-foreground wrap-break-words">
                    {renderAddressField(
                      customer.address?.permanentAddress?.locality
                    )}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                      City
                    </span>
                    <span className="font-semibold text-foreground truncate block">
                      {renderAddressField(
                        customer.address?.permanentAddress?.city
                      )}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                      State
                    </span>
                    <span className="font-semibold text-foreground truncate block">
                      {renderAddressField(
                        customer.address?.permanentAddress?.state
                      )}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                      Country
                    </span>
                    <span className="font-semibold text-foreground truncate block">
                      {renderAddressField(
                        customer.address?.permanentAddress?.country
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Temporary Address */}
            <div className="p-4 rounded border border-border bg-card shadow-lg relative overflow-hidden border-l-4 border-l-primary/80">
              <div className="flex items-center gap-2 mb-4 pb-2 border-b border-border/40">
                <div className="p-1 rounded bg-primary/10 text-primary flex items-center justify-center">
                  <Icon name="building" size="16px" />
                </div>
                <h3 className="font-bold text-foreground">Temporary Address</h3>
              </div>
              <div className="space-y-2.5 text-sm">
                <div>
                  <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                    Locality
                  </span>
                  <span className="font-semibold text-foreground wrap-break-words">
                    {renderAddressField(
                      customer.address?.temporaryAddress?.locality
                    )}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                      City
                    </span>
                    <span className="font-semibold text-foreground truncate block">
                      {renderAddressField(
                        customer.address?.temporaryAddress?.city
                      )}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                      State
                    </span>
                    <span className="font-semibold text-foreground truncate block">
                      {renderAddressField(
                        customer.address?.temporaryAddress?.state
                      )}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                      Country
                    </span>
                    <span className="font-semibold text-foreground truncate block">
                      {renderAddressField(
                        customer.address?.temporaryAddress?.country
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Associated Users Table Card */}
          <div className="rounded border border-border bg-card shadow-xl overflow-hidden border-t-4 border-t-primary/80">
            <div className="p-4 border-b border-border bg-muted/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="p-1 rounded bg-primary/10 text-primary flex items-center justify-center">
                  <Icon name="users" size="16px" />
                </div>
                <h3 className="font-extrabold text-foreground">
                  Associated Tenant Users ({pagination?.totalItems || 0})
                </h3>
              </div>
            </div>

            <DataTable
              entityName="Users"
              columns={columns}
              data={usersData}
              loading={loading}
              onSearch={handleSearch}
              onSort={handleSort}
              sortConfig={sortConfig}
              searchTerm={searchTerm}
              pagination={pagination}
              searchPlaceholder="Search users by name and email..."
              emptyMessage={emptyMessage}
              renderActions={renderActions}
              headerActions={getHeaderActions()}
              error={tableError}
            />
          </div>
        </div>

        {/* Right column: Sidebar Info */}
        <div className="space-y-4">
          {/* Tenant Details Card */}
          <div className="p-4 rounded border border-border bg-card shadow-lg relative overflow-hidden border-l-4 border-l-primary/80">
            <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-4 pb-1 border-b border-border/40">
              Tenant Administration
            </h4>

            <div className="space-y-4 text-sm">
              {/* Tenant ID block */}
              <div>
                <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70 mb-1">
                  Tenant ID
                </span>
                <div className="flex items-center justify-between p-2 rounded bg-muted/30 border border-border/60">
                  <code className="text-xs font-bold text-primary mr-2 select-all uppercase">
                    {customer.tenantId}
                  </code>
                  <button
                    type="button"
                    onClick={() => handleCopyTenantId(customer.tenantId)}
                    className="p-1 rounded text-muted-foreground hover:text-primary hover:bg-muted transition cursor-pointer"
                    title="Copy Tenant ID"
                  >
                    <Icon name="copy" size="14px" />
                  </button>
                </div>
              </div>

              {/* Secondary Phone if available */}
              {customer.secondaryPhone && (
                <div>
                  <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70 mb-0.5">
                    Secondary Phone
                  </span>
                  <span className="font-semibold text-foreground">
                    <PhoneDisplay value={customer.secondaryPhone} />
                  </span>
                </div>
              )}

              {/* Created By details */}
              {customer.createdBy?.userId && (
                <div className="pt-3 border-t border-border/40">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70 mb-2">
                    Registered By Authority
                  </span>
                  <div className="p-2 rounded bg-muted/10 border border-border/30">
                    <UserMiniCard
                      name={customer.createdBy.userId.name}
                      email={customer.createdBy.userId.email}
                      avatar={customer.createdBy.userId.avatar}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Audit / Timeline Card */}
          <div className="p-4 rounded border border-border bg-card shadow-lg relative overflow-hidden border-l-4 border-l-primary/80">
            <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-3 pb-1 border-b border-border/40">
              System Logs & History
            </h4>

            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-green-500/10 text-green-600 flex items-center justify-center shrink-0">
                  <Icon name="calendar" size="14px" />
                </div>
                <div className="min-w-0">
                  <span className="text-[9px] uppercase font-bold text-muted-foreground tracking-tighter block leading-none">
                    Created On
                  </span>
                  <span className="text-xs font-semibold text-foreground truncate block">
                    {formatDateWithMonthNameAndTime(customer.createdAt)}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-blue-500/10 text-blue-600 flex items-center justify-center shrink-0">
                  <Icon name="refresh" size="14px" />
                </div>
                <div className="min-w-0">
                  <span className="text-[9px] uppercase font-bold text-muted-foreground tracking-tighter block leading-none">
                    Last Dynamic Sync
                  </span>
                  <span className="text-xs font-semibold text-foreground truncate block">
                    {formatDateWithMonthNameAndTime(customer.updatedAt)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {createAdminOpen && (
        <CustomerUserModal
          open={createAdminOpen}
          onOpenChange={setCreateAdminOpen}
          mode="create"
          customer={customer}
          onSave={handleSaveCustomerUser}
        />
      )}

      {updateCustomerOpen && (
        <CustomerManageModal
          open={updateCustomerOpen}
          onOpenChange={setUpdateCustomerOpen}
          mode="update"
          customer={customer}
          onSave={handleUpdateCustomer}
        />
      )}

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
