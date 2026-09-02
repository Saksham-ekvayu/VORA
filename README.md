# VORA Platform

FastAPI microservices for VORA.

## Structure

- `backend/services/`: Contains all domain and AI microservices.
- `backend/shared/`: Shared package used across services.
- `backend/gateway/`: API Gateway.
- `scripts/`: Python and Batch scripts for environment setup and running.

## Local Run

The platform is designed to be run using the provided batch (`.bat`) or shell (`.sh`) scripts which automate setting up environments and running all microservices. If you prefer to set up and run the services manually, please refer to the [Backend README](backend/README.md#manual-service-setup) for detailed instructions.

### 1. Setup Environments

**For Windows:**
Create virtual environments for all services:
```cmd
python scripts\batch\create_venvs.bat
```
Install requirements across all virtual environments:
```cmd
scripts\batch\install_venvs.bat
```

**For Linux / macOS:**
Make the shell scripts executable first:
```bash
chmod +x scripts/shell/*.sh
```
Create virtual environments for all services:
```bash
./scripts/shell/create_venvs.sh
```
Install requirements across all virtual environments:
```bash
./scripts/shell/install_venvs.sh
```

### 2. Database Setup & Migrations (First Time or Schema Changes)

When setting up a completely new database, or if you have modified the SQLAlchemy models in `shared/vora_shared/models/`, you need to generate and apply Alembic migrations. The database schema is centrally managed in the `shared` module.

**For Windows:**
Open your terminal and run the following commands sequentially:

1. Navigate to the shared directory:
   ```cmd
   cd backend\shared
   ```
2. Generate the migration script (this detects all tables/changes):
   ```cmd
   ..\services\authentication-service\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "Initial_migration"
   ```
3. Apply the migration to create tables in the database:
   ```cmd
   ..\services\authentication-service\.venv\Scripts\python.exe -m alembic upgrade head
   ```

**For Linux / macOS:**
Open your terminal and run the following commands sequentially:

1. Navigate to the shared directory:
   ```bash
   cd backend/shared
   ```
2. Generate the migration script (this detects all tables/changes):
   ```bash
   source ../services/authentication-service/.venv/bin/activate
   python -m alembic revision --autogenerate -m "Initial_migration"
   ```
3. Apply the migration to create tables in the database:
   ```bash
   python -m alembic upgrade head
   ```
4. Verify migration status:
   ```bash
   python -m alembic current
   ```

### 3. Run Services

Start all services simultaneously. 

**For Windows:**
If Windows Terminal is installed, it will launch them in tabbed windows. Otherwise, they will open in separate CMD windows.
```cmd
scripts\batch\run_services.bat
```

**For Linux / macOS:**
This will start all services in the background.
```bash
./scripts/shell/run_services.sh
```

### 4. Run Frontend

Open your terminal and run the following commands sequentially:

1. Navigate to the frontend directory:
   ```cmd
   cd frontend
   ```
2. Generate the node_modules or install:
   ```cmd
   pnpm i
   ```
3. Run:
   ```cmd
   pnpm dev
   ```

The API Gateway will be accessible at `http://localhost:8000`.

The Frontend will be accessible at `http://localhost:5173`.
