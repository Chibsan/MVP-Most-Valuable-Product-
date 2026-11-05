# MVP4U - Most Valuable Product

Cross-platform grocery comparison and barcode scanning application with a FastAPI backend, PostgreSQL database, and React Native (Expo) mobile frontend.

---

## Prerequisites

- **Container Engine**: [Docker](https://docs.docker.com/get-docker/) or [Podman](https://podman.io/) (with compose plugin)
- **Frontend Runtime**: [Bun](https://bun.sh/) (recommended) or [Node.js](https://nodejs.org/) (v18+)
- **Mobile Testing**: [Expo Go](https://expo.dev/go) app on your physical smartphone (iOS / Android) or an Android/iOS emulator.

---

## Getting Started

### 1. Run the Backend & Database

The backend and PostgreSQL database run containerized:

```bash
# Using Docker
docker compose up --build

# Or using Podman
podman compose up --build
```

- **API Base**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

---

### 2. Run the Mobile Frontend

Open a new terminal window:

```bash
cd frontend

# Install dependencies
bun install

# Start the Expo development server
bun run start
```

- Open the **Expo Go** app on your phone and scan the displayed QR code.
- Ensure your phone and development machine are connected to the same local Wi-Fi network.
- To run on an emulator, press `a` (Android) or `i` (iOS).

---

## Platform Notes

- **Linux**: Both `docker` and `podman` are supported. Podman runs daemonless and rootless out-of-the-box (`sudo pacman -S podman podman-compose` on Arch/CachyOS).
- **macOS**: Compatible with Docker Desktop, Podman Desktop, or OrbStack.
- **Windows**: Use Docker Desktop with the WSL 2 backend, or Podman via WSL 2. Ensure Windows Defender Firewall allows inbound traffic on port `8000` (FastAPI) and `8081` (Metro bundler) for physical device scanning.

