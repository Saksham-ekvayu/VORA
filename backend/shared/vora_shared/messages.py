"""Centralized messages file for all services."""

from typing import Any

# --- Helper functions ---


def format_message(template: str, **replacements: Any) -> str:
    message = template
    for key, value in replacements.items():
        message = message.replace(f"{{{key}}}", str(value))
    return message


def role_restriction(current_role: str, allowed_roles: str) -> str:
    return f"{current_role} can only create users with roles: {allowed_roles}"


def role_assignment_restriction(current_role: str, allowed_roles: str) -> str:
    return f"{current_role} can only assign roles: {allowed_roles}"


def cannot_change_own_role(role: str) -> str:
    return f"{role} cannot change their own role"


def cannot_change_own_status(role: str) -> str:
    return f"{role} cannot change their own account status"


def cannot_delete_own_account(role: str) -> str:
    return f"{role} cannot delete their own account"


# --- Flat Messages (Auth & Profile) ---
USER_ALREADY_EXISTS = "An account with this email already exists."
INVALID_CREDENTIALS = "Incorrect email or password. Please try again."
PASSWORD_MISMATCH = "Current password is incorrect."
USER_NOT_FOUND_EMAIL = "No account found with this email address."
ACCOUNT_DEACTIVATED = "Your account has been deactivated. Please contact administrator."
ACCOUNT_NOT_VERIFIED = "Your account is not verified. Please verify your email first."

OTP_NOT_FOUND = "No verification code found. Please request a new one."
OTP_EXPIRED = "Verification code has expired. Please request a new one."
OTP_INVALID = "Invalid verification code. Please try again."
OTP_WRONG_PURPOSE = "This verification code cannot be used for this action."
OTP_SENT_SUCCESS = "New verification code sent successfully."

EMAIL_SEND_FAILED = "Unable to send email. Please try again later."

EMAIL_SUBJECT_REGISTRATION = "Welcome! Verify Your Email Address"
EMAIL_SUBJECT_RESEND_OTP = "Email Verification - New OTP Code"
EMAIL_SUBJECT_PASSWORD_RESET = "Password Reset - Security Code"
EMAIL_SUBJECT_EMAIL_VERIFICATION = "Email Verification - Confirm Your Identity"

DEFAULT_USER_NAME = "User"

LOGIN_SUCCESS = "Login successful."
LOGOUT_SUCCESS = "Logout successful."
LOGOUT_ALL_DEVICES_SUCCESS = "Logged out from all devices successfully."
EMAIL_VERIFIED_SUCCESS = "Email verified successfully. Please login."
PASSWORD_RESET_OTP_SENT = "Password reset code sent to your email."
PASSWORD_RESET_SUCCESS = "Password reset successful. Please login with your new password."
PASSWORD_CHANGED_SUCCESS = "Password changed successfully. Please login again with your new password."
VERIFICATION_OTP_SENT = "Verification code sent to your email."
EMAIL_ALREADY_VERIFIED = "Email is already verified."

PASSWORD_SAME_AS_OLD = "New password must be different from current password"
PHONE_ALREADY_EXISTS = "Phone number already exists"
USER_NOT_FOUND = "User not found"

USER_PROFILE_NOT_FOUND = "User profile not found."
EMAIL_ALREADY_EXISTS = "An account with this email already exists."
NAME_CANNOT_BE_EMPTY = "Name cannot be empty."
PROFILE_UPDATE_FAILED = "Failed to update profile. Please try again."
EMAIL_CANNOT_BE_CHANGED = "Email cannot be changed"
ROLE_CANNOT_BE_CHANGED_BY_USER = "Role cannot be changed by user"
AVATAR_UPDATED = "Avatar updated successfully"
AVATAR_REQUIRED = "Please select an image file to upload"
NO_CHANGES_DETECTED = "No changes detected. Provide different values."
USER_ACCOUNT_DEACTIVATED = "User account is deactivated"
CANNOT_CHANGE_ADMIN_ROLE = "Cannot change role of other admin users"
ONLY_UPDATE_CREATED_USERS = "You can only update users created by you"
ONLY_VIEW_CREATED_USERS = "You can only view users created by you"
ONLY_CHANGE_STATUS_CREATED_USERS = "You can only change status of users created by you"
ONLY_DELETE_CREATED_USERS = "You can only delete users created by you"
FAILED_TO_UPDATE_USER = "Failed to update user"
FAILED_TO_UPDATE_USER_STATUS = "Failed to update user status"
USER_ACTIVATED = "User activated successfully"
USER_DEACTIVATED = "User deactivated successfully"
CUSTOMER_NOT_FOUND = "Customer not found"

NO_USERS_MATCH_CRITERIA = "No users match your search criteria. Try adjusting your filters."
NO_USERS_AVAILABLE = "No users available yet. Create your first user to get started."
USER_LIST_RETRIEVED = "User list retrieved successfully"
PROFILE_RETRIEVED = "Profile retrieved successfully"
PROFILE_UPDATED = "Profile updated successfully"
USER_CREATED = "User created successfully. Temporary password has been sent to their email address."
USER_CREATED_EMAIL_FAILED = (
    "User created successfully, but failed to send email. Please provide the temporary password manually."
)
USER_DELETED = "User deleted successfully"

TENANT_ID_REQUIRED = "Tenant ID is required in X-TENANT-ID header"
TENANT_ID_INVALID_FORMAT = "Invalid Tenant ID format"
TENANT_ID_INVALID_CHARS = "Tenant ID contains invalid characters"
TENANT_ID_LENGTH = "Tenant ID must be between 3 and 50 characters"
TENANT_ID_MISMATCH = "Tenant ID mismatch between JWT token and header"

# --- Constants ---

VALID_STATUSES = ["pending", "approved", "rejected", "revoked"]

# --- Dictionary Messages ---

MESSAGES = {
    # From dashboard-service
    "DASHBOARD_ANALYTICS_SUCCESS": "Dashboard analytics retrieved successfully",
    "DASHBOARD_ANALYTICS_FAILED": "Failed to fetch dashboard analytics",
    # From framework-category-service
    "FRAMEWORK_CATEGORY_NOT_FOUND": "Framework Category not found",
    "FRAMEWORK_CATEGORY_CODE_EXISTS": "Framework category with this code already exists",
    "FRAMEWORK_CATEGORIES_SUCCESS": "Framework categories retrieved successfully",
    "FRAMEWORK_CATEGORY_SUCCESS": "Framework category retrieved successfully",
    "FRAMEWORK_CATEGORY_CREATED": "Framework category created successfully",
    "FRAMEWORK_CATEGORY_UPDATED": "Framework category updated successfully",
    "FRAMEWORK_CATEGORY_DELETED_WITH_ACCESS": "Framework category deleted successfully. {count} related access records were also removed.",
    "NO_CATEGORIES_SEARCH": "No framework categories match your search criteria. Try adjusting your filters.",
    "NO_CATEGORIES_FIRST": "No framework categories available yet. Create your first category to get started.",
    "FRAMEWORK_ACCESS_NOT_FOUND": "Framework access record not found",
    "FRAMEWORK_ACCESS_REQUEST_NOT_FOUND": "Framework Access Request not found",
    "FRAMEWORK_ACCESS_SUCCESS": "Framework access records retrieved successfully",
    "FRAMEWORK_ACCESS_RECORD_SUCCESS": "Framework access record retrieved successfully",
    "FRAMEWORK_ACCESS_ASSIGNED": "Framework access assigned successfully",
    "FRAMEWORK_ACCESS_APPROVED": "Framework access approved successfully",
    "FRAMEWORK_ACCESS_REJECTED": "Framework access rejected successfully",
    "FRAMEWORK_ACCESS_REVOKED": "Framework access revoked successfully",
    "NO_ACCESS_SEARCH": "No framework access records match your search criteria.",
    "NO_ACCESS_STATUS": "No {status} framework access records found.",
    "NO_ACCESS_EXPERT": "No framework access records found for this expert.",
    "NO_ACCESS_RECORDS": "No framework access records found.",
    "NO_ACCESS_FRAMEWORK_CODE": "No framework access records found for this framework code.",
    "EXPERT_NOT_FOUND": "Expert not found",
    "EXPERT_NOT_ACTIVE": "Expert is not active",
    "FRAMEWORK_CATEGORY_INACTIVE": "Framework category is not active",
    "ACCESS_ALREADY_PROCESSED": "Access request has already been processed",
    "ACCESS_RECORD_NOT_FOUND": "Framework access record not found for this expert and framework category",
    "ONLY_APPROVED_CAN_REVOKE": "Only approved access can be revoked",
    "INVALID_STATUS": "Invalid status. Must be one of: {statuses}, all",
    "EXPERT_ID_REQUIRED": "Expert ID is required",
    "FRAMEWORK_CATEGORY_IDS_REQUIRED": "At least one framework category must be selected",
    "FRAMEWORK_CATEGORY_IDS_ARRAY": "Framework category IDs must be provided as an array",
    "ALREADY_HAS_ACCESS": "Expert already has access to this framework",
    "INVALID_OBJECT_ID": "Invalid {field}: {value}",
    "FRAMEWORK_CATEGORIES_NOT_FOUND_PREFIX": "Framework categories not found",
}

VALIDATION_MESSAGES = {
    # From framework-category-service
    "FRAMEWORK_CODE_REQUIRED": "Framework code is required",
    "FRAMEWORK_CODE_LENGTH": "Framework code must be between 2 and 100 characters",
    "FRAMEWORK_CODE_INVALID_CHARS": "Framework code can only contain lowercase letters, numbers, and underscores",
    "FRAMEWORK_CODE_UNDERSCORE": "Framework code cannot start or end with underscore",
    "FRAMEWORK_NAME_REQUIRED": "Framework category name is required",
    "FRAMEWORK_NAME_LENGTH": "Framework category name must be between 2 and 200 characters",
    "FRAMEWORK_NAME_SPACES_ONLY": "Framework category name cannot contain only spaces",
    "DESCRIPTION_TOO_LONG": "Description cannot exceed 1000 characters",
    "IS_ACTIVE_BOOLEAN": "isActive must be a boolean value",
}

BUSINESS_MESSAGES = {
    # From deployment-framework-service
    "FRAMEWORK_ACCESS_DENIED": "You don't have permission to access this framework",
    "FRAMEWORK_RETRIEVED_SUCCESS": "Framework retrieved successfully",
    "DEPLOYMENT_FRAMEWORKS_RETRIEVED": "Deployment frameworks retrieved successfully",
    "USER_FRAMEWORKS_RETRIEVED": "Your frameworks retrieved successfully",
    "NO_FRAMEWORKS_MATCH_CRITERIA": "No frameworks match your search criteria. Try adjusting your filters.",
    "NO_FRAMEWORKS_FOR_REVIEW": "No frameworks assigned to you for review",
    "NO_USER_FRAMEWORKS": "You haven't uploaded any frameworks yet. Upload your first framework to get started.",
    "ASSIGNED_FRAMEWORKS_RETRIEVED": "{status} frameworks retrieved successfully",
    "NO_ASSIGNED_FRAMEWORKS": "No frameworks have been {status} to your customer yet.",
    "NO_ASSIGNED_FRAMEWORKS_SEARCH": "No assigned frameworks match your search criteria. Try adjusting your filters.",
    "ASSIGNMENT_NOT_FOUND": "Framework assignment not found",
    "ASSIGNMENT_ALREADY_REVOKED": "Framework assignment is already revoked",
    "ASSIGNMENT_REVOKED_SUCCESS": "Framework assignment revoked successfully",
    "SECTION_ID_NAME_REQUIRED": "sectionId and name are required",
    "FILE_VERSION_NOT_FOUND": "File version {version} not found",
    "AI_EXTRACTION_NOT_FOUND": "AI Extraction data not found for this version",
    "SECTION_NOT_FOUND": "Section {sectionId} not found in version {version}",
    "CONTROL_ID_ALREADY_EXISTS": "Control ID {controlId} already exists",
    "CONTROL_ADDED_SUCCESS": "Control added successfully to section {sectionId} in version {version}",
    "CONTROL_NOT_FOUND": "Control {controlId} not found in version {version}",
    "CONTROL_UPDATE_REQUIRED": "At least one of name, description, or deployment_points must be provided",
    "CONTROL_UPDATED_SUCCESS": "Control {controlId} updated successfully in version {version}",
    "CONTROL_CUSTOM_ONLY": "You can only update custom controls",
    "CONTROL_DELETE_CUSTOM_ONLY": "You can only delete custom controls",
    "CONTROL_DELETED_SUCCESS": "Control {controlId} deleted successfully from version {version}",
    "CONTROL_WEIGHTAGE_INVALID": "Valid weightage object must be provided",
    "CONTROL_NOT_APPLICABLE_WEIGHTAGE_ERROR": "Cannot update weightage for a control that is marked not applicable",
    "CONTROL_WEIGHTAGE_UPDATED_SUCCESS": "Control {controlId} weightage updated successfully",
    "INVALID_ASSIGNMENT_STATUS_FILTER": "Invalid assignment status. Allowed values: assigned, revoked",
    "INVALID_FINALIZATION_STATUS_FILTER": "Invalid finalization status. Allowed values: finalized, pending",
    "NEW_SECTION_EMPTY": "New section name cannot be empty",
    "SECTION_ALREADY_EXISTS": 'Section with name "{sectionName}" already exists',
    "SECTION_ID_EXISTS": 'Generated Section ID "{sectionId}" already exists',
    "VERSION_NO_CONTROLS": "No controls found in version {version}",
    "CONTROL_APPLICABILITY_UPDATED_SUCCESS": "Control {controlId} marked as {status}",
    "CONTROL_IDS_REQUIRED": "Control IDs must be a non-empty array",
    "APPLICABILITY_REQUIRED": "is_applicable must be a boolean value",
    "NO_CONTROLS_FOUND": "No matching controls found in this version",
    "USER_ID_REQUIRED": "User ID (_id) is required for sync",
    "CANNOT_MODIFY_FINALIZED": "Cannot modify a finalized framework version.",
}

FRAMEWORK_MESSAGES = {
    # From deployment-framework-service
    "COMPARISON_REQUIRED_FIELDS": "Both deploymentControlsJobId and officialControlsJobId are required",
    "DEPLOYMENT_FRAMEWORK_NOT_FOUND": "Deployment framework not found or you don't have permission to access it",
    "FRAMEWORK_VERSION_NOT_FOUND": "Framework version not found for the provided job ID",
    "COMPARISON_IN_PROGRESS": "Comparison is already in progress for this framework",
    "COMPARISON_COMPLETED_RECENTLY": "Comparison already completed recently",
    "COMPARISON_STARTED": "Framework comparison started successfully",
    "COMPARISON_START_FAILED": "Failed to start framework comparison",
    "COMPARISON_SERVICE_UNAVAILABLE": "AI comparison service is unavailable. Please try again later.",
    "COMPARISON_SERVICE_ERROR": "AI comparison service returned an error",
    "COMPARISON_INITIATE_FAILED": "Failed to initiate framework comparison",
    "COMPARISON_NOT_COMPLETED": "Comparison analysis must be completed before downloading the report",
    "MERGE_DOCUMENT_NOT_COMPLETED": "Merge extraction must be completed before downloading the report",
    "DEPLOYMENT_GAP_IN_PROGRESS": "Deployment gap analysis is already in progress for this framework",
    "DEPLOYMENT_GAP_COMPLETED_RECENTLY": "Deployment gap analysis already completed recently",
    "DEPLOYMENT_GAP_STARTED": "Deployment gap analysis started successfully",
    "DEPLOYMENT_GAP_START_FAILED": "Failed to start deployment gap analysis",
    "DEPLOYMENT_GAP_SERVICE_UNAVAILABLE": "Deployment gap service is unavailable. Please try again later.",
    "DEPLOYMENT_GAP_SERVICE_ERROR": "Deployment gap service returned an error",
    "DEPLOYMENT_GAP_INITIATE_FAILED": "Failed to initiate deployment gap analysis",
    "GAP_ANALYSIS_NOT_COMPLETED": "Gap analysis must be completed before downloading the report",
    "EXPERT_ID_REQUIRED": "Expert ID is required",
    "ONLY_OWN_FRAMEWORKS": "You can only request review for your own frameworks",
    "REVIEW_ALREADY_REQUESTED": "Review has already been requested for this framework",
    "EXPERT_NOT_FOUND": "Expert not found or not active",
    "REVIEW_REQUESTED": "Expert review requested successfully",
    "ONLY_ASSIGNED_FRAMEWORKS": "You can only approve frameworks assigned to you",
    "REVIEW_NOT_REQUESTED": "Framework review has not been requested or already reviewed",
    "FRAMEWORK_APPROVED": "Framework approved and deployed successfully",
    "FRAMEWORK_RETURNED": "Framework returned for revision",
    "COMMENTS_REQUIRED_REJECTION": "Comments are required when rejecting a framework",
    "ONLY_REJECT_ASSIGNED": "You can only reject frameworks assigned to you",
    "FRAMEWORK_REJECTED": "Framework rejected successfully",
}

FRAMEWORK_SERVICE_MESSAGES = {
    "FRAMEWORK_NOT_FOUND": "Framework not found",
    "ONLY_THE_USER_WHO_UPLOADED_THE_FRAMEWORK": "Only the user who uploaded the framework can approve it.",
    "FRAMEWORK_IS_ALREADY_APPROVED": "Framework is already approved",
    "FRAMEWORK_MUST_BE_UPLOADED_TO_AI_BEFORE": "Framework must be uploaded to AI before approval",
    "FRAMEWORK_AI_PROCESSING_IS_IN_PROGRESS_P": "Framework AI processing is in progress. Please wait for completion",
    "FRAMEWORK_AI_PROCESSING_FAILED": "Framework AI processing failed",
    "FRAMEWORK_IS_ALREADY_REJECTED": "Framework is already rejected",
    "CUSTOMERID_TENANTID_AND_FRAMEWORKIDS_NON": "customerId, tenantId, and frameworkIds (non-empty array) are required fields.",
    "CUSTOMER_ORGANIZATION_NOT_FOUND": "Customer organization not found.",
    "CUSTOMER_ORGANIZATION_IS_NOT_ACTIVE": "Customer organization is not active.",
    "FRAMEWORKS_NOT_FOUND": "Frameworks not found",
    "ONE_OR_MORE_PROVIDED_FRAMEWORK_IDS_ARE_I": "One or more provided framework IDs are invalid.",
    "INVALID_FRAMEWORK_CATEGORY_ID_FORMAT": "Invalid framework category ID format",
    "FAILED_TO_SAVE_FILE": "Failed to save file",
    "YOU_DON_T_HAVE_PERMISSION_TO_UPDATE_THIS": "You don't have permission to update this framework",
    "YOU_DON_T_HAVE_PERMISSION_TO_DELETE_THIS": "You don't have permission to delete this file",
    "CANNOT_DELETE_APPROVED_FRAMEWORK": "Cannot delete approved framework",
    "YOU_DON_T_HAVE_PERMISSION_TO_ACCESS_THES": "You don't have permission to access these files",
    "YOU_DON_T_HAVE_PERMISSION_TO_ACCESS_THIS": "You don't have permission to access this file",
    "FILE_NOT_FOUND": "File not found",
    "FILE_NOT_FOUND_ON_DISK": "File not found on disk",
    "FILE_VERSION_NOT_FOUND": "File version not found",
    "FILE_ON_DISK_NOT_FOUND": "File on disk not found",
    "CANNOT_DELETE_FILES_FROM_APPROVED_FRAMEW": "Cannot delete files from approved framework",
    "SECTIONID_OR_NEWSECTION_AND_NAME_ARE_REQ": "sectionId or newSection, and name are required",
    "YOU_DON_T_HAVE_PERMISSION_TO_MODIFY_THIS": "You don't have permission to modify this framework",
    "CANNOT_EDIT_CONTROLS_IN_APPROVED_FRAMEWO": "Cannot edit controls in approved frameworks",
    "AI_EXTRACTION_DATA_NOT_FOUND_FOR_THIS_VE": "AI Extraction data not found for this version",
    "AT_LEAST_ONE_OF_NAME_DESCRIPTION_OR_DEPL": "At least one of name, description, or deployment_points must be provided",
    "VALID_WEIGHTAGE_MUST_BE_PROVIDED": "Valid weightage must be provided",
    "CANNOT_DELETE_CONTROLS_FROM_APPROVED_FRA": "Cannot delete controls from approved frameworks",
    "FRAMEWORK_RETRIEVED_SUCCESSFULLY": "Framework retrieved successfully",
    "APPROVAL": "approval",
    "FRAMEWORK_REJECTED_SUCCESSFULLY": "Framework rejected successfully",
    "TENANTID": "tenantId",
    "FRAMEWORK_CREATED_SUCCESSFULLY": "Framework created successfully",
    "FRAMEWORK_UPDATED_SUCCESSFULLY": "Framework updated successfully",
    "FRAMEWORK_DELETED_SUCCESSFULLY": "Framework deleted successfully",
    "FRAMEWORK_FILES_RETRIEVED_SUCCESSFULLY": "Framework files retrieved successfully",
    "FRAMEWORK_FILE_RETRIEVED_SUCCESSFULLY": "Framework file retrieved successfully",
    "SECTIONID": "sectionId",
    "FILEVERSION": "fileVersion",
    "FRAMEWORK_CATEGORY_NOT_FOUND": "Framework category not found",
    "FRAMEWORK_CATEGORY_IS_NOT_ACTIVE": "Framework category is not active",
    "ID": "id",
}
