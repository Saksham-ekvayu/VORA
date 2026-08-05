# VORA Navigation and Routing Flow

Below are comprehensive flow diagrams representing the navigation structure and available pages for your application, mapped out according to the authentication state and user roles (`admin`, `expert`, `Customer`, `user`).

## 1. High-Level Routing & Auth Flow

This diagram illustrates the entry point of the app where the system decides what routes the user can access based on their authentication status and assigned role.

```mermaid
graph TD
    %% Base entry point
    Root((Root /)) --> AuthCondition{Is Authenticated?}
    AuthCondition -->|No| Auth[Auth Flow]
    AuthCondition -->|Yes| RoleCheck{User Role?}

    %% Auth Flow Routes
    subgraph Auth Routes
        Auth --> Login[/auth/login]
        Auth --> Register[/auth/register]
        Auth --> ForgotPwd[/auth/forgot-password]
        Auth --> ResetPwd[/auth/reset-password]
        Auth --> VerifyEmail[/auth/verify-email]
        Auth --> VerifyOTP[/auth/verify-otp]
    end

    %% Protected Routes Distribution
    RoleCheck -->|Admin| Admin[Admin Layout]
    RoleCheck -->|Expert| Expert[Expert Layout]
    RoleCheck -->|Customer| Customer[Customer Layout]
    RoleCheck -->|User| AppUser[User Layout]

    %% Shared Routes
    RoleCheck -.-> Profile[Profile View /profile]
```

---

## 2. Admin Navigation Flow

Admins have access to system-wide framework management, profiles management, and an admin dashboard.

```mermaid
graph TD
    Admin[Admin Role] --> Sidebar[Sidebar Menu]

    subgraph Menu Navigation
        Sidebar --> AdminDashboard[Dashboard /dashboard]
        Sidebar --> AdminUsers[Profiles Management /profiles]
        Sidebar --> FrameworkMgmtGroup["Framework Management ▼"]

        %% Framework Management Dropdown
        FrameworkMgmtGroup --> AdminFrameworkCat[Framework Categories /framework-categories]
        FrameworkMgmtGroup --> AdminFrameworkAcc[Framework Access /framework-access]
        FrameworkMgmtGroup --> AdminFrameworkAsg[Framework Assignments /framework-assignments]
    end
```

---

## 3. Expert Navigation Flow

Experts have access to framework details, deployment frameworks requests, and their own dashboard.

```mermaid
graph TD
    Expert[Expert Role] --> Sidebar[Sidebar Menu]

    subgraph Menu Navigation
        Sidebar --> ExpertDashboard[Dashboard /dashboard]
        Sidebar --> FrameworkMgmtGroup["Framework Management ▼"]
        Sidebar --> ExpertDeployReq[Deployment Framework /deployment-frameworks]

        %% Framework Management Dropdown
        FrameworkMgmtGroup --> ExpertFrameworks[Frameworks /frameworks]
        FrameworkMgmtGroup --> ExpertFrameworkCat[Framework Categories /framework-categories]
        FrameworkMgmtGroup --> ExpertFrameworkAcc[Framework Access /framework-access]
    end

    subgraph Detail Pages
        ExpertFrameworks -.-> ExpertFrameworksDetail[Framework Details /frameworks/:id]
        ExpertDeployReq -.-> ExpertDeployDetail[Deployment Framework Details /deployment-frameworks/:id]
    end
```

---

## 4. Customer Navigation Flow

Customer users can manage their own nested users, oversee framework deployments assigned to them, and manage deployment documents.

```mermaid
graph TD
    Customer[Customer Role] --> Sidebar[Sidebar Menu]

    subgraph Menu Navigation
        Sidebar --> CustomerAdminDashboard[Dashboard /dashboard]
        Sidebar --> CustomerUsers[Profiles Management /users]
        Sidebar --> FrameworkMgmtGroup["Framework Management ▼"]
        Sidebar --> CustomerDocs[My Documents /documents]

        %% Framework Management Dropdown
        FrameworkMgmtGroup --> CustomerDeploy[My Frameworks /deployment-frameworks]
        FrameworkMgmtGroup --> CustomerAssigned[Assigned Frameworks /assigned-frameworks]
    end

    subgraph Detail Pages
        CustomerDeploy -.-> CustomerDeployDetail[My Framework Detail /deployment-frameworks/:id]
        CustomerDocs -.-> CustomerDocsDetail[Document Detail /documents/:id]
    end
```

---

## 5. End User Navigation Flow

Standard users have access to a simplified dashboard and their documents view.

```mermaid
graph TD
    AppUser[User Role] --> Sidebar[Sidebar Menu]

    subgraph Menu Navigation
        Sidebar --> UserDashboard[Dashboard /dashboard]
        Sidebar --> UserDocs[Documents /documents]
    end

    subgraph Detail Pages
        UserDocs -.-> UserDocsDetail[Document Detail /documents/:id]
    end
```
