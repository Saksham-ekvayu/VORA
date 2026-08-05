import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";
import CustomBadge from "@/components/custom/CustomBadge";
import UserMiniCard from "@/components/custom/UserMiniCard";
import PhoneDisplay from "@/components/custom/PhoneDisplay";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import { Button } from "@/components/ui/button";
import { DeleteUserModal } from "@/components/custom/modal";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import {
  getUserById,
  toggleUserStatus,
  deleteUser,
} from "@/services/userService";
import { getFrameworkAccessByUserId } from "@/services/adminService";
import DataTable from "@/components/data-table/DataTable";
import { useTableData } from "@/components/data-table/hooks/useTableData";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";
import {
  getAccessStatusFilterLabel,
  isExpert,
  STATUS_APPROVED,
  STATUS_PENDING,
  STATUS_REJECTED,
  STATUS_REVOKED,
} from "@/utils/commonUtils";
import UserAvatar from "@/components/custom/UserAvatar";
import { usePageTitle } from "@/hooks/usePageTitle";

const renderField = (value) => value || "N/A";

export default function UserDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  // Reusable hook to handle the dynamic breadcrumb/header title
  usePageTitle(id, "Profile Details");

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [togglingStatus, setTogglingStatus] = useState(false);
  const [deleteModalState, setDeleteModalState] = useState({
    isOpen: false,
    user: null,
  });

  // Stable curried fetcher — recreated only when id changes
  const frameworkAccessFetcher = useMemo(
    () => getFrameworkAccessByUserId(id),
    [id]
  );

  const {
    data: accessRecords,
    loading: accessLoading,
    emptyMessage: accessEmptyMessage,
    pagination: accessPagination,
    searchTerm: accessSearchTerm,
    sortConfig: accessSortConfig,
    onSearch: handleAccessSearch,
    onSort: handleAccessSort,
    onFilterChange: handleAccessFilterChange,
  } = useTableData(frameworkAccessFetcher, {
    defaultLimit: 5,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No framework access records found for this user.",
  });

  const fetchUserDetails = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getUserById(id);
      if (response?.success) {
        setUser(response.data);
      } else {
        setError(response?.message || "Failed to load user details.");
      }
    } catch (err) {
      console.error("Error fetching user:", err);
      setError(
        err?.message || "An error occurred while fetching user details."
      );
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (id) fetchUserDetails();
  }, [id, fetchUserDetails]);

  const handleToggleStatus = async () => {
    setTogglingStatus(true);
    try {
      const response = await toggleUserStatus(id);
      toast.success(response?.message || "User status updated successfully");
      fetchUserDetails();
    } catch (e) {
      toast.error(e?.message || "Failed to toggle user status");
    } finally {
      setTogglingStatus(false);
    }
  };

  const handleDeleteUser = async () => {
    try {
      const response = await deleteUser(id);
      if (!response?.success)
        throw new Error(response?.message || "Failed to delete user");
      toast.success(response?.message || "User deleted successfully");
      setDeleteModalState({ isOpen: false, user: null });
      navigate(-1);
    } catch (e) {
      toast.error(e?.message || "Failed to delete user");
      throw e;
    }
  };

  const handleStatusFilter = (status) =>
    handleAccessFilterChange("status", status);

  /* ─── Framework Access Table config ─── */
  const accessColumns = [
    {
      key: "frameworkCategory.frameworkCode",
      label: "Framework Code",
      sortable: false,
      render: (_, row) => (
        <span className="font-mono text-sm bg-muted px-2 py-1 rounded uppercase">
          {row.frameworkCategory?.frameworkCode ?? "—"}
        </span>
      ),
    },
    {
      key: "frameworkCategory.frameworkCategoryName",
      label: "Framework",
      sortable: false,
      render: (_, row) => (
        <FrameworkMiniCard
          name={row.frameworkCategory?.frameworkCategoryName}
          description={row.frameworkCategory?.description}
        />
      ),
    },
    {
      key: "status",
      label: "Status",
      sortable: true,
      render: (value) => <CustomBadge status={value} />,
    },
    {
      key: "createdAt",
      label: "Requested On",
      sortable: true,
      render: (value) => (
        <span className="text-xs whitespace-nowrap">
          {formatDateWithMonthNameAndTime(value)}
        </span>
      ),
    },
  ];

  const getAccessHeaderActions = () => {
    const urlParams = new URLSearchParams(globalThis.location.search);
    const statusFilter = urlParams.get("status") || "";
    return [
      {
        type: "dropdown",
        label: getAccessStatusFilterLabel(statusFilter),
        triggerClassName: "w-fit",
        options: [
          { label: "All Status", onClick: () => handleStatusFilter("") },
          {
            label: "Pending",
            onClick: () => handleStatusFilter(STATUS_PENDING),
            separatorBefore: true,
          },
          {
            label: "Approved",
            onClick: () => handleStatusFilter(STATUS_APPROVED),
          },
          {
            label: "Rejected",
            onClick: () => handleStatusFilter(STATUS_REJECTED),
          },
          {
            label: "Revoked",
            onClick: () => handleStatusFilter(STATUS_REVOKED),
          },
        ],
      },
    ];
  };

  /* ─── LOADING ─── */
  if (loading) return <LoadingSpinner className="min-h-[calc(100vh-150px)]" />;

  /* ─── ERROR ─── */
  if (error || !user) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-150px)]">
        <div className="text-center p-8 rounded border border-border bg-card shadow-2xl max-w-md w-full">
          <div className="w-16 h-16 bg-red-500/10 rounded flex items-center justify-center mx-auto mb-4">
            <Icon name="error" size="36px" className="text-red-500" />
          </div>
          <h2 className="text-lg font-bold mb-2">Error Loading Details</h2>
          <p className="text-sm text-muted-foreground mb-6">
            {error || "We couldn't retrieve the details for this user."}
          </p>
          <div className="flex gap-3">
            <Button
              onClick={() => navigate(-1)}
              variant="outline"
              className="flex-1 gap-2"
            >
              <Icon name="arrow-left" size="16px" /> Back
            </Button>
            <Button
              onClick={fetchUserDetails}
              variant="primary"
              className="flex-1 gap-2"
            >
              <Icon name="refresh" size="16px" /> Retry
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const displayAddress = ["expert", "admin"].includes(user.role)
    ? user.address
    : user.customer?.address;

  return (
    <div className="space-y-4 my-2">
      {/* ─── HEADER CARD ─── */}
      <div className="relative group">
        <div className="absolute -inset-1 bg-linear-to-r from-primary/20 to-primary/10 rounded blur-xl opacity-20 group-hover:opacity-30 transition" />
        <div className="relative rounded border border-border bg-card shadow-xl overflow-hidden">
          <div className="h-16 bg-linear-to-r from-primary to-primary/80 relative overflow-hidden flex items-center justify-end px-4">
            <div className="space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleToggleStatus}
                disabled={togglingStatus}
                className="gap-2 text-white hover:text-primary bg-white/10 relative z-10"
              >
                <Icon name="power" size="14px" />
                {togglingStatus && "Updating..."}
                {!togglingStatus &&
                  (user.isActive ? "Deactivate User" : "Activate User")}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDeleteModalState({ isOpen: true, user })}
                className="gap-2 text-white hover:text-primary bg-white/10 relative z-10"
              >
                <Icon name="trash" size="14px" /> Delete User
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(-1)}
                className="gap-2 text-white hover:text-primary bg-white/10 relative z-10"
              >
                <Icon name="arrow-left" size="14px" /> Back
              </Button>
            </div>
            <div className="absolute top-0 right-0 w-48 h-48 bg-white/5 rounded-full -translate-y-1/3 translate-x-1/3 blur-2xl" />
          </div>

          <div className="px-6 pb-6 -mt-6">
            <div className="flex flex-col md:flex-row md:items-end gap-4">
              <div className="relative p-1.5 bg-card rounded shadow-xl border border-border/50 shrink-0">
                <UserAvatar user={user} size="3xl" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-3 mb-1.5">
                  <h1 className="text-2xl font-extrabold text-foreground tracking-tight truncate">
                    {user.name}
                  </h1>
                  <CustomBadge isActive={user.isActive} />
                  <CustomBadge role={user.role} />
                  {user.isEmailVerified && (
                    <CustomBadge label="Verified" color="blue" />
                  )}
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted-foreground font-medium">
                  <span className="flex items-center gap-1.5">
                    <Icon
                      name="email"
                      size="12px"
                      className="text-primary/70"
                    />
                    {user.email}
                  </span>
                  {user.phone && (
                    <span className="flex items-center gap-1.5">
                      <Icon
                        name="phone"
                        size="12px"
                        className="text-primary/70"
                      />
                      <PhoneDisplay value={user.phone} />
                    </span>
                  )}
                  {user.designation && (
                    <span className="flex items-center gap-1.5">
                      <Icon
                        name="briefcase"
                        size="12px"
                        className="text-primary/70"
                      />
                      {user.designation}
                    </span>
                  )}
                  <span className="flex items-center gap-1.5">
                    <Icon
                      name="calendar"
                      size="12px"
                      className="text-primary/70"
                    />
                    Joined {formatDateWithMonthNameAndTime(user.createdAt)}
                  </span>
                </div>
              </div>

              {user.createdBy?.user?.id && (
                <div className="shrink-0 self-center md:self-end">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                    Registered By
                  </span>
                  <div className="rounded bg-muted/10 border border-border/30">
                    <UserMiniCard
                      name={user.createdBy.user.name}
                      email={user.createdBy.user.email}
                      avatar={user.createdBy.user.avatar}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ─── MAIN GRID ─── */}
      <div
        className={`grid ${isExpert(user.role) ? "grid-cols-4" : "grid-cols-3"} gap-4`}
      >
        {user.customer?.id && (
          <div className="p-4 rounded border border-border bg-card shadow-lg border-l-4 border-l-primary/80">
            <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-3 pb-1 border-b border-border/40">
              Customer Information
            </h4>
            <div className="space-y-3 text-sm">
              <div className="p-2 rounded bg-muted/10 border border-border/30">
                <UserMiniCard
                  name={user.customer.name}
                  email={user.customer.email}
                  avatar={user.customer.avatar}
                />
              </div>
              {user.customer.phone && (
                <div className="flex items-center gap-2 pt-1 text-xs font-semibold text-foreground">
                  <Icon name="phone" size="12px" className="text-primary/70" />
                  <PhoneDisplay value={user.customer.phone} />
                </div>
              )}
            </div>
          </div>
        )}

        <div className="p-4 rounded border border-border bg-card shadow-lg border-l-4 border-l-primary/80">
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
                {renderField(displayAddress?.permanentAddress?.locality)}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {["city", "state", "country"].map((field) => (
                <div key={field}>
                  <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                    {field}
                  </span>
                  <span className="font-semibold text-foreground truncate block">
                    {renderField(displayAddress?.permanentAddress?.[field])}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 rounded border border-border bg-card shadow-lg border-l-4 border-l-primary/80">
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
                {renderField(displayAddress?.temporaryAddress?.locality)}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {["city", "state", "country"].map((field) => (
                <div key={field}>
                  <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70">
                    {field}
                  </span>
                  <span className="font-semibold text-foreground truncate block">
                    {renderField(displayAddress?.temporaryAddress?.[field])}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 rounded border border-border bg-card shadow-lg border-l-4 border-l-primary/80">
          <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-4 pb-1 border-b border-border/40">
            Account Information
          </h4>
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70 mb-1">
                  Role
                </span>
                <CustomBadge role={user.role} />
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest block opacity-70 mb-1">
                  Designation
                </span>
                <span className="font-semibold text-foreground text-xs">
                  {renderField(user.designation)}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center ${user.isEmailVerified ? "bg-green-500/10 text-green-600" : "bg-yellow-500/10 text-yellow-600"}`}
              >
                <Icon
                  name={user.isEmailVerified ? "check" : "clock"}
                  size="12px"
                />
              </div>
              <span className="text-xs font-semibold text-foreground">
                Email {user.isEmailVerified ? "Verified" : "Not Verified"}
              </span>
            </div>
          </div>
        </div>

        <div className="p-4 rounded border border-border bg-card shadow-lg border-l-4 border-l-primary/80">
          <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-3 pb-1 border-b border-border/40">
            System Logs &amp; History
          </h4>
          <div className="space-y-3">
            {[
              {
                label: "Created On",
                date: user.createdAt,
                iconBg: "bg-green-500/10 text-green-600",
                icon: "calendar",
              },
              {
                label: "Last Updated",
                date: user.updatedAt,
                iconBg: "bg-blue-500/10 text-blue-600",
                icon: "refresh",
              },
            ].map(({ label, date, iconBg, icon }) => (
              <div key={label} className="flex items-center gap-3">
                <div
                  className={`w-8 h-8 rounded ${iconBg} flex items-center justify-center shrink-0`}
                >
                  <Icon name={icon} size="14px" />
                </div>
                <div className="min-w-0">
                  <span className="text-[9px] uppercase font-bold text-muted-foreground tracking-tighter block leading-none">
                    {label}
                  </span>
                  <span className="text-xs font-semibold text-foreground truncate block">
                    {formatDateWithMonthNameAndTime(date)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ─── Framework Access DataTable ─── */}
      {isExpert(user.role) && (
        <div className="rounded border border-border bg-card shadow-xl overflow-hidden border-t-4 border-t-primary/80 lg:col-span-3">
          <div className="p-4 border-b border-border bg-muted/10 flex items-center gap-2">
            <div className="p-1 rounded bg-primary/10 text-primary flex items-center justify-center">
              <Icon name="shield" size="16px" />
            </div>
            <h3 className="font-extrabold text-foreground">
              Framework Access Records
            </h3>
          </div>
          <DataTable
            entityName="Access Records"
            columns={accessColumns}
            data={accessRecords}
            loading={accessLoading}
            onSearch={handleAccessSearch}
            onSort={handleAccessSort}
            sortConfig={accessSortConfig}
            searchTerm={accessSearchTerm}
            pagination={accessPagination}
            headerActions={getAccessHeaderActions()}
            searchPlaceholder="Search framework code..."
            emptyMessage={accessEmptyMessage}
          />
        </div>
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
