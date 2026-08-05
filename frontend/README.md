# VORA Frontend

VORA is a React single page application for the VORA AI Compliance Platform. It provides role-based dashboards and workflows for compliance framework management, deployment framework reviews, deployment documents, user/profile management, and AI-assisted processing status.

## Tech Stack

- React 19 with Vite
- React Router DOM 7
- Tailwind CSS 4 through `@tailwindcss/vite`
- Radix UI/shadcn-style UI primitives
- Recharts and Chart.js for dashboard charts
- Sonner for toast notifications
- pnpm for package management
- Docker + Nginx for production serving

## Core Functionality

- Authentication: login, registration, OTP verification, email verification, forgot/reset password, change password, and logout.
- Role-based routing for `admin`, `expert`, `customer`, `user`, `auditor`, and `internal-expert`.
- Session handling with `sessionStorage`, tenant header support, 1 hour idle timeout, 6 hour max session duration, and a global 401 logout flow.
- Dashboard analytics for admin, expert, and customer-style dashboards, including date and framework filters.
- Admin management for profiles, framework categories, expert framework access, and customer framework assignments.
- Expert framework management, including uploads, file versions, AI upload, approval/rejection, and control editing.
- Customer, auditor, user, and internal expert deployment workflows for deployment frameworks, deployment documents, assigned frameworks, reports, review requests, comparison, and gap analysis.
- Shared profile management and theme support.
- Reusable data tables, grid cards, upload/status cards, document preview, phone/geography inputs, and chart components.

## Roles And Main Routes

| Role              | Main Routes                                                                                                                                                                                                                                     | Purpose                                                                                                                    |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `admin`           | `/dashboard`, `/profiles`, `/framework-categories`, `/framework-access`, `/framework-assignments`, `/my-profile`                                                                                                                                | Platform administration, profile management, framework category/access management, and framework assignment to customers.  |
| `expert`          | `/dashboard`, `/frameworks`, `/frameworks/:id`, `/framework-categories`, `/framework-access`, `/deployment-frameworks`, `/deployment-frameworks/:id`, `/deployment-frameworks/:id/report`, `/my-profile`                                        | Framework upload/review, category access requests, and deployment framework expert review.                                 |
| `customer`        | `/dashboard`, `/profiles`, `/deployment-frameworks`, `/deployment-frameworks/:id`, `/deployment-frameworks/:id/report`, `/assigned-frameworks`, `/assigned-frameworks/:id`, `/deployment-documents`, `/deployment-documents/:id`, `/my-profile` | Customer user management, deployment framework/document workflows, assigned framework review, reports, and AI comparisons. |
| `user`            | `/dashboard`, `/deployment-frameworks`, `/deployment-frameworks/:id`, `/deployment-documents`, `/deployment-documents/:id`, `/my-profile`                                                                                                       | User-level access to deployment frameworks and deployment documents.                                                       |
| `auditor`         | `/dashboard`, `/profiles`, `/deployment-frameworks`, `/deployment-frameworks/:id`, `/deployment-frameworks/:id/report`, `/assigned-frameworks`, `/assigned-frameworks/:id`, `/deployment-documents`, `/deployment-documents/:id`, `/my-profile` | Auditor access to customer-style framework, document, profile, and report workflows.                                       |
| `internal-expert` | `/dashboard`, `/profiles`, `/deployment-frameworks`, `/deployment-frameworks/:id`, `/deployment-frameworks/:id/report`, `/assigned-frameworks`, `/assigned-frameworks/:id`, `/deployment-documents`, `/deployment-documents/:id`, `/my-profile` | Internal expert access to customer-style deployment, assigned framework, document, and report workflows.                   |

Public authentication routes:

- `/auth/login`
- `/auth/register`
- `/auth/verify-otp`
- `/auth/forgot-password`
- `/auth/reset-password`
- `/auth/verify-email`

The root route redirects authenticated users to `/dashboard` and unauthenticated users to `/auth/login`.

## Project Structure

```text
src/
  App.jsx                         App providers, document title, routes, toaster
  main.jsx                        React entry point
  index.css                       Tailwind/global styles
  assets/                         Logos and static app assets
  components/
    custom/                       App-specific UI components
    data-table/                   Reusable table and table data hook
    grid-card/                    Reusable grid/card views
    ui/                           shadcn-style primitives
  context/
    authContext/                  Auth state, login/logout, session handling
    customerAssignedFrameworksContext/
    expertAccessContext/
    profileContext/
    ThemeContext.jsx              Theme state
  hooks/                          Assigned framework, expert access, page title, polling hooks
  layout/                         App shell, auth layout, sidebar, header, footer
  lib/                            Shared low-level helpers
  pages/
    auth/                         Auth screens
    dashboard-management/         Role dashboards and dashboard widgets
    deployment-document-management/
    deployment-framework-management/
    framework-category-access-management/
    framework-management/
    profile-management/
  routes/
    routes.jsx                    Role-based route selection
    components/                   Route arrays and route guards
  services/                       API clients
  utils/                          Formatting, breadcrumbs, framework grouping, Word export
```

## API And State

All API calls go through `src/services/apiService.js`.

- API base URL: `${VITE_API_BASE_URL}/api`
- Auth token storage: `sessionStorage.token`
- User storage: `sessionStorage.user`
- Tenant storage: `sessionStorage.tenantId`
- Auth header: `Authorization: Bearer <token>`
- Tenant header: `X-TENANT-ID: <tenantId>`
- JSON requests automatically receive `Content-Type: application/json`.
- `FormData` uploads are sent without forcing a JSON content type.
- Blob responses are used for file downloads.
- A single global `unauthorized-response` event handles 401 responses and redirects the user to login.

Main service files:

- `authService.js` - login, registration, OTP, email verification, password flows, logout.
- `userService.js` - user and profile operations.
- `adminService.js` - framework categories, expert access, framework assignments.
- `frameworkService.js` - expert framework upload, AI upload, approval/rejection, file download, version/control updates.
- `deploymentFrameworkService.js` - assigned frameworks, deployment uploads, AI upload, comparison, gap analysis, expert review, reports/control updates.
- `deploymentDocumentService.js` - document upload, versions, preview, AI upload, download, update, delete.
- `dashboardService.js` - admin, expert, and customer analytics.

## Environment Variables

Create or update `.env`/`.env.local` with these values for the target environment:

```env
VITE_API_BASE_URL=http://localhost:7000
VITE_WS_BASE_URL=ws://localhost:7000
VITE_INTERNAL_USER_SYNC_API_KEY=replace-with-api-key
```

Notes:

- `VITE_API_BASE_URL` is required by the API service.
- `VITE_WS_BASE_URL` is reserved for realtime/AI processing integrations.
- Keep real API keys out of committed examples and shared documentation.

## Getting Started

Install dependencies:

```bash
pnpm install
```

Run the development server:

```bash
pnpm dev
```

Build for production:

```bash
pnpm build
```

Preview the production build locally:

```bash
pnpm preview
```

Run linting:

```bash
pnpm lint
```

Format source files:

```bash
pnpm format
```

## Docker Deployment

Build and run with Docker Compose:

```bash
docker compose up -d --build
```

The compose file exposes the Nginx container on port `7050`:

```text
http://localhost:7050
```

The production image:

- Builds the Vite app with Node 20 Alpine.
- Serves `dist/` through Nginx.
- Uses `nginx.conf` to support React Router fallback to `index.html`.
- Adds long-lived caching for static assets and common security headers.

## Build Notes

- The Vite alias `@` points to `src`.
- Production builds split common vendor chunks for React, charts, Radix/UI, and miscellaneous dependencies.
- Source maps are disabled for production.
- The Nginx config handles browser refreshes on nested SPA routes.

## Last Updated

May 6, 2026
