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

## Agent model configuration

Configure model credentials in the Catalyst console for the **Drishti** AppSail
service. Do not add secrets to `app-config.json`, `.env` files, shell history, or
Git.

| Variable | Recommended value | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Secret entered in Catalyst | Enables the model-backed tool loop |
| `DRISHTI_AI_MODEL` | `gpt-5-mini` | Selects the deployed agent model |
| `DRISHTI_AI_MODE` | `required` | Fails closed instead of silently using the deterministic fallback |

Add `OPENAI_API_KEY` from the console **after the final CLI deployment**. The
CLI deploy reads `env_variables` from `app-config.json`; a later CLI deployment
can replace the service configuration and remove console-only variables. Never
copy the secret into `app-config.json` to work around this behavior. After
saving the variable, restart AppSail from the console (without another CLI
deployment) and verify that
`/api/health` reports `ai.configured: true`, `ai.provider: "openai"`, and
`ai.mode: "required"`. Then run one synthetic FIR investigation and confirm its
response contains a model response ID and non-zero token usage.

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

   The Agentic Case Room additionally requires the append-only
   `DrishtiAgentRun` table. Its application columns are `RunID` (unique Var
   Char), `CaseID` (BigInt), `Role` (Var Char), `QueryHash` (Var Char),
   `PlanFingerprint` (Var Char), `PreviousAuditHash` (Var Char), `AuditHash`
   (Var Char), `Tools` (Text), `CitationCount` (BigInt), `AIProvider` (Var
   Char), `AIModel` (Var Char), `ModelResponseID` (Var Char), `TokenUsage`
   (Text), `Status` (Var Char), and `CreatedAt` (DateTime). Index `CaseID`,
   `Status`, and `CreatedAt`. Catalyst creates its system columns automatically.

   Investigation tasks and evidence-custody changes reuse the append-only
   `DrishtiOperationalAction` table. `ActionType` values beginning with
   `task-` and `evidence-` are immutable events; the API reconstructs current
   state instead of updating prior rows. Add indexes for `CaseID`,
   `ActionType`, `Status`, and `CreatedAt`.

   The development UI contains a role selector so reviewers can exercise every
   workspace. This is not authentication. Before production, place AppSail
   behind Catalyst Authentication/User Management and derive role, unit,
   district, and permitted cases from the verified server-side identity. Do
   not accept the browser's role selector or request-body role as authority.
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

## Persisted synthetic use cases

Generate the fixed eight-scenario, 230-row relational package with:

```bash
python scripts/generate_catalyst_use_cases.py
```

The AppSail build bundles this package. Its development-only internal seed
endpoint accepts no caller-provided rows, enforces reserved IDs and a 500-row
cap, and is idempotent. The manifest SHA-256 prefix must be supplied through
the `X-Drishti-Synthetic-Seed` header. It inserts only missing fixed rows and
never updates an existing FIR.
