# VORA FastAPI Platform

FastAPI microservices for VORA.

## Structure
- `services/`: Contains all domain and AI microservices.
- `shared/`: Shared package used across services.
- `gateway/`: API Gateway.
- `scripts/`: Python and Batch scripts for environment setup and running.

## Local Run (Windows)

The platform is designed to be run using the provided batch scripts which automate setting up environments and running all microservices.

### 1. Setup Environments

Create virtual environments for all services:
```cmd
python scripts\batch\create_service_venvs.bat
```

Install requirements across all virtual environments:
```cmd
scripts\batch\install_venvs.bat
```

### 2. Database Setup & Migrations (First Time or Schema Changes)

When setting up a completely new database, or if you have modified the SQLAlchemy models in `shared/vora_shared/models/`, you need to generate and apply Alembic migrations. The database schema is centrally managed in the `shared` module.

Open your terminal and run the following commands sequentially:

1. Navigate to the shared directory:
   ```cmd
   cd shared
   ```
2. Generate the migration script (this detects all tables/changes):
   ```cmd
   ..\services\authentication-service\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "Initial_migration"
   ```
3. Apply the migration to create tables in the database:
   ```cmd
   ..\services\authentication-service\.venv\Scripts\python.exe -m alembic upgrade head
   ```

### 3. Run Services

Start all services simultaneously. If Windows Terminal is installed, it will launch them in tabbed windows. Otherwise, they will open in separate CMD windows.

```cmd
python scripts\batch\run_services.bat
```

The API Gateway will be accessible at `http://localhost:8000`.
