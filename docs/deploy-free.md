# Free demo deployment: Vercel + Render

This setup serves the static English website from Vercel and proxies `/api/*` to the FastAPI service on Render. The Render service runs on the free plan with a single worker and an in-memory SQLite database.

## Important: demo data is temporary

Render Free services spin down after 15 minutes without inbound traffic, and they do not support persistent disks. Field Shift stores accounts, saved fields, observations, conversations, jobs, and analysis results in SQLite. The free setup therefore uses `FIELD_SHIFT_DB=:memory:`: **all saved records disappear whenever the Render process restarts or spins down**. A running analysis can also be interrupted by a restart. The service may take time to wake after inactivity.

Use this deployment for a public demo with sample data. Do not invite farmers to enter sensitive or important field records, and do not describe accounts or reports as persistent. Render documents the free-service limits [here](https://render.com/docs/free) and its filesystem persistence rules [here](https://render.com/docs/disks).

## Files prepared for deployment

- `render.yaml` defines the free Docker web service, health check, temporary database, secure cookies, and a generated expert-inbox key.
- `vercel.json` publishes the `frontend/` directory and proxies `/api/*` to `https://field-shift-api-laith.onrender.com`.
- `backend/Dockerfile` now listens on Render's `PORT` environment variable (default 10000); `compose.yaml` still uses port 8000 for local Docker.
- The backend allows writes from an exact configured frontend origin and can force `Secure` cookies behind the HTTPS proxy.

Vercel external rewrites keep the browser URL on the Vercel site while forwarding API requests to the backend; Vercel does not cache external rewrites by default. See [Vercel rewrite documentation](https://vercel.com/docs/routing/rewrites).

## Deploy order

1. Review and commit the intended project changes to the GitHub branch to deploy. The working tree may include unfinished design work; only deploy the revision you want public.
2. Import the GitHub repository into Vercel. Keep the project root at the repository root and use the `vercel.json` settings (`frontend` output directory; no framework build is required). Note the production origin Vercel assigns. Until Render is deployed, API requests from the site will fail.
3. In Render, create a **Blueprint** from the same repository and select `render.yaml`. Confirm that the service plan is **Free**. When asked for `FIELD_SHIFT_ALLOWED_ORIGINS`, enter the exact Vercel production origin, such as `https://your-project.vercel.app`, without a trailing slash. This allowlist is required for registration, login, saved-field changes, and all other browser write requests. The API hostname in `vercel.json` assumes Render creates `field-shift-api-laith.onrender.com`.
4. Wait for the Render deploy to pass its health check at `/api/v2/health`.
5. If Render assigned a different hostname, update the rewrite destination in `vercel.json` to that exact HTTPS origin and redeploy Vercel.

Do not put API keys in the Vercel project: browser code must not receive private keys. The OpenAI key is optional; without usable API access, the app should show its labelled evidence-based fallback. The generated `FIELD_SHIFT_EXPERT_KEY` belongs only in the Render service environment and should be shared privately with the agronomist team.

## Smoke check after deployment

Open these URLs on the Vercel domain:

- `/` — public home page
- `/workspace/` — account and field workspace
- `/science/` — methods and validation page
- `/api/v2/health` — should return `{"status":"ok"}` through the proxy

Then test sample analysis, registration, sign-in, and an API write. Confirm the browser stores both session cookies with `Secure`, `HttpOnly`, and `SameSite=Strict`. Confirm a request with an unrelated `Origin` is rejected with 403. Treat account data as disposable: loss after an idle spin-down or service restart is expected on this free configuration.

## Move beyond the demo

Before retaining real farmer records, replace in-memory SQLite with a durable managed database, review backups and privacy disclosures, and add a durable job queue for analyses. Render's free web service cannot attach a persistent disk; a persistent disk requires a paid web service and is limited to one service instance. See the [project evidence index](project-evidence.md) for the remaining scientific validation requirements, which hosting does not change.
