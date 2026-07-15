# Deploy Drishti to Zoho Catalyst AppSail

AppSail must launch the FastAPI service on the port supplied through `X_ZOHO_CATALYST_LISTEN_PORT`. Drishti already supports that contract.

## Recommended: Catalyst-managed Python runtime

1. Install and authenticate the Catalyst CLI:

   ```bash
   npm install -g zcatalyst-cli
   catalyst login
   ```

2. From the repository root, associate the directory with the team’s Catalyst project:

   ```bash
   catalyst init
   ```

3. Select **AppSail**, **Catalyst-Managed Runtime**, and a supported Python runtime (Python 3.11 is recommended). Use the repository root as the build path.

4. Set the startup command generated in `app-config.json` to:

   ```text
   sh -c 'uvicorn backend.app:app --host 0.0.0.0 --port ${X_ZOHO_CATALYST_LISTEN_PORT}'
   ```

5. Deploy and verify:

   ```bash
   catalyst deploy appsail
   curl https://YOUR_APPSAIL_ENDPOINT/api/health
   ```

Do not commit `.catalystrc`, access tokens, project secrets, or credentials. The CLI-generated `catalyst.json` and `app-config.json` may be committed after confirming that they contain no secrets and use portable paths.

## Container fallback

The included `Dockerfile` is compatible with AppSail’s custom-runtime path. Catalyst requires a Linux AMD64 OCI image:

```bash
docker build --platform linux/amd64 -t drishti-ksp:latest .
catalyst deploy appsail --name drishti-ksp \
  --source docker://drishti-ksp:latest \
  --port 9000
```

## Post-deployment checklist

- `/api/health` returns HTTP 200.
- `/` loads the dashboard without browser-console errors.
- Dashboard, map, search, profiles, networks, alerts, and district drill-down work.
- Cold-start and warm response times are recorded.
- The public demo uses synthetic data only.
- Production credentials and real police data are absent.
