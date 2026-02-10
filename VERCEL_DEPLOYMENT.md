# Vercel Deployment Guide for HX Stall Analysis

## Overview
This guide explains how to deploy the HX Stall Analysis tool to Vercel from GitHub.

## Prerequisites
- GitHub account with the HXStall repository
- Vercel account (free tier works fine)
- Git installed locally

## Project Structure for Vercel

```
HXStall/
├── api/                          # Serverless functions
│   ├── main.py                   # FastAPI application
│   ├── calculation_engine.py     # Core calculation logic
│   └── validation.py             # Input validation
├── frontend/                     # Static files
│   ├── index.html               # Main app interface
│   └── help.html                # User guide
├── requirements.txt             # Python dependencies
├── vercel.json                  # Vercel configuration
└── .vercelignore               # Files to exclude from deployment
```

## Deployment Steps

### Option 1: Deploy from GitHub (Recommended)

1. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com) and sign in
   - Click "Add New..." → "Project"
   - Import your GitHub repository: `jhfish/HXStall`

2. **Configure Project**:
   - **Framework Preset**: Other
   - **Root Directory**: Leave as `.` (root)
   - **Build Command**: Leave empty (static + serverless)
   - **Output Directory**: Leave empty
   
3. **Environment Variables** (if needed):
   - None required for this project

4. **Deploy**:
   - Click "Deploy"
   - Wait for build to complete (~1-2 minutes)
   - Your app will be available at: `https://your-project.vercel.app`

### Option 2: Deploy from CLI

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   cd HXStall
   vercel login
   ```

3. **Deploy**:
   ```bash
   vercel --prod
   ```

4. **Follow prompts**:
   - Link to existing project or create new
   - Confirm settings
   - Wait for deployment

## Configuration Files

### vercel.json
Routes all `/api/*` requests to the Python serverless function and serves the frontend for all other paths.

### requirements.txt
Essential Python dependencies:
- `fastapi==0.111.0` - Web framework
- `iapws==1.5.3` - Steam property calculations (IF-97)
- `pydantic==2.6.1` - Data validation
- `numpy==1.26.4` - Numerical computations

### .vercelignore
Excludes development files from deployment to keep the serverless bundle size small.

## Troubleshooting

### 404 NOT_FOUND Error
**Cause**: Missing frontend files or incorrect routing
**Solution**: 
- Ensure `frontend/index.html` exists
- Check `vercel.json` routes configuration
- Redeploy with `vercel --prod`

### FUNCTION_INVOCATION_FAILED Error
**Cause**: Missing Python dependencies or import errors
**Solution**:
- Check that `api/` folder contains all three files:
  - `main.py`
  - `calculation_engine.py`
  - `validation.py`
- Verify `requirements.txt` includes `iapws` and `pydantic`
- Check Vercel logs: `vercel logs [deployment-url]`

### Module Import Errors
**Cause**: Import paths referencing parent directories
**Solution**:
- All imports in `api/main.py` should be relative to the `api/` folder
- Do NOT use `sys.path.insert()` or parent directory imports
- Example: `from calculation_engine import ...` (not `from ../calculation_engine`)

### Large Bundle Size / Slow Cold Starts
**Cause**: Including unnecessary files in deployment
**Solution**:
- Update `.vercelignore` to exclude dev files
- Remove heavy dependencies not needed for serverless functions

## Testing the Deployment

### 1. Frontend
Visit your Vercel URL to load the web interface:
```
https://your-project.vercel.app
```

### 2. API Health Check
Test the API endpoint:
```bash
curl https://your-project.vercel.app/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "calculation_engine": "validated (91.2% Excel parity)"
}
```

### 3. Full Analysis
Run a test analysis from the web interface or via API:
```bash
curl -X POST https://your-project.vercel.app/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "operating_mode": "mode1",
    "duty_100pct": 1257060,
    "surface_area": 58.71,
    "htc_clean": 140,
    "htc_service": 110,
    "process_inlet_temp": 0,
    "process_outlet_temp": 300,
    "backpressure_max": 70
  }'
```

## Vercel Limits (Free Tier)

- **Serverless Function Size**: 50 MB (compressed)
- **Execution Time**: 10 seconds max
- **Bandwidth**: 100 GB/month
- **Deployments**: Unlimited

This application fits well within free tier limits.

## Continuous Deployment

Once connected to GitHub:
- Every push to `main` branch automatically deploys to production
- Pull requests create preview deployments
- Rollback to previous deployments via Vercel dashboard

## Custom Domain (Optional)

To use your own domain:
1. Go to Project Settings → Domains
2. Add your domain
3. Update DNS records as instructed
4. SSL certificate is automatically provisioned

## Support

For issues:
- Check Vercel logs: Project → Deployments → [deployment] → Function Logs
- Review this guide and troubleshooting section
- Check Vercel documentation: [vercel.com/docs](https://vercel.com/docs)

---

**Last Updated**: February 10, 2026
**Vercel Documentation**: https://vercel.com/docs
**Project Repository**: https://github.com/jhfish/HXStall
