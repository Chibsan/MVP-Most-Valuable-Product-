# MVP4U - Most Valuable Product

Cross-platform grocery comparison and barcode scanning application with a FastAPI backend, PostgreSQL database, and React Native (Expo) frontend supporting **Mobile** and **Web**.

---

## Prerequisites

- **Container Engine**: [Docker](https://docs.docker.com/get-docker/) or [Podman](https://podman.io/) (with compose plugin)
- **Frontend Runtime**: [Bun](https://bun.sh/) (recommended) or [Node.js](https://nodejs.org/) (v18+)
- **Mobile Testing**: [Expo Go](https://expo.dev/go) app (iOS / Android) or an emulator

---

## 1. Start Backend & Database

```bash
# Using Docker
docker compose up --build

# Or using Podman
podman compose up --build
```

- **API**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`

---

## 2. Start Frontend

Navigate to `frontend/` and install dependencies:

```bash
cd frontend
bun install
```

### Option A: Web (Browser)

```bash
bun run web
```
Opens in your browser at `http://localhost:8081`.
- **Rankings**: Full interactive rankings and category filters.
- **Scanning**: On desktop web browsers, use the manual barcode input (webcams lack native hardware autofocus for 1D barcodes).

### Option B: Mobile (Expo Go)

```bash
bun run start
```
Scan the QR code in **Expo Go** on your phone (or press `a` for Android emulator / `i` for iOS simulator). Uses your phone's rear autofocus camera for live scanning.

---

## 3. Run Backend Tests

```bash
podman exec mvp4u_backend_1 pytest tests
# Or: docker compose exec backend pytest tests
```

---

## Platform Notes

- **Linux**: Both `docker` and `podman` are supported. If using `ufw`, allow inbound ports `8000` (FastAPI) and `8081` (Metro bundler) for mobile device connections.
- **macOS / Windows**: Compatible with Docker Desktop or Podman. Ensure local firewall allows inbound traffic on ports `8000` and `8081` for physical device testing.
- **GitHub Codespaces**: In the **Ports** tab, right-click Port `8000` -> **Port Visibility** -> set to **Public** so the browser frontend can reach the backend.

