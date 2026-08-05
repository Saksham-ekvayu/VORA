# VORA Admin Dashboard Specification

## Purpose

This document defines the content and structure for the single Admin dashboard page in VORA.

Here, **Admin** means the platform/product owner role. This dashboard is not for managing a single customer organization internally. Customer organization operations belong to the **Customer Admin** dashboard.

The Admin dashboard should help the product owner answer:

- Is the VORA platform healthy?
- Are customers, experts, frameworks, and assignments growing correctly?
- What needs admin action right now?
- Are experts blocked because of pending access?
- Are approved frameworks being assigned to customers?
- Are there inactive or incomplete setup areas that need follow-up?

## Admin Scope

Admin is responsible for platform-level control:

- Manage expert profiles.
- Manage customer organizations.
- Manage framework categories.
- Approve, reject, assign, or revoke expert framework category access.
- Track framework inventory and approval state.
- Assign approved frameworks to customer organizations.
- Monitor product adoption across customers and experts.

Admin should not deeply manage customer-side execution from this dashboard.

## What This Dashboard Should Not Show

The Admin dashboard should avoid showing detailed customer-admin operational data such as:

- Customer organization's internal user workload.
- Detailed deployment document file lists.
- Detailed control-by-control compliance implementation.
- Deep gap analysis rows for each customer.
- Customer-side daily audit task management.
- Internal deployment setup configuration.
- Customer admin's organization-level dashboard details.

Admin can see high-level indicators if useful, but detailed customer execution should stay inside customer/customer-admin pages.

## Page Layout

Recommended single-page layout:

1. Header and filters
2. Platform KPI summary
3. Admin action queue
4. Customer organization overview
5. Expert and access overview
6. Framework library overview
7. Framework assignment overview
8. Platform activity trend
9. Recent platform activity
10. Quick actions

## 1. Header And Filters

Header title:

`Admin Dashboard`

Subtitle:

`Platform overview for customers, experts, frameworks, and assignments`

Controls:

- Date range filter: Today, 7 days, 30 days, custom range
- Refresh button
- Optional status filter for action queue

The page should default to the last 30 days for trend charts, while lifetime totals can still be shown in KPI cards.

## 2. Platform KPI Summary

Top KPI cards should show only platform-owner level metrics.

Recommended cards:

| KPI                            | Meaning                                                  | Click Target                             |
| ------------------------------ | -------------------------------------------------------- | ---------------------------------------- |
| Active Customers               | Number of active customer organizations                  | `/customers?isActive=true`               |
| Active Experts                 | Number of active expert users                            | `/profiles?role=expert&isActive=true`    |
| Framework Categories           | Active framework categories available in the platform    | `/framework-categories`                  |
| Approved Frameworks            | Frameworks approved and available for assignment         | `/frameworks?approval=approved`          |
| Pending Access Requests        | Expert category access requests waiting for admin action | `/framework-access?status=pending`       |
| Active Assignments             | Frameworks currently assigned to customers               | `/framework-assignments?status=assigned` |
| Unassigned Approved Frameworks | Approved frameworks not assigned to any customer         | framework assignment flow                |
| Inactive Customers             | Customer organizations currently inactive                | `/customers?isActive=false`              |

Priority cards:

1. Active Customers
2. Active Experts
3. Pending Access Requests
4. Approved Frameworks
5. Active Assignments
6. Unassigned Approved Frameworks

## 3. Admin Action Queue

This should be the most important dashboard section.

It should show items that need admin action.

Recommended action types:

| Action Type                            | Why It Matters                                                  | CTA                |
| -------------------------------------- | --------------------------------------------------------------- | ------------------ |
| Pending expert access requests         | Experts cannot upload/manage frameworks without category access | Review Access      |
| Experts with no category access        | Expert exists but cannot contribute yet                         | Assign Access      |
| Frameworks pending approval            | Framework library is blocked until approval                     | Review Framework   |
| Approved frameworks not assigned       | Framework exists but is not generating customer value           | Assign To Customer |
| Customers with no framework assignment | Customer onboarding is incomplete                               | Assign Framework   |
| Inactive customers                     | Product owner should know inactive accounts                     | View Customer      |
| Revoked assignments                    | Shows customer access removals and potential follow-up          | View Assignment    |

Each queue row should include:

- Type
- Name/title
- Related user/customer/framework
- Status
- Created/requested date
- Direct action button

Do not include customer-admin internal tasks here.

## 4. Customer Organization Overview

This section should give product-level customer visibility, not deep operational customer details.

Recommended summary:

- Total customers
- Active customers
- Inactive customers
- New customers in selected date range
- Customers with at least one framework assignment
- Customers with zero framework assignments

Recommended table columns:

| Column              | Description                                |
| ------------------- | ------------------------------------------ |
| Customer            | Organization name and email                |
| Status              | Active/inactive                            |
| Assigned Frameworks | Count of currently assigned frameworks     |
| Created At          | Customer onboarding date                   |
| Last Updated        | Last customer profile update, if available |
| Action              | View customer                              |

Useful labels:

- `No Framework Assigned`
- `Active`
- `Inactive`
- `Recently Added`

Avoid showing:

- Customer deployment document details
- Individual customer controls
- Customer internal users, except a count if needed
- Customer gap analysis details

## 5. Expert And Access Overview

This section should help admin manage expert readiness.

Recommended summary cards:

- Total experts
- Active experts
- Inactive experts
- Experts with approved access
- Experts with pending access
- Experts with no access

Recommended chart:

`Framework Access Status Distribution`

Statuses:

- Pending
- Approved
- Rejected
- Revoked

Recommended table:

| Column            | Description                                |
| ----------------- | ------------------------------------------ |
| Expert            | Expert name and email                      |
| Access Status     | Approved/pending/rejected/revoked summary  |
| Categories        | Number of categories assigned/requested    |
| Framework Uploads | Count of uploaded frameworks, if available |
| Action            | Manage access                              |

This is admin-relevant because expert access is directly controlled by admin.

## 6. Framework Library Overview

This section should summarize the platform's reusable compliance framework inventory.

Recommended summary:

- Total frameworks
- Approved frameworks
- Pending frameworks
- Rejected frameworks
- Frameworks by category
- Frameworks uploaded in selected date range

Recommended charts:

- Framework approval status distribution
- Frameworks by category
- Framework uploads over time

Recommended table:

| Column      | Description                  |
| ----------- | ---------------------------- |
| Framework   | Framework name and version   |
| Category    | Framework category           |
| Uploaded By | Expert who uploaded it       |
| Approval    | Pending/approved/rejected    |
| Assignments | Number of customers assigned |
| Action      | View framework or assign     |

Admin should see framework inventory health, but should not edit controls from the dashboard.

## 7. Framework Assignment Overview

This section should show whether approved frameworks are being connected to customers.

Recommended summary:

- Total active assignments
- Revoked assignments
- Customers with assignments
- Customers without assignments
- Approved frameworks assigned to at least one customer
- Approved frameworks not assigned to any customer

Recommended chart:

- Assignments by framework
- Assignments by customer

Recommended table:

| Column      | Description            |
| ----------- | ---------------------- |
| Customer    | Customer organization  |
| Framework   | Assigned framework     |
| Version     | Framework version      |
| Status      | Assigned/revoked       |
| Assigned At | Date of assignment     |
| Action      | View/revoke assignment |

This belongs to Admin because assignment is an admin-owned action.

## 8. Platform Activity Trend

This section should show product adoption and platform movement.

Recommended charts:

- New customers over time
- New experts over time
- Framework uploads over time
- Framework assignments over time
- Expert access requests over time

Keep this section focused on platform adoption, not customer execution detail.

## 9. Recent Platform Activity

A compact activity feed should show the latest platform-level events.

Recommended events:

- Customer created
- Customer activated/deactivated
- Expert created
- Expert activated/deactivated
- Framework category created/updated
- Expert access requested
- Expert access approved/rejected/revoked
- Framework uploaded
- Framework approved/rejected
- Framework assigned to customer
- Framework assignment revoked

Each activity item should include:

- Event label
- Related actor
- Related entity
- Timestamp
- Link to details

## 10. Quick Actions

Recommended quick actions:

- Add Customer
- Add Expert
- Create Framework Category
- Manage Expert Access
- Assign Framework To Customer
- View Framework Assignments

Avoid generic actions like `System Settings` unless a real settings page exists.

## Recommended Data Shape

The redesigned admin dashboard API should ideally return:

```json
{
  "stats": {
    "activeCustomers": 0,
    "inactiveCustomers": 0,
    "activeExperts": 0,
    "inactiveExperts": 0,
    "frameworkCategories": 0,
    "approvedFrameworks": 0,
    "pendingFrameworks": 0,
    "pendingAccessRequests": 0,
    "activeAssignments": 0,
    "revokedAssignments": 0,
    "customersWithoutAssignments": 0,
    "unassignedApprovedFrameworks": 0
  },
  "actionQueue": [],
  "customerOverview": [],
  "expertAccessOverview": [],
  "frameworkOverview": [],
  "assignmentOverview": [],
  "charts": {
    "customerGrowth": [],
    "expertGrowth": [],
    "frameworkApprovalStatus": [],
    "accessStatus": [],
    "assignmentTrend": []
  },
  "recentActivity": []
}
```

## Current Backend Fit

Current dashboard admin analytics already provides some base counts:

- Total users
- Total customers
- Total frameworks
- Total framework categories
- Total approved framework access
- Total assigned frameworks
- Recent created users
- User creation chart

For the redesigned Admin dashboard, backend should be extended for:

- Pending access requests
- Expert access status distribution
- Framework approval status distribution
- Customers with/without assignments
- Approved frameworks with/without assignments
- Assignment status distribution
- Platform-level recent activity

## Final Dashboard Principle

The Admin dashboard should be a **platform control dashboard**, not a customer execution dashboard.

It should focus on:

- Platform growth
- Admin approvals
- Expert readiness
- Framework library health
- Customer onboarding/assignment status
- High-level platform activity

Customer-admin dashboard should separately focus on:

- Organization users
- Assigned frameworks for that organization
- Deployment documents
- Customer-specific compliance progress
- Customer audit/review execution
