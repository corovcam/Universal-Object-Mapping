# UOM Assistant Frontend: Setup, Operations, & Contribution Guide

This guide describes how to configure, run, and contribute to the **UOM Assistant** frontend dashboard, separating development and production environments.

---

## 1. Environment Configurations

The frontend uses environment files located at the root of the [`uom-translator-ui`](../../frontend/uom-translator-ui) directory:
*   `.env.development`: Default variables for local developer runs.
*   `.env.production`: Production fallback configurations.
*   `.env.local`: User overrides (contains additional local settings).

### Key Variables

| Variable Name | Description | Default / Example Value |
| :--- | :--- | :--- |
| `LANGGRAPH_API_URL` | Endpoint of the Python LangGraph backend server. | `http://localhost:2024` |
| `NEXT_PUBLIC_LANGGRAPH_API_URL` | Direct client-side SDK API endpoint reference. | (Defaults to Next.js API proxy `/api`) |
| `NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID` | Graph assistant routing identifier. | `universal-object-mapping-translator` |
| `LANGSMITH_TRACING` | Enables trace recording on LangSmith. | `true` |
| `LANGSMITH_API_KEY` | Secret credential key. NECESSARY for LangSmith License Authentication. Not required for local frontend development. | `lsv2_pt_...` |

---

## 2. Local Development Environment Setup

### 2.1 Prerequisites
*   **Node.js**: Version 24+ (Recommended: Node.js 24.16.0 LTS).
*   **Package Manager**: `pnpm` (Version 11+ is recommended for faster installs. Alternatively, `npm` is supported; if changing, update the `package.json` config).

### 2.2 Getting Started (Step-by-Step)

1.  **Configure Environment Variables**:
    Establish your local environment configuration by copying the template file:
    ```bash
    cp .env.example .env.development # For local development
    cp .env.example .env.production # For production builds
    ```
    Modify `.env.development` to specify your local database ports, Ollama settings, or Metacentrum SSH keys.

2.  **Install Project Dependencies**:
    ```bash
    pnpm install
    ```

3.  **Start the Development Server**:
    You can choose to start the entire developer stack (Next.js Dev Server + LangGraph Dev Server + LLMock mock LLM server for request/response fixtures) with:
    ```bash
    pnpm run dev
    ```
    Or launch only the Next.js frontend separately (if you already have the backend running independently on port `2024`):
    ```bash
    pnpm run dev:frontend
    ```

4.  **Verify Application Access**:
    Open your browser to **`http://localhost:3001`** (since Daytona daemon binds to port `3000` by default). Next.js will route and proxy all client-side API requests from `/api/*` to the LangGraph backend API on `http://localhost:2024`.

---

## 3. Production Environment Setup

### 3.1 Prerequisites
*   **Docker Engine**: Version 25+
*   **Docker Compose V2**: Supported

### 3.2 Getting Started (Step-by-Step)

1.  **Configure Production Variables**:
    Establish your production environment configuration by copying the template file:
    ```bash
    cp .env.example .env.production
    ```
    Configure the actual production backend service endpoints (based on your networking setup) and database authorization credentials within `.env.production`.

2.  **Multi-Stage Dockerfile Compilation**:
    The production environment compiles the Next.js dashboard using a multi-stage [Dockerfile](../../frontend/uom-translator-ui/Dockerfile) to optimize image footprint and isolate environment configurations based on [Next.js Official Example](https://github.com/vercel/next.js/tree/canary/examples/with-docker) patterns. The stages include:

    *(Note: The Dockerfile stages shown below are simplified conceptual representations of the actual multi-stage build process.)*
    *   **Stage 1 (Dependencies)**: Installs production and development node packages using frozen lockfile validation:
        ```dockerfile
        FROM node:24-alpine AS deps
        WORKDIR /app
        COPY package.json pnpm-lock.yaml ./
        RUN corepack enable pnpm && pnpm install --frozen-lockfile
        ```
    *   **Stage 2 (Builder)**: Compiles the Next.js pages and generates the optimized static server bundle:
        ```dockerfile
        FROM node:24-alpine AS builder
        WORKDIR /app
        COPY --from=deps /app/node_modules ./node_modules
        COPY . .
        RUN corepack enable pnpm && pnpm build
        ```
    *   **Stage 3 (Runner)**: Copies compiled Next.js standalone assets, configures container health checks via curl, drops root privileges to run as user `node`, and starts the production server.
        ```dockerfile
        FROM node:24-alpine AS runner
        WORKDIR /app
        ENV NODE_ENV=production
        COPY --from=builder /app/.next/standalone ./
        COPY --from=builder /app/.next/static ./.next/static
        COPY --from=builder /app/public ./public
        EXPOSE 3000
        USER node
        CMD ["node", "server.js"]
        ```

3.  **Build and Run the Container**:
    Build the production image and run it locally mapping standard ports:
    ```bash
    # Build production image
    docker build -t uom-translator-ui .

    # Run container mapping port 3000
    docker run -p 3000:3000 --env LANGGRAPH_API_URL="http://host.docker.internal:2024" uom-translator-ui
    ```

---

## 4. Developer Contribution Guidelines

We enforce code style guidelines and compile checks to maintain codebase quality.

### 4.1 Linter & Code Formatting (Biome)
The project uses **Biome** for fast formatting and linting.
*   **Rules Configuration**: [`biome.json`](../../frontend/uom-translator-ui/biome.json)

Before committing changes, run:
```bash
# Run Biome linter check
pnpm run lint

# Auto-fix linting issues and imports
pnpm run lint:fix

# Format files
pnpm run format

# Auto-fix formatting issues
pnpm run format:fix
```

### 4.2 Type Checking & Compilations
To verify that your changes do not introduce type safety errors:
```bash
# Run TypeScript compilation checks and build
pnpm run build
```
Ensure all diagnostics return clean build outputs prior to pushing updates to the repository.
