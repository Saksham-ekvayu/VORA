# -------- BASE IMAGE --------
FROM python:3.11-slim

# -------- ENVIRONMENT --------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -------- WORKDIR --------
WORKDIR /app

# -------- SYSTEM DEPENDENCIES --------
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# -------- COPY REQUIREMENTS --------
COPY requirements.txt .

# -------- INSTALL PYTHON PACKAGES --------
RUN pip install --no-cache-dir -r requirements.txt

# -------- COPY PROJECT --------
COPY . .

# -------- CREATE NON-ROOT USER --------
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# -------- EXPOSE PORT --------
EXPOSE 8099

# -------- START FASTAPI APPLICATION --------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8099"]