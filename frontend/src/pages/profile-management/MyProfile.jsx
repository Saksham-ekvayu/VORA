/* eslint-disable react/prop-types */

import { useState } from "react";
import { useProfile } from "@/context/profileContext/useProfile";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import Icon from "@/components/custom/Icon";
import EditProfileModal from "./components/EditProfileModal";
import ChangePasswordModal from "./components/ChangePasswordModal";
import { Button } from "@/components/ui/button";
import UserAvatar from "@/components/custom/UserAvatar";
import CustomBadge from "@/components/custom/CustomBadge";
import { cn } from "@/lib/utils";
import LoadingSpinner from "@/components/custom/Loader/LoadingSpinner";
import {
  isAdmin,
  isCustomerAdmin,
  ROLE_ADMIN,
  ROLE_EXPERT,
} from "@/utils/commonUtils";
import { uploadCustomerAvatarOwn } from "@/services/userService";
import CustomerManageModal from "@/pages/customer-management/components/CustomerManageModal";
import { toast } from "sonner";
import { updateCustomer } from "@/services/customerService";

const renderAddressField = (value) => value || "N/A";

const getManagedByBadgeColor = (type) => (isAdmin(type) ? "red" : "blue");

const renderManagedByCard = (createdBy) => {
  if (
    !createdBy ||
    createdBy === "self" ||
    createdBy.type === "self" ||
    !createdBy.user
  )
    return null;

  return (
    <div className="p-4 rounded border border-border bg-card shadow-xl relative overflow-hidden border-l-4 border-l-primary/80">
      <div className="absolute top-0 right-0 p-4 opacity-5">
        <Icon name="shield" size="60px" />
      </div>

      <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
        <span className="w-6 h-px bg-primary/30"></span> Assigned Manager
      </h4>

      <div className="flex items-center gap-3 mb-4">
        <UserAvatar
          user={createdBy.user}
          size="xl"
          className="rounded shadow-lg"
        />
        <div className="flex flex-col gap-1">
          <p className="text-sm font-bold text-foreground leading-tight">
            {createdBy.user.name}
          </p>
          <CustomBadge
            label={createdBy.type}
            color={getManagedByBadgeColor(createdBy.type)}
            className="w-fit"
          />
        </div>
      </div>

      <div className="space-y-2.5 pt-2 border-t border-border/40">
        <div className="flex items-start gap-2.5">
          <Icon
            name="mail"
            size="14px"
            className="mt-0.5 text-muted-foreground"
          />
          <span className="text-xs font-medium text-muted-foreground break-all">
            {createdBy.user.email}
          </span>
        </div>
        <div className="flex items-center gap-2.5">
          <Icon name="shield" size="14px" className="text-muted-foreground" />
          <span className="text-xs font-bold text-muted-foreground/80 uppercase">
            Primary Authority
          </span>
        </div>
      </div>
    </div>
  );
};

const renderCustomerCard = (
  customer,
  role,
  onRefresh,
  setShowCustomerEditModal
) => {
  if (!customer) return null;

  return (
    <div className="p-4 rounded border border-border bg-card shadow-xl relative overflow-hidden border-l-4 border-l-primary/80">
      <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
        <Icon name="business" size="60px" />
      </div>

      <div className="flex items-center justify-between mb-4 relative z-10">
        <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em] flex items-center gap-2">
          <span className="w-6 h-px bg-primary/30"></span> Organization Profile
        </h4>
        {isCustomerAdmin(role) && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs px-2 gap-1 bg-background/50 hover:bg-background"
            onClick={() => setShowCustomerEditModal(true)}
          >
            <Icon name="edit" size="12px" />
            Edit Info
          </Button>
        )}
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="relative">
          <UserAvatar
            user={customer}
            size="2xl"
            editable={isCustomerAdmin(role)}
            uploadFn={
              isCustomerAdmin(role)
                ? (file) => uploadCustomerAvatarOwn(file)
                : undefined
            }
            onUploaded={isCustomerAdmin(role) ? onRefresh : undefined}
            className="rounded shadow-lg"
          />
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-sm font-bold text-foreground leading-tight">
            {customer.name}
          </p>
          <CustomBadge label="Organization" color="green" className="w-fit" />
        </div>
      </div>

      <div className="space-y-2.5 pt-2 border-t border-border/40">
        <div className="flex items-start gap-2.5">
          <Icon
            name="mail"
            size="14px"
            className="mt-0.5 text-muted-foreground"
          />
          <span className="text-xs font-medium text-muted-foreground break-all">
            {customer.email || "N/A"}
          </span>
        </div>

        <div className="flex items-center gap-2.5">
          <Icon name="phone" size="14px" className="text-muted-foreground" />
          <span className="text-xs font-medium text-muted-foreground">
            {customer.phone ? `+${customer.phone}` : "N/A"}
          </span>
        </div>

        {customer.secondaryPhone && (
          <div className="flex items-center gap-2.5">
            <Icon name="phone" size="14px" className="text-muted-foreground opacity-60" />
            <span className="text-xs font-medium text-muted-foreground">
              +{customer.secondaryPhone}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

function MyProfile() {
  const {
    profile: profileData,
    loading,
    fetchProfile: fetchProfileData,
  } = useProfile();
  const [showEditModal, setShowEditModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showCustomerEditModal, setShowCustomerEditModal] = useState(false);

  const handleUpdateCustomer = async (data) => {
    try {
      const customerId = profileData.customer?.id || profileData.customer?._id;
      const response = await updateCustomer(customerId, data);
      if (!response?.success) {
        throw new Error(response?.message || "Failed to update customer");
      }
      toast.success(response.message || "Organization updated successfully");
      fetchProfileData();
    } catch (e) {
      console.error("Update organization error:", e);
      throw e;
    }
  };

  if (loading) {
    return <LoadingSpinner className={"min-h-[calc(100vh-100px)]"} />;
  }

  if (!profileData) {
    return (
      <div className="flex items-center justify-center min-h-100">
        <div className="text-center p-8 rounded border border-border bg-card shadow-2xl max-w-md">
          <div className="w-20 h-20 bg-red-500/10 rounded flex items-center justify-center mx-auto mb-6">
            <Icon name="error" size="40px" className="text-red-500" />
          </div>
          <h2 className="text-xl font-bold mb-2">Profile Missing</h2>
          <p className="text-muted-foreground mb-6">
            We couldn't retrieve your profile information. This might be due to
            a connection issue.
          </p>
          <Button
            onClick={fetchProfileData}
            variant="primary"
            className="w-full gap-2"
          >
            <Icon name="refresh" size="18px" />
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  const displayAddress = [
    ROLE_EXPERT,
    ROLE_ADMIN,
  ].includes(profileData.role)
    ? profileData.address
    : profileData.customer?.address;

  return (
    <div className="space-y-2 my-2">
      {/* Premium Profile Header Card */}
      <div className="relative group">
        <div className="absolute -inset-1 bg-linear-to-r from-primary/30 to-primary-2/30 rounded blur-xl opacity-25 group-hover:opacity-40 transition"></div>
        <div className="relative rounded border border-border bg-card shadow-xl overflow-hidden">
          {/* Cover Art with Glassmorphism Overlay */}
          <div className="h-24 bg-linear-to-r from-primary to-primary-2 relative overflow-hidden">
            {/* Abstract design elements */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded -translate-y-1/2 translate-x-1/2 blur-3xl"></div>
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-black/10 rounded translate-y-1/2 -translate-x-1/2 blur-2xl"></div>

            <div className="absolute inset-0 bg-linear-to-b from-transparent to-black/30"></div>

            {/* Action Buttons on Header */}
            <div className="absolute top-4 right-4 flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowEditModal(true)}
              >
                <Icon name="edit" size="16px" className="mr-2" />
                Update Profile
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowPasswordModal(true)}
                className="border-primary/20 hover:border-primary text-primary hover:bg-primary/5"
              >
                <Icon name="key" size="16px" className="mr-2" />
                Change Password
              </Button>
            </div>
          </div>

          {/* Profile Core Info Row */}
          <div className="px-4 pb-4">
            <div className="relative flex flex-col md:flex-row md:items-end gap-4 -mt-10">
              {/* Avatar with status ring */}
              <div className="relative p-1.5 bg-card rounded shadow-xl border border-border/50">
                <UserAvatar
                  user={profileData}
                  size="4xl"
                  className="rounded text-3xl"
                  editable
                  onUploaded={fetchProfileData}
                />
              </div>

              <div className="flex-1 pb-1">
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <h1 className="text-2xl font-extrabold text-foreground tracking-tight">
                    {profileData.name}
                  </h1>
                  <CustomBadge
                    role={profileData.role}
                    size="sm"
                    className="uppercase tracking-widest"
                  />
                </div>

                <div className="flex flex-wrap gap-y-1.5 gap-x-4 text-sm">
                  <span className="flex items-center gap-2 text-muted-foreground font-medium">
                    <Icon name="mail" size="14px" className="text-primary/70" />
                    {profileData.email}
                  </span>
                  <span className="flex items-center gap-2 text-muted-foreground font-medium">
                    <Icon
                      name="phone"
                      size="14px"
                      className="text-primary/70"
                    />
                    +{profileData.phone}
                  </span>
                  <span className="flex items-center gap-2 text-muted-foreground font-medium">
                    <Icon
                      name="calendar"
                      size="14px"
                      className="text-primary/70"
                    />
                    Joined{" "}
                    {formatDateWithMonthNameAndTime(
                      profileData.createdAt,
                      "MMM YYYY"
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Profile Detail Grid */}
      <div className="grid lg:grid-cols-3 gap-2">
        {/* Main Info Columns */}
        <div className="lg:col-span-2 space-y-2">
          {/* Bio/Summary (If application has one) or Identity Section */}
          <div className="p-4 rounded border border-border bg-card shadow-xl border-l-4 border-l-primary/80">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-1.5 rounded bg-primary/10 text-primary flex items-center justify-center">
                <Icon name="user" size="18px" />
              </div>
              <h3 className="text-lg font-bold tracking-tight">
                Personal Identity
              </h3>
            </div>

            <div className="grid sm:grid-cols-12 gap-x-2 gap-y-4">
              <div className="group col-span-3">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  Display Name
                </p>
                <p className="text-base font-semibold text-foreground border-b border-transparent group-hover:border-primary/20 py-1">
                  {profileData.name}
                </p>
              </div>
              <div className="group col-span-4">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  Primary Email
                </p>
                <p className="text-base font-semibold text-foreground border-b border-transparent group-hover:border-primary/20 py-1 truncate">
                  {profileData.email}
                </p>
              </div>

              <div className="group col-span-2">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  Phone Number
                </p>
                <p className="text-base font-semibold text-foreground border-b border-transparent group-hover:border-primary/20 py-1">
                  {renderAddressField(
                    profileData.phone ? `+${profileData.phone}` : ""
                  )}
                </p>
              </div>
              <div className="group col-span-3">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  Secondary Phone Number
                </p>

                <p className="text-base font-semibold text-foreground border-b border-transparent group-hover:border-primary/20 py-1">
                  {renderAddressField(
                    profileData.secondaryPhone
                      ? `+${profileData.secondaryPhone}`
                      : ""
                  )}
                </p>
              </div>
              <div className="group col-span-3">
                <div className="group">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60"></p>
                </div>
              </div>
            </div>
          </div>

          {/* Address Sections - Conditional rendering */}
          {/* Permanent Address Section */}
          <div className="p-4 rounded border border-border bg-card shadow-xl overflow-hidden relative group border-l-4 border-l-primary/80">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded blur-3xl -translate-y-1/2 translate-x-1/2"></div>

            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-1.5 rounded bg-primary/10 text-primary flex items-center justify-center">
                <Icon name="home" size="18px" />
              </div>
              <h3 className="text-lg font-bold tracking-tight">
                Permanent Address
              </h3>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 relative z-10">
              <div className="group">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  Country
                </p>
                <p className="text-sm font-semibold text-foreground">
                  {renderAddressField(
                    displayAddress?.permanentAddress?.country
                  )}
                </p>
              </div>
              <div className="group">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  State / Province
                </p>
                <p className="text-sm font-semibold text-foreground">
                  {renderAddressField(displayAddress?.permanentAddress?.state)}
                </p>
              </div>
              <div className="group">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  City / Town
                </p>
                <p className="text-sm font-semibold text-foreground">
                  {renderAddressField(displayAddress?.permanentAddress?.city)}
                </p>
              </div>
              <div className="group sm:col-span-2">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  Locality / Area
                </p>
                <p className="text-sm font-semibold text-foreground">
                  {renderAddressField(
                    displayAddress?.permanentAddress?.locality
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Temporary Address Section */}
          <div className="p-4 rounded border border-border bg-card shadow-xl overflow-hidden relative group border-l-4 border-l-primary/80">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded blur-3xl -translate-y-1/2 translate-x-1/2"></div>

            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-1.5 rounded bg-primary/10 text-primary flex items-center justify-center">
                <Icon name="building" size="18px" />
              </div>
              <h3 className="text-lg font-bold tracking-tight">
                Temporary Address
              </h3>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 relative z-10">
              <div className="group">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  Country
                </p>
                <p className="text-sm font-semibold text-foreground">
                  {renderAddressField(
                    displayAddress?.temporaryAddress?.country
                  )}
                </p>
              </div>
              <div className="group">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  State / Province
                </p>
                <p className="text-sm font-semibold text-foreground">
                  {renderAddressField(displayAddress?.temporaryAddress?.state)}
                </p>
              </div>
              <div className="group">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  City / Town
                </p>
                <p className="text-sm font-semibold text-foreground">
                  {renderAddressField(displayAddress?.temporaryAddress?.city)}
                </p>
              </div>
              <div className="group sm:col-span-2">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 opacity-60">
                  Locality / Area
                </p>
                <p className="text-sm font-semibold text-foreground">
                  {renderAddressField(
                    displayAddress?.temporaryAddress?.locality
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-2">
          {/* Managed By Card */}
          {renderManagedByCard(profileData.createdBy)}

          {/* Customer/Organization Info Card */}
          {renderCustomerCard(
            profileData.customer,
            profileData.role,
            fetchProfileData,
            setShowCustomerEditModal
          )}

          {/* Security Status Card */}
          <div className="p-4 rounded border border-border bg-linear-to-br from-card to-muted/20 shadow-xl border-l-4 border-l-primary/80">
            <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em] mb-3">
              Security Profile
            </h4>

            <div className="space-y-2">
              <div className="flex items-center justify-between p-2 rounded bg-card border border-border/40">
                <div className="flex items-center gap-2.5">
                  <div
                    className={cn(
                      "w-7 h-7 rounded flex items-center justify-center",
                      profileData.isEmailVerified
                        ? "bg-green-500/10 text-green-600"
                        : "bg-red-500/10 text-red-600"
                    )}
                  >
                    <Icon
                      name={profileData.isEmailVerified ? "check" : "x"}
                      size="14px"
                    />
                  </div>
                  <span className="text-xs font-bold">Email Status</span>
                </div>
                <span
                  className={cn(
                    "text-[10px] font-black uppercase tracking-widest",
                    profileData.isEmailVerified
                      ? "text-green-600"
                      : "text-red-500"
                  )}
                >
                  {profileData.isEmailVerified ? "Verified" : "Action Req"}
                </span>
              </div>
            </div>

            <p className="mt-3 text-[10px] text-muted-foreground leading-relaxed italic text-center opacity-80">
              Your security credentials are systematically enforced by the
              central authority.
            </p>
          </div>

          {/* History & Timeline Section */}
          <div className="p-4 rounded border border-border bg-card shadow-xl overflow-hidden relative group border-l-4 border-l-primary/80">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded blur-3xl -translate-y-1/2 translate-x-1/2"></div>

            <div className="flex items-center gap-2.5 mb-4">
              <div className="p-1.5 rounded bg-primary/10 text-primary flex items-center justify-center">
                <Icon name="clock" size="18px" />
              </div>
              <h3 className="text-lg font-bold tracking-tight">
                Timeline & Activity
              </h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 relative z-10">
              <div className="p-4 rounded bg-muted/20 border border-border/40 hover:bg-muted/30">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded bg-green-500/10 text-green-600 flex items-center justify-center">
                    <Icon name="calendar" size="16px" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase font-semibold text-muted-foreground tracking-tighter">
                      Registration Date
                    </span>
                    <span className="text-xs font-semibold">
                      {formatDateWithMonthNameAndTime(profileData.createdAt)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded bg-muted/20 border border-border/40 hover:bg-muted/30">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded bg-orange-500/10 text-orange-600 flex items-center justify-center">
                    <Icon name="refresh" size="16px" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase font-semibold text-muted-foreground tracking-tighter">
                      Last Profile Sync
                    </span>
                    <span className="text-xs font-semibold">
                      {formatDateWithMonthNameAndTime(profileData.updatedAt)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      {showEditModal && (
        <EditProfileModal
          isOpen={showEditModal}
          onClose={() => setShowEditModal(false)}
          profileData={profileData}
          onUpdate={fetchProfileData}
        />
      )}

      {showPasswordModal && (
        <ChangePasswordModal
          isOpen={showPasswordModal}
          onClose={() => setShowPasswordModal(false)}
        />
      )}

      {showCustomerEditModal && profileData?.customer && (
        <CustomerManageModal
          open={showCustomerEditModal}
          onOpenChange={setShowCustomerEditModal}
          mode="update"
          customer={profileData.customer}
          onSave={handleUpdateCustomer}
        />
      )}
    </div>
  );
}

export default MyProfile;
