# Deployment Guide: Inventory Reorder Prediction System

Your **FastAPI + Jinja2 + SQLite** web application is fully tested (15/15 tests passing) and configured for deployment.

---

## 🚀 Option 1: Free Cloud Deployment on Render (Recommended)

Render provides free hosting for Python web services with automatic HTTPS and custom domains.

### Steps to Deploy:
1. **Push your code to GitHub**:
   - Create a new GitHub repository (e.g., `inventory-reorder-system`).
   - Push this directory to your GitHub repo.
2. **Log into Render**:
   - Go to [render.com](https://render.com/) and sign in with GitHub.
3. **Create New Web Service**:
   - Click **New +** -> **Web Service**.
   - Connect your GitHub repository.
4. **Configure Settings**:
   - **Name**: `inventory-reorder-system`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
5. **Click "Deploy Web Service"**:
   - In 2-3 minutes, your web application will be live at a public URL like:
     `https://inventory-reorder-system-xxxx.onrender.com`

---

## ⚡ Option 2: Deploy to Railway.app

1. Go to [railway.app](https://railway.app/) and sign in with GitHub.
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select your repository.
4. Railway automatically detects `Procfile` and `requirements.txt` and deploys your service.
5. In **Settings** -> **Networking**, click **Generate Domain** to get your public HTTPS URL.

---

## 🐳 Option 3: Docker Deployment (Any Cloud / VPS / Server)

A production-ready `Dockerfile` has been created in your project root.

```bash
# Build Docker image
docker build -t inventory-system .

# Run container
docker run -d -p 8000:8000 --name inventory-app inventory-system
```
Access the application at `http://localhost:8000`.

---

## 🌐 Option 4: Instant Public URL for Hackathon / Live Demo

If you need a live public URL **right now** for judges or presentation without setting up cloud accounts:

### Using Cloudflare Tunnel:
```powershell
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://127.0.0.1:8000
```
This gives you an instant `https://<random-id>.trycloudflare.com` URL accessible worldwide.

### Using LocalTunnel:
```bash
npx localtunnel --port 8000
```

---

## 🔑 Default Login Credentials
- **Email**: `admin@example.com`
- **Password**: `admin123`
