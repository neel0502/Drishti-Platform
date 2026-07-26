# Deploy Drishti to Zoho Catalyst AppSail

The current development URL retains the original Catalyst app identifier. Rename and redeploy the app to change the URL.

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

3. Select **AppSail**, **Catalyst-Managed Runtime**, and Python 3.11. The committed configuration uses `.appsail-build` as the deployable build path.

4. Build the AppSail bundle before deployment. The script creates a clean bundle and installs Linux AMD64 Python wheels so native analytics dependencies are compatible with AppSail:

   ```bash
   ./scripts/build_appsail.sh
   ```

   Its startup command is:

   ```text
   sh -c 'python3 -m uvicorn backend.app:app --host 0.0.0.0 --port ${X_ZOHO_CATALYST_LISTEN_PORT}'
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
docker build --platform linux/amd64 -t drishti:latest .
catalyst deploy appsail --name drishti \
  --source docker://drishti:latest \
  --port 9000
```

## Post-deployment checklist

- `/api/health` returns HTTP 200.
- `/` loads the dashboard without browser-console errors.
- Dashboard, map, search, profiles, networks, alerts, and district drill-down work.
- Cold-start and warm response times are recorded.
- The public demo uses synthetic data only.
- Production credentials and real police data are absent.

## Catalyst Data Store migration

Drishti now selects Catalyst Data Store automatically inside AppSail and falls
back to local CSV files only when the SDK or required tables are unavailable.
Set `DRISHTI_DATA_SOURCE=csv` to force local mode, or
`DRISHTI_DATA_SOURCE=catalyst` to require a Catalyst-first attempt.

1. Create the tables and columns described in `datastore-schema.json` in the
   Catalyst console. This manifest is the implementation-ready version of the
   supplied `Police_FIR_ER_Diagram (1).pdf`, including corrected act/section
   keys and explicit Catalyst data types. Mark each `unique` column as unique
   and add the recommended search indexes.
2. Prepare a development subset:

   ```bash
   python scripts/prepare_catalyst_import.py --environment development --case-limit 2500
   ```

3. Import the staged tables:

   ```bash
   sh scripts/import_catalyst_datastore.sh development
   ```

4. For the complete dataset, enable the Catalyst production environment and run:

   ```bash
   python scripts/prepare_catalyst_import.py --environment production
   sh scripts/import_catalyst_datastore.sh production
   ```

Catalyst development permits 5,000 rows per table and 25,000 rows overall.
The complete Drishti relational dataset therefore cannot be imported into
development without truncation. Production is the system of record; development
is for workflow tables and a representative analytical subset.
