# Devacia Lead OS - Production Deployment Guide

This guide will walk you through deploying the Devacia Lead OS to production using a hybrid architecture: **Vercel** for the frontend and **Render** for the backend.

---

## Step 1: Push Code to GitHub
Both Vercel and Render deploy automatically from GitHub.

1. Initialize a Git repository (if you haven't already):
   `ash
   git init
   git add .
   git commit -m "Initial commit for production"
   `
2. Create a new private repository on GitHub.
3. Push your code to GitHub:
   `ash
   git remote add origin https://github.com/yourusername/devacia-os.git
   git branch -M main
   git push -u origin main
   `

---

## Step 2: Deploy Backend to Render

We have already included a 
ender.yaml blueprint which automatically sets up your Database, Redis cache, FastAPI server, and Celery web scraper.

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New** -> **Blueprint**.
3. Connect your GitHub account and select your devacia-os repository.
4. Render will automatically detect the 4 services. Click **Apply**.
5. Wait for the services to build and deploy (~5-10 minutes).
6. **Important**: Go to the **Environment** tab of your new **devacia-api** web service and fill in the missing API Keys (e.g. GEMINI_API_KEY, DATAFORSEO_USERNAME, etc.).
7. Copy the public URL of your new API service (e.g., https://devacia-api.onrender.com). You will need this for Vercel.

---

## Step 3: Deploy Frontend to Vercel

1. Log in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New** -> **Project**.
3. Import your devacia-os GitHub repository.
4. In the **Configure Project** screen, make the following critical changes:
   - **Root Directory**: Click "Edit" and select pps/web.
   - **Environment Variables**: Add a new variable:
     - Name: NEXT_PUBLIC_API_URL
     - Value: Paste the URL you copied from Render (e.g., https://devacia-api.onrender.com)
5. Click **Deploy**.

---

## Step 4: Verify the Deployment

1. Once Vercel finishes deploying, visit the public Vercel URL.
2. Log in using the default admin credentials:
   - **Email:** dmin@devacia.com
   - **Password:** dmin123
3. Go to **Settings** immediately and update your password.
4. You're done! Your teammates can now access the CRM securely from anywhere.
