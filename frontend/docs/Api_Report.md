# Vora Microservice API Report

<div style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">

<!-- Header Panel -->
<div style="background-color: #1e3a8a; color: white; padding: 20px; border-radius: 6px 6px 0 0; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
  <h1 style="margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -0.025em; display: flex; align-items: center; justify-content: center; gap: 12px;">
    🔧 Vora Microservice API Report
  </h1>
  <p style="margin: 8px 0 0 0; font-style: italic; font-size: 15px; color: #93c5fd; font-weight: 500;">
    Service-wise API Inventory & Functionality Overview
  </p>
</div>

<!-- Inventory Table -->
<table style="width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 14px; text-align: left; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">
  <thead>
    <tr style="background-color: #3b82f6; color: white; font-weight: 700;">
      <th style="padding: 12px 16px; border: 1px solid #2563eb; text-align: center; width: 50px;">#</th>
      <th style="padding: 12px 16px; border: 1px solid #2563eb;">Microservice Name</th>
      <th style="padding: 12px 16px; border: 1px solid #2563eb;">Base URL / Prefix</th>
      <th style="padding: 12px 16px; border: 1px solid #2563eb; text-align: center; width: 100px;">Total APIs</th>
      <th style="padding: 12px 16px; border: 1px solid #2563eb; text-align: center; width: 80px;">GET</th>
      <th style="padding: 12px 16px; border: 1px solid #2563eb; text-align: center; width: 80px;">POST</th>
      <th style="padding: 12px 16px; border: 1px solid #2563eb; text-align: center; width: 100px;">PUT/PATCH</th>
      <th style="padding: 12px 16px; border: 1px solid #2563eb; text-align: center; width: 80px;">DELETE</th>
      <th style="padding: 12px 16px; border: 1px solid #2563eb; text-align: center; width: 100px;">DB Collections</th>
    </tr>
  </thead>
  <tbody>
    <!-- Auth Service -->
    <tr style="background-color: #ffffff;">
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600;">1</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-weight: 600; color: #1e293b;">Auth Service</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-family: monospace; color: #0f766e;">/api/auth</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 700; color: #1e3a8a;">11</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; color: #64748b;">0</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #0f766e;">11</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; color: #64748b;">0</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; color: #64748b;">0</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #7c3aed;">2</td>
    </tr>
    <!-- Profile Service -->
    <tr style="background-color: #f8fafc;">
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600;">2</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-weight: 600; color: #1e293b;">Profile Service</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-family: monospace; color: #0f766e;">/api/profile <br> /api/users</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 700; color: #1e3a8a;">15</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #2563eb;">5</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #0f766e;">3</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #d97706;">5</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #dc2626;">2</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #7c3aed;">3</td>
    </tr>
    <!-- Framework Category Service -->
    <tr style="background-color: #ffffff;">
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600;">3</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-weight: 600; color: #1e293b;">Framework Category Service</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-family: monospace; color: #0f766e;">/api/admin/framework-categories <br> /api/admin/framework-access <br> /api/admin/frameworks</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 700; color: #1e3a8a;">12</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #2563eb;">5</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #0f766e;">2</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #d97706;">4</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #dc2626;">1</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #7c3aed;">5</td>
    </tr>
    <!-- Framework Service -->
    <tr style="background-color: #f8fafc;">
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600;">4</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-weight: 600; color: #1e293b;">Framework Service</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-family: monospace; color: #0f766e;">/api/frameworks</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 700; color: #1e3a8a;">21</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #2563eb;">8</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #0f766e;">7</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #d97706;">3</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #dc2626;">3</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #7c3aed;">6</td>
    </tr>
    <!-- Deployment Framework Service -->
    <tr style="background-color: #ffffff;">
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600;">5</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-weight: 600; color: #1e293b;">Deployment Framework Service</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-family: monospace; color: #0f766e;">/api/deployment-frameworks</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 700; color: #1e3a8a;">17</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #2563eb;">7</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #0f766e;">2</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #d97706;">5</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #dc2626;">3</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #7c3aed;">5</td>
    </tr>
    <!-- Deployment Document Service -->
    <tr style="background-color: #f8fafc;">
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600;">6</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-weight: 600; color: #1e293b;">Deployment Document Service</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-family: monospace; color: #0f766e;">/api/deployment-documents</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 700; color: #1e3a8a;">10</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #2563eb;">6</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #0f766e;">1</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #d97706;">1</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #dc2626;">2</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #7c3aed;">4</td>
    </tr>
    <!-- Dashboard Service -->
    <tr style="background-color: #ffffff;">
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600;">7</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-weight: 600; color: #1e293b;">Dashboard Service</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; font-family: monospace; color: #0f766e;">/api/dashboard</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 700; color: #1e3a8a;">3</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #2563eb;">3</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; color: #64748b;">0</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; color: #64748b;">0</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; color: #64748b;">0</td>
      <td style="padding: 12px 16px; border: 1px solid #e2e8f0; text-align: center; font-weight: 600; color: #7c3aed;">9</td>
    </tr>
    <!-- Total Summary Row -->
    <tr style="background-color: #ea580c; color: white; font-weight: 800; font-size: 15px; border-radius: 0 0 6px 6px; box-shadow: 0 -2px 10px rgba(0,0,0,0.05);">
      <td style="padding: 14px 16px; border: 1px solid #c2410c; text-align: center;" colspan="3">TOTAL</td>
      <td style="padding: 14px 16px; border: 1px solid #c2410c; text-align: center; font-size: 16px;">89</td>
      <td style="padding: 14px 16px; border: 1px solid #c2410c; text-align: center; font-size: 16px;">34</td>
      <td style="padding: 14px 16px; border: 1px solid #c2410c; text-align: center; font-size: 16px;">26</td>
      <td style="padding: 14px 16px; border: 1px solid #c2410c; text-align: center; font-size: 16px;">18</td>
      <td style="padding: 14px 16px; border: 1px solid #c2410c; text-align: center; font-size: 16px;">11</td>
      <td style="padding: 14px 16px; border: 1px solid #c2410c; text-align: center; font-size: 16px;">34</td>
    </tr>
  </tbody>
</table>

---

## Detailed Endpoint Registry

Below is the complete catalog of all backend microservice routes mapped directly from the codebase.

### 🔑 1. Auth Service (`authentication-service`)

- **Base URL / Gateway Routing:** `http://localhost:8000/api/auth`
- **Port:** `7001`

| HTTP Method | Path                   | Description                                       |
| :---------- | :--------------------- | :------------------------------------------------ |
| `POST`      | `/register`            | Register a new customer organization admin        |
| `POST`      | `/verify-otp`          | Verify user registration/login email OTP          |
| `POST`      | `/resend-otp`          | Trigger resending of verification OTP             |
| `POST`      | `/login`               | Authenticate credentials & generate access tokens |
| `POST`      | `/forgot-password`     | Request password reset token / OTP                |
| `POST`      | `/reset-password`      | Reset password using verified OTP                 |
| `POST`      | `/verify-email`        | Request email verification code                   |
| `POST`      | `/logout`              | Invalidate current session token                  |
| `POST`      | `/logout-all-devices`  | Invalidate all sessions globally                  |
| `POST`      | `/change-password`     | Invalidate previous & update with new password    |
| `POST`      | `/internal/users/sync` | Force dynamic user sync across active nodes       |

---

### 👤 2. Profile Service (`profile-service`)

- **Base URL / Gateway Routing:** `http://localhost:8000/api/profile` and `http://localhost:8000/api/users`
- **Port:** `7002`

| HTTP Method | Path                                 | Description                                     |
| :---------- | :----------------------------------- | :---------------------------------------------- |
| `GET`       | `/profile/`                          | Fetch authenticated user's profile              |
| `PATCH`     | `/profile/update`                    | Modify personal profile fields                  |
| `POST`      | `/profile/avatar`                    | Upload or update personal avatar file           |
| `GET`       | `/users/all-users`                   | Fetch list of all system users (paginated)      |
| `GET`       | `/users/:id`                         | Fetch specific user details by ID               |
| `POST`      | `/users/create`                      | Provision a new user account (Admin/Expert)     |
| `PATCH`     | `/users/:id`                         | Update existing user details                    |
| `PATCH`     | `/users/:id/toggle-status`           | Toggle user status (Active/Inactive)            |
| `DELETE`    | `/users/:id`                         | Remove a user account permanently               |
| `GET`       | `/users/customers`                   | Fetch list of all organizations                 |
| `GET`       | `/users/customers/:id`               | Fetch details of a single organization          |
| `POST`      | `/users/customers`                   | Register a new customer organization            |
| `PATCH`     | `/users/customers/:id`               | Update organization details                     |
| `PATCH`     | `/users/customers/:id/toggle-status` | Toggle organization status (Active/Inactive)    |
| `DELETE`    | `/users/customers/:id`               | Delete customer organization and related scopes |

---

### 📂 3. Framework Category Service (`framework-category-service`)

- **Base URL / Gateway Routing:** `/api/admin/framework-categories`, `/api/admin/framework-access`, `/api/admin/frameworks`
- **Port:** `7004`

| HTTP Method | Path                                            | Description                                   |
| :---------- | :---------------------------------------------- | :-------------------------------------------- |
| `GET`       | `/categories/`                                  | Fetch all framework category groups           |
| `GET`       | `/categories/:id`                               | Get details of a single category group        |
| `POST`      | `/categories/`                                  | Create a new framework category group         |
| `PUT`       | `/categories/:id`                               | Update category configurations                |
| `DELETE`    | `/categories/:id`                               | Delete category group                         |
| `GET`       | `/access/`                                      | List all current framework access requests    |
| `GET`       | `/access/:id`                                   | Retrieve single access request details        |
| `POST`      | `/access/assign`                                | Direct direct-assignment of access to experts |
| `PUT`       | `/access/approve/:id`                           | Approve pending access requests               |
| `PUT`       | `/access/reject/:id`                            | Reject access requests                        |
| `PUT`       | `/access/revoke/:expertId/:frameworkCategoryId` | Revoke specific framework category access     |
| `GET`       | `/approved/`                                    | Get list of approved frameworks local replica |

---

### 📋 4. Framework Service (`framework-service`)

- **Base URL / Gateway Routing:** `http://localhost:8000/api/frameworks`
- **Port:** `7005`

| HTTP Method | Path                                                            | Description                                  |
| :---------- | :-------------------------------------------------------------- | :------------------------------------------- |
| `GET`       | `/categories/available`                                         | List categories available for assignment     |
| `GET`       | `/all-frameworks`                                               | List all system frameworks                   |
| `GET`       | `/:id`                                                          | Get individual framework metadata & versions |
| `POST`      | `/:id/approve`                                                  | Approve framework publication status         |
| `POST`      | `/:id/reject`                                                   | Reject framework publication status          |
| `POST`      | `/assign-framework-to-customer`                                 | Link a framework to customer organization    |
| `POST`      | `/upload`                                                       | Upload a new framework file/version          |
| `PUT`       | `/:id`                                                          | Edit details of a framework                  |
| `DELETE`    | `/:id`                                                          | Delete a framework package                   |
| `GET`       | `/:frameworkId/files`                                           | Get files linked to the framework            |
| `GET`       | `/:frameworkId/files/:fileId`                                   | Fetch file specifications                    |
| `GET`       | `/:frameworkId/files/:fileId/download`                          | Stream framework source file download        |
| `GET`       | `/:frameworkId/files/:fileId/preview`                           | Render preview of framework documentation    |
| `DELETE`    | `/:frameworkId/files/:fileId`                                   | Invalidate and delete file                   |
| `POST`      | `/:frameworkId/files/:fileId/ai-upload`                         | Dispatch file to AI engine for indexing      |
| `POST`      | `/:id/file-versions/:fileVersion/controls`                      | Add a control standard to version            |
| `PATCH`     | `/:id/file-versions/:fileVersion/controls/:controlId`           | Update control details                       |
| `PATCH`     | `/:id/file-versions/:fileVersion/controls/:controlId/weightage` | Invalidate weight & update                   |
| `DELETE`    | `/:id/file-versions/:fileVersion/controls/:controlId`           | Remove control from version standards        |
| `POST`      | `/access/:frameworkCategoryId/request`                          | Submit new framework category request        |
| `GET`       | `/access/my-access`                                             | Fetch list of category request history       |

---

### 🏗️ 5. Deployment Framework Service (`deployment-framework-service`)

- **Base URL / Gateway Routing:** `http://localhost:8000/api/deployment-frameworks`
- **Port:** `7006`

| HTTP Method | Path                                                                       | Description                              |
| :---------- | :------------------------------------------------------------------------- | :--------------------------------------- |
| `GET`       | `/frameworks/assigned`                                                     | Fetch organization's assigned frameworks |
| `GET`       | `/frameworks/assignments`                                                  | List all framework assignments           |
| `GET`       | `/frameworks/assignments/:id`                                              | Fetch single assignment specifications   |
| `PATCH`     | `/frameworks/assignments/:frameworkId/:customerId/revoke`                  | Revoke organization framework assignment |
| `GET`       | `/frameworks/`                                                             | Fetch deployment compliance frameworks   |
| `GET`       | `/frameworks/client-controls`                                              | Fetch list of compliance controls        |
| `GET`       | `/frameworks/:id`                                                          | Retrieve deployment framework details    |
| `PUT`       | `/frameworks/:id`                                                          | Update framework configuration details   |
| `DELETE`    | `/frameworks/:id`                                                          | Delete compliance mapping package        |
| `POST`      | `/frameworks/upload`                                                       | Upload customer deployment logs/details  |
| `GET`       | `/frameworks/:frameworkId/files/:fileId/preview`                           | Preview file configuration parameters    |
| `DELETE`    | `/frameworks/:frameworkId/packages/:packageVersion`                        | Delete framework version package         |
| `POST`      | `/frameworks/:id/file-versions/:fileVersion/controls`                      | Append compliance control                |
| `PATCH`     | `/frameworks/:id/file-versions/:fileVersion/controls/applicability`        | Toggle control scope                     |
| `PATCH`     | `/frameworks/:id/file-versions/:fileVersion/controls/:controlId/weightage` | Update weightage score                   |
| `PUT`       | `/frameworks/:id/file-versions/:fileVersion/controls/:controlId`           | Modify control parameters                |
| `DELETE`    | `/frameworks/:id/file-versions/:fileVersion/controls/:controlId`           | Invalidate control record                |

---

### 📄 6. Deployment Document Service (`deployment-document-service`)

- **Base URL / Gateway Routing:** `http://localhost:8000/api/deployment-documents`
- **Port:** `7007`

| HTTP Method | Path                                            | Description                              |
| :---------- | :---------------------------------------------- | :--------------------------------------- |
| `GET`       | `/documents/`                                   | Get all uploaded deployment files        |
| `GET`       | `/documents/:id`                                | Fetch single document specifications     |
| `PUT`       | `/documents/:id`                                | Edit document meta specifications        |
| `DELETE`    | `/documents/:id`                                | Delete deployment document record        |
| `POST`      | `/documents/upload`                             | Upload a new deployment document file    |
| `GET`       | `/documents/:documentId/files`                  | Get list of version files                |
| `GET`       | `/documents/:documentId/files/:fileId`          | Fetch file specifications                |
| `GET`       | `/documents/:documentId/files/:fileId/download` | Download deployment document source file |
| `GET`       | `/documents/:documentId/files/:fileId/preview`  | View document preview                    |
| `DELETE`    | `/documents/:documentId/files/:fileId`          | Invalidate and delete file               |

---

### 📊 7. Dashboard Service (`dashboard-service`)

- **Base URL / Gateway Routing:** `http://localhost:8000/api/dashboard`
- **Port:** `7003`

| HTTP Method | Path                  | Description                                        |
| :---------- | :-------------------- | :------------------------------------------------- |
| `GET`       | `/admin/analytics`    | Retrieve global analytics (Admin)                  |
| `GET`       | `/expert/analytics`   | Retrieve workload and evaluation progress (Expert) |
| `GET`       | `/customer/analytics` | Retrieve organization compliance stats (Customer)  |

## </div>

## Database Schema Overview

Each microservice has its own MongoDB database with specific collections (tables). Below is the detailed schema information for each service.

### 🔑 1. Auth Service (`authentication-service`)

- **Port:** `7001`
- **Database:** MongoDB

| Collection          | Description                      | Key Fields                                                                                                  |
| :------------------ | :------------------------------- | :---------------------------------------------------------------------------------------------------------- |
| **users**           | User accounts for authentication | tenantId, avatar, name, email, phone, role, password, isEmailVerified, isActive, otp, tokenVersion, address |
| **processed-event** | RabbitMQ event tracking          | eventId, eventType, userId, sequenceNumber, data, processedAt                                               |

---

### 👤 2. Profile Service (`profile-service`)

- **Port:** `7002`
- **Database:** MongoDB

| Collection          | Description               | Key Fields                                                                                                |
| :------------------ | :------------------------ | :-------------------------------------------------------------------------------------------------------- |
| **users**           | User profiles and details | tenantId, name, email, phone, role, designation, isEmailVerified, isActive, avatar, address, tokenVersion |
| **customers**       | Customer organizations    | tenantId, name, email, phone, isActive, avatar, address                                                   |
| **processed-event** | RabbitMQ event tracking   | eventId, eventType, userId, sequenceNumber, data, processedAt                                             |

---

### 📂 3. Framework Category Service (`framework-category-service`)

- **Port:** `7004`
- **Database:** MongoDB

| Collection                    | Description                              | Key Fields                                                                                         |
| :---------------------------- | :--------------------------------------- | :------------------------------------------------------------------------------------------------- |
| **users**                     | Replica user records                     | tenantId, avatar, name, email, role, tokenVersion, isActive                                        |
| **framework-categories**      | Framework category definitions           | code, frameworkCategoryName, description, isActive, createdBy, updatedBy                           |
| **frameworks**                | Framework replica from framework-service | frameworkCode, frameworkName, frameworkVersion, currentFileVersion, approval                       |
| **framework-category-access** | Expert framework access requests         | expertId, frameworkCategoryId, frameworkCode, status, requestedBy, approval, rejection, revocation |
| **processed-event**           | RabbitMQ event tracking                  | eventId, eventType, userId, sequenceNumber, data, processedAt                                      |

---

### 📋 4. Framework Service (`framework-service`)

- **Port:** `7005`
- **Database:** MongoDB

| Collection                    | Description                                | Key Fields                                                                                                                  |
| :---------------------------- | :----------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------- |
| **users**                     | Replica user records for framework uploads | tenantId, avatar, name, email, role, tokenVersion, isActive                                                                 |
| **customers**                 | Customer organizations                     | tenantId, name, email, phone, isActive, avatar, address                                                                     |
| **frameworks**                | Main framework definitions                 | frameworkName, frameworkVersion, frameworkCategoryId, frameworkCode, uploadedBy, currentFileVersion, fileVersions, approval |
| **framework-categories**      | Framework category definitions             | code, frameworkCategoryName, description, isActive, createdBy, updatedBy                                                    |
| **framework-category-access** | Expert framework access management         | expertId, frameworkCategoryId, frameworkCode, status, requestedBy, approval, rejection, revocation                          |
| **processed-event**           | RabbitMQ event tracking                    | eventId, eventType, userId, sequenceNumber, data, processedAt                                                               |

---

### 🏗️ 5. Deployment Framework Service (`deployment-framework-service`)

- **Port:** `7006`
- **Database:** MongoDB

| Collection                | Description                      | Key Fields                                                                                                                                          |
| :------------------------ | :------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------- |
| **users**                 | Replica user records             | tenantId, avatar, name, email, role, tokenVersion, isActive, createdBy                                                                              |
| **customers**             | Customer organizations           | tenantId, name, email, phone, isActive, avatar, address                                                                                             |
| **deployment-frameworks** | Deployment framework definitions | tenantId, frameworkName, frameworkCategoryId, frameworkCode, frameworkVersion, uploadedBy, currentPackageVersion, packages                          |
| **framework-assignments** | Customer framework assignments   | tenantId, customerId, frameworkId, frameworkCode, frameworkName, frameworkVersion, currentFileVersion, fileVersions, status, assignment, revocation |
| **processed-event**       | RabbitMQ event tracking          | eventId, eventType, tenantId, userId, sequenceNumber, data, processedAt                                                                             |

---

### 📄 6. Deployment Document Service (`deployment-document-service`)

- **Port:** `7007`
- **Database:** MongoDB

| Collection                | Description                            | Key Fields                                                                                                                           |
| :------------------------ | :------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------- |
| **users**                 | Replica user records                   | tenantId, avatar, name, email, role, tokenVersion, isActive, createdBy                                                               |
| **deployment-documents**  | Uploaded deployment documents          | tenantId, documentName, uploadedBy, deploymentFrameworkId, controlId, controlName, deploymentPoint, currentFileVersion, fileVersions |
| **deployment-frameworks** | Replica framework for document linking | frameworkName, frameworkCode, frameworkVersion, currentPackageVersion, packages                                                      |
| **processed-event**       | RabbitMQ event tracking                | eventId, eventType, tenantId, userId, sequenceNumber, data, processedAt                                                              |

---

### 📊 7. Dashboard Service (`dashboard-service`)

- **Port:** `7003`
- **Database:** MongoDB

| Collection                    | Description                      | Key Fields                                                                                  |
| :---------------------------- | :------------------------------- | :------------------------------------------------------------------------------------------ |
| **users**                     | Replica user records             | tenantId, avatar, name, email, role, tokenVersion, isActive, createdBy                      |
| **customers**                 | Customer organizations           | tenantId, name, email, phone, isActive, avatar, address                                     |
| **frameworks**                | Framework replica for analytics  | frameworkName, frameworkCategoryId, uploadedBy, currentFileVersion, fileVersions, approval  |
| **framework-categories**      | Framework category replica       | frameworkCategoryName, isActive                                                             |
| **framework-assignment**      | Customer framework assignments   | customerId, frameworkId, status                                                             |
| **framework-category-access** | Expert framework access          | expertId, frameworkCategoryId, status                                                       |
| **deployment-documents**      | Document replica for analytics   | tenantId, documentName, uploadedBy, deploymentFrameworkId, currentFileVersion, fileVersions |
| **deployment-frameworks**     | Framework replica for dashboards | tenantId, frameworkName, frameworkVersion, uploadedBy, currentPackageVersion, packages      |
| **processed-event**           | RabbitMQ event tracking          | eventId, eventType, userId, sequenceNumber, data, processedAt                               |

---

## Summary of All Collections

| Collection Name               | Used By Services                                                                    |
| :---------------------------- | :---------------------------------------------------------------------------------- |
| **users**                     | All 7 services (replicated for reference)                                           |
| **customers**                 | profile-service, dashboard-service, framework-service, deployment-framework-service |
| **frameworks**                | dashboard-service, framework-service, framework-category-service                    |
| **framework-categories**      | dashboard-service, framework-service, framework-category-service                    |
| **framework-assignment**      | dashboard-service                                                                   |
| **framework-assignments**     | deployment-framework-service                                                        |
| **framework-category-access** | dashboard-service, framework-service, framework-category-service                    |
| **deployment-documents**      | dashboard-service, deployment-document-service                                      |
| **deployment-frameworks**     | dashboard-service, deployment-document-service, deployment-framework-service        |
| **processed-event**           | All 7 services (RabbitMQ event logging)                                             |
