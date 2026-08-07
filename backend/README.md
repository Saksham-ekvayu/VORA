# VORA Backend - Setup & Running Guide

## Project Structure

```
backend/
├── gateway/              # API Gateway (Port 8000)
├── services/            # Individual microservices
│   ├── authentication-service/     (Port 7001)
│   ├── profile-service/            (Port 7002)
│   ├── dashboard-service/          (Port 7003)
│   ├── framework-category-service/ (Port 7004)
│   ├── framework-service/          (Port 7005)
│   ├── deployment-framework-service/ (Port 7006)
│   ├── extract-controls-service/   (Port 7007)
│   ├── compliance-agent-service/   (Port 7008)
│   └── ai-analysis-service/        (Port 7009)
├── scripts/             # Setup and management scripts
└── shared/              # Shared Python package
```

## Quick Start

### 1. **Create Virtual Environments**

Run this to create `.venv` folders for all services:

```bash
cd backend/scripts/batch
create_venvs.bat
```

### 2. **Install Dependencies**

Install all service dependencies automatically:

```bash
cd backend/scripts/batch
install_venvs.bat
```

This script will:

- Install the shared package in editable mode
- Create virtual environments for all services
- Install requirements.txt for each service

**Note:** If Windows Terminal is available, it opens tabs for parallel installation. Otherwise, installation runs sequentially.

### 3. **Run All Services**

Start all microservices and the API Gateway:

```bash
cd backend/scripts/batch
run_services.bat
```

**Note:** Services will run in Windows Terminal tabs if available, otherwise in separate CMD windows.

## Service Ports Reference

| Service                      | Port | Route Prefix                                               |
| ---------------------------- | ---- | ---------------------------------------------------------- |
| API Gateway                  | 8000 | `/`                                                        |
| Authentication Service       | 7001 | `/api/auth`                                                |
| Profile Service              | 7002 | `/api/user`, `/api/admin`, `/uploads`                      |
| Dashboard Service            | 7003 | `/api/dashboard/*`                                         |
| Framework Category Service   | 7004 | `/api/framework-categories`                                |
| Framework Service            | 7005 | `/api/framework`                                           |
| Deployment Framework Service | 7006 | `/api/assignment-frameworks`, `/api/deployment-frameworks` |
| Extract Controls Service     | 7007 | `/api/extract`                                             |
| Compliance Agent Service     | 7008 | `/api/compliance-agent`                                    |
| AI Analysis Service          | 7009 | `/api/comparison`, `/api/deployment-gap`                   |

## Available Scripts

### Batch Scripts (Windows)

Located in `backend/scripts/batch/`:

- **`create_venvs.bat`** - Create virtual environments for all services
- **`install_venvs.bat`** - Install all dependencies in virtual environments
- **`run_services.bat`** - Start all services simultaneously
- **`format_code.bat`** - Format code using Black and Isort
- **`remove_venvs.bat`** - Remove all virtual environments

### Python Scripts

Located in `backend/scripts/`:

- **`create_venvs.py`** - Python script to create virtual environments
  - Options: `--install`, `--install-shared`, `--python`, `--root`
- **`remove_venvs.py`** - Python script to remove virtual environments

## Manual Service Setup

If you prefer to set up services individually:

### 1. Create a Virtual Environment

```bash
cd backend/services/authentication-service
python -m venv .venv
```

### 2. Activate Virtual Environment

```bash
# Windows CMD
.venv\Scripts\activate.bat

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Service

```bash
python -m uvicorn app.main:app --host localhost --port 7001 --reload
```

Replace `7001` with the appropriate port from the reference table above.

## Development Workflow

### Format Code

Keep code formatted with Black and Isort:

```bash
cd backend/scripts/batch
format_code.bat
```

### Check Service Health

Once all services are running, check the API Gateway:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "success": true,
  "service": "api-gateway",
  "status": "healthy"
}
```

### Access Service Documentation

Each service exposes API documentation at:

```
http://localhost:<service-port>/docs
```

For example:

- Authentication API: http://localhost:7001/docs
- Profile API: http://localhost:7002/docs
- Dashboard API: http://localhost:7003/docs

## Troubleshooting

### Virtual Environment Issues

If `.venv` folders are corrupted or outdated:

```bash
# Remove all venvs
cd backend/scripts/batch
remove_venvs.bat

# Recreate and reinstall
create_venvs.bat
install_venvs.bat
```

### Port Already in Use

If a port is already in use, check what's running:

```bash
# Find process using port 7001
netstat -ano | findstr :7001
```

Then kill the process or use a different port by modifying the service's `.env` file.

### Dependencies Issues

If you encounter dependency issues:

1. Update pip:

   ```bash
   pip install --upgrade pip
   ```

2. Clear pip cache:

   ```bash
   pip cache purge
   ```

3. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Windows Terminal Not Found

If scripts detect Windows Terminal is not available, services will open in separate CMD windows instead of tabs.

To install Windows Terminal: https://www.microsoft.com/store/productId/9N0DX20HK701

## Environment Variables

Each service has a `.env` file (not tracked in git) and a `.env.example` file (for reference).

To set up a service's environment:

1. Copy `.env.example` to `.env`
2. Update values as needed

Example `.env` file:

```
SERVICE_NAME=authentication-service
PORT=7001
```

## Development Notes

- Services use FastAPI with uvicorn
- Hot reload is enabled by default (code changes auto-reload servers)
- Shared Python package is installed in editable mode (`pip install -e`)
- Black and Isort are used for code formatting

## Next Steps

1. Follow the "Quick Start" section to get services running
2. Access http://localhost:8000 to test the API Gateway
3. Visit individual service docs at http://localhost:<port>/docs
4. Start developing!
