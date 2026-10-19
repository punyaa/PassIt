# PassIt

**Rent more, own less.** PassIt is a Singapore peer-to-peer rental marketplace prototype built by six parallel workstreams.

This is the master project document. Folder-specific details live only in the short README inside each primary implementation folder.

## Start locally

The supported local environment is Docker Compose:

```bash
docker compose up --build
```

- Web application: <http://localhost:3000>
- API documentation: <http://localhost:8000/docs>
- API health: <http://localhost:8000/health>
- PostgreSQL: `localhost:5432`

Compose waits for PostgreSQL, applies pending Alembic migrations, and then starts the API and web application.

For native development:

```bash
uv sync --project api --dev
npm ci --prefix web
uv run --directory api alembic upgrade head
npm run api:dev
npm run web:dev
```

Create your private local configuration before starting:

```bash
cp .env.example .env
```

The template explains which values are required, which are optional, and where each value comes from. Replace only the settings needed by your workstream.

## Environment variables and secrets

| Value | Local development | Shared staging/demo |
| --- | --- | --- |
| App URLs and feature settings | Root `.env` | GitHub Environment variables or ECS task configuration |
| JWT secret, provider tokens and MongoDB URI | Root `.env` | AWS Secrets Manager or SSM Parameter Store |
| AWS Bedrock and S3 access | AWS SSO profile in `~/.aws` | ECS task IAM role |
| Deployment role identifier | Not normally needed | GitHub Environment secret such as `AWS_ROLE_ARN` |

Rules:

- Commit `.env.example`, but never commit `.env` or any environment-specific variant.
- Never put a secret in a variable beginning with `NEXT_PUBLIC_`; Next.js exposes those values to the browser.
- Bedrock and S3 use AWS IAM. They do not require separate API keys.
- Prefer short-lived AWS SSO credentials locally and an ECS task role in AWS. Do not create long-lived AWS access keys for teammates.
- PostgreSQL is the primary database. MongoDB variables are optional and should only be populated if an approved workstream deliberately uses Atlas.
- Store shared secrets in the deployment secret store, not in GitHub source files, issues, chat messages or screenshots.
- Rotate a token immediately if it is accidentally committed or shared.

## Repository structure

```text
api/          FastAPI, domain modules, Alembic, OpenAPI and backend tests
web/          Next.js, TypeScript, Tailwind, generated API types and MSW mocks
infra/        Docker/AWS infrastructure boundaries and Terraform environments
scripts/      Seed, load, contention and demo-operation tools
.github/      CI, dependency updates, issue forms and ownership rules
compose.yaml  Local PostgreSQL, API and web environment
```

The supported product lives only in these paths. There is no separate legacy application.

## Architecture

```text
Next.js web  →  FastAPI  →  PostgreSQL 16
                    ├── S3 / CloudFront media
                    ├── OneMap / approved model service
                    └── EventBridge / settlement worker
```

- FastAPI owns the committed OpenAPI contract in `api/openapi.json`.
- The frontend generates types in `web/lib/api-types.ts` and uses MSW mocks while endpoints are unfinished.
- Alembic owns database schema changes.
- A PostgreSQL exclusion constraint prevents overlapping active bookings.
- Monetary values use exact decimal types and every ledger event must balance to zero.
- Payments and deposits are simulated ledger entries; the prototype does not move real money.
- Public listings use approximate neighbourhood information, never exact addresses.
- Terraform currently defines reviewed boundaries, not deployed AWS resources.

## Six workstreams

| Stream | Responsibility | Owned paths |
| --- | --- | --- |
| P1 Platform | Cloud, Terraform, Docker, CI/CD, monitoring and authentication | `infra/`, `.github/`, `compose.yaml`, `api/app/auth/`, `api/app/core/` |
| B1 Booking | Availability, conflict-safe booking, lifecycle, checklists and reviews | `api/app/bookings/`, `api/app/reviews/`, contention tests |
| B2 Transactions | Balanced ledger, holds, releases, deposits and aggregation | `api/app/transactions/` |
| B3 Catalogue | Listings, media, search, location, pricing and seed data | `api/app/catalogue/`, `api/app/media/` |
| F1 Front core | Design system, shell, auth, catalogue, search and booking views | shared `web/components/` and core routes |
| F2 Front transaction | Handover, return, damage, dashboards and reviews | transaction routes under `web/app/` |

Replace the bootstrap account in `.github/CODEOWNERS` when the six GitHub usernames are confirmed.

## Contract workflow

After changing API routes or schemas:

```bash
uv run --directory api python -m scripts.export_openapi
npm run generate:api --prefix web
```

Commit `api/openapi.json` and `web/lib/api-types.ts` with the implementation. Frontend mocks must follow the same contract.

## Development workflow

1. Claim an issue with a clear owner and acceptance criteria.
2. Branch from `main` using `feat/`, `fix/`, `test/`, `docs/` or `chore/`.
3. Keep changes inside the owning workstream where possible.
4. Add tests for behaviour changes and update the API contract when applicable.
5. Open a focused pull request and request one cross-stream reviewer.
6. Merge only after CI passes and review conversations are resolved.

Use short imperative commit subjects such as `feat: add booking conflict response`.

## Verification

```bash
npm run api:lint
npm run api:test
npm run web:check
npm run web:build
docker compose config --quiet
```

CI repeats these checks and rejects stale generated contracts.

## Delivery plan

- **Foundation:** authentication, listing creation, media upload and stable staging.
- **Correctness:** transactional booking, contention tests, balanced ledger and idempotent settlement.
- **Journey:** search, booking, handover, return, damage, dashboards and reviews.
- **Evaluation:** load testing, fault recovery, cost evidence and moderated usability testing.

If scope must be reduced, cut delivery, subscriptions, monthly pricing and reviews before conflict-safe booking, the ledger, condition evidence or return settlement.

## Repository administration

Before sharing the repository:

- use the final `PassIt` repository name and description;
- invite the six contributors and update `.github/CODEOWNERS`;
- protect `main` with pull requests, one approval, required CI and resolved conversations;
- enable secret scanning, push protection and private vulnerability reporting;
- store deployment secrets only in GitHub Environments;
- use squash merging and delete merged branches automatically.

## Security and conduct

Do not commit secrets, identity documents, exact addresses, real payment data or participant data. Report vulnerabilities privately to the repository owner or course team rather than through a public issue. Do not test against systems or data you do not own.

Contributors must communicate respectfully, review ideas rather than people, acknowledge others' work and maintain academic integrity. Harassment, discrimination, plagiarism and disclosure of private information are not acceptable.

This is a prototype, not a production marketplace. It does not provide identity verification, insurance, real payment processing or a completed legal/privacy review.

## Licence

MIT. See `LICENSE`.
