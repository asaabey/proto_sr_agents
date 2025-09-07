# Use Python 3.13 slim image  
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
# Install minimal build tools (for any native deps) and clean cache later
RUN apt-get update && apt-get install -y python3 make g++ && rm -rf /var/lib/apt/lists/*
# Ensure clean dependency install with better fallback
RUN npm ci --no-audit --no-fund --prefer-offline || \
    (echo 'Falling back to npm install due to npm ci failure' && \
     rm -rf node_modules package-lock.json && \
     npm install --no-audit --no-fund)
COPY frontend .
# Verify files copied correctly and build with Vite (skip separate TypeScript check)
RUN ls -la src/lib/ && npx vite build

# --- Backend stage ---
FROM python:3.13-slim AS backend

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_COMPILE_BYTECODE=0
ENV UV_LINK_MODE=copy

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project --no-dev

# Copy project files
COPY . .
# Copy built frontend assets into a static directory
COPY --from=frontend-build /frontend/dist /app/app/static

# Install the project itself
RUN uv sync --frozen --no-dev

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
