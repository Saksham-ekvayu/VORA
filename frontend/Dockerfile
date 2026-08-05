FROM node:22-alpine AS builder

# Set working directory
WORKDIR /app

# Production mode
ENV NODE_ENV=production

# -----------------------------
# Build Arguments
# -----------------------------
ARG VITE_API_BASE_URL
ARG VITE_WS_BASE_URL
ARG VITE_INTERNAL_USER_SYNC_API_KEY

# Convert ARG -> ENV for Vite build
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_WS_BASE_URL=${VITE_WS_BASE_URL}
ENV VITE_INTERNAL_USER_SYNC_API_KEY=${VITE_INTERNAL_USER_SYNC_API_KEY}

# Install pnpm
RUN corepack enable && corepack prepare pnpm@10.13.1 --activate

# Copy dependency files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy application files
COPY . .

# Verify variables
RUN echo "API URL: ${VITE_API_BASE_URL}"
RUN echo "WS URL: ${VITE_WS_BASE_URL}"

# Build application
RUN pnpm run build

# ===================================
# Production Stage
# ===================================
FROM nginx:alpine

# Copy frontend build
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Expose nginx port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]