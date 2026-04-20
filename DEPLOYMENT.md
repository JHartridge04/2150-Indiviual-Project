# Deployment Guide

Backend → Render (Python/Flask + Gunicorn)  
Frontend → Vercel (React / Create React App)

---

## Prerequisites

- GitHub repo with the latest code pushed to `main`
- [Render](https://render.com) account (free tier is fine)
- [Vercel](https://vercel.com) account (free tier is fine)
- Supabase project already set up with the database migrations run

---

## 1 — Deploy the Backend (Render)

### 1.1 Create the web service

1. Log in to Render → click **New → Web Service**
2. Connect your GitHub repo
3. Render detects `backend/render.yaml` automatically — confirm the settings:
   - **Name:** `style-assistant-backend`
   - **Root directory:** `backend`
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
4. Click **Create Web Service**

### 1.2 Set environment variables

In the Render dashboard → your service → **Environment**, add each variable:

| Key | Value / where to find it |
|---|---|
| `SUPABASE_URL` | Supabase dashboard → Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Supabase dashboard → Settings → API → `anon public` key |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `RAPIDAPI_KEY` | RapidAPI dashboard → your app key |
| `CORS_ORIGINS` | `http://localhost:3000` for now — **update after Vercel deploy** (see step 3.2) |

### 1.3 Note your backend URL

After the first deploy completes Render shows a URL like:

```
https://style-assistant-backend.onrender.com
```

Copy this — you'll need it for the frontend env var and for CORS.

> **Free tier cold start:** Render spins down idle services after 15 minutes of inactivity. The first request after that takes ~30 seconds. This is normal on the free tier.

---

## 2 — Deploy the Frontend (Vercel)

### 2.1 Import the project

1. Log in to Vercel → **New Project → Import Git Repository**
2. Select your GitHub repo
3. Set **Root Directory** to `frontend`
4. Framework preset should auto-detect as **Create React App**

### 2.2 Set environment variables

In the Vercel project → **Settings → Environment Variables**, add:

| Key | Value |
|---|---|
| `REACT_APP_SUPABASE_URL` | Same as `SUPABASE_URL` above |
| `REACT_APP_SUPABASE_ANON_KEY` | Same as `SUPABASE_ANON_KEY` above |
| `REACT_APP_API_BASE_URL` | Your Render backend URL, e.g. `https://style-assistant-backend.onrender.com` |

### 2.3 Deploy

Click **Deploy**. Vercel builds and assigns a URL like:

```
https://your-app.vercel.app
```

Copy this for the next steps.

---

## 3 — Post-deploy Supabase & CORS config

### 3.1 Add the Vercel URL to Supabase redirect URLs

Supabase → **Authentication → URL Configuration → Redirect URLs** → Add:

```
https://your-app.vercel.app/reset-password
```

Without this, password-reset email links will be blocked by Supabase.

### 3.2 Update CORS in Render

Render dashboard → your backend service → **Environment** → update `CORS_ORIGINS`:

```
http://localhost:3000,https://your-app.vercel.app
```

Trigger a redeploy (or Render redeploys automatically on env var change).

---

## 4 — Smoke test checklist

Work through these in order after deployment:

- [ ] Sign up with a new account
- [ ] Confirm email (check inbox), then log in
- [ ] Upload a photo and run style analysis
- [ ] View recommendations
- [ ] Add an item to the wardrobe
- [ ] Build an outfit around a wardrobe item
- [ ] Edit your style profile
- [ ] Change password (Profile page)
- [ ] Log out, then use "Forgot password?" on the login page and confirm the reset email arrives
- [ ] Click the reset link, set a new password, confirm redirect to login

---

## 5 — Troubleshooting

**CORS errors in the browser console**  
The `CORS_ORIGINS` env var on Render doesn't include the Vercel URL. Update it (comma-separated) and redeploy.

**"Auth session missing" / Supabase errors**  
Double-check `REACT_APP_SUPABASE_URL` and `REACT_APP_SUPABASE_ANON_KEY` in Vercel match your Supabase project exactly.

**Password reset link says "invalid or expired"**  
The Vercel URL hasn't been added to Supabase → Authentication → URL Configuration → Redirect URLs.

**First request after idle is very slow (~30 s)**  
Normal on Render's free tier. The service cold-starts on the first request after inactivity. Subsequent requests are fast.

**Recommendations return nothing / product search fails**  
Check `RAPIDAPI_KEY` is set correctly in Render. Test the `/api/health` endpoint directly to confirm the backend is live.

**Frontend shows blank page after deploy**  
Usually a missing env var. Check the Vercel build logs for errors about missing `REACT_APP_*` variables.
