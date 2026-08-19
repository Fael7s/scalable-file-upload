# Scalable File Upload

A file service that keeps binary payloads out of the application tier: uploaded bytes go to Amazon S3, the API stores only metadata and an audit trail, and downloads are handed off to S3 through short-lived presigned URLs.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-green.svg)](https://fastapi.tiangolo.com/)

## Context

Most file-upload tutorials write bytes to the application server's local disk. That works until the service runs on more than one instance, at which point the file exists on exactly one machine and every other replica returns 404. This project exists to demonstrate the alternative: the API tier stays stateless, object storage owns the bytes, and a relational store owns the metadata that makes those objects addressable.

The engineering decision on display is the separation between the control plane (an authenticated, audited HTTP API that validates, records, and authorizes) and the data plane (S3, which receives the bytes on upload and serves them directly to the client on download). The API never streams a stored object back to the caller; it issues a time-bounded presigned URL and steps out of the transfer path. Every state-changing operation and every link issuance is written to an append-only access log in the same database transaction as the operation itself.

## Tech stack

| Technology | Version | Why it was chosen |
|---|---|---|
| Python | 3.12 (`python:3.12-slim` base image) | Runtime for the Docker image defined in `Dockerfile` |
| FastAPI | 0.115.6 | Async request handling plus dependency injection, which is what carries auth, DB sessions, and the S3 client into every route |
| Uvicorn | 0.34.0 | ASGI server; single process in the container CMD |
| boto3 | 1.35.86 | AWS SDK used for `put_object`, `generate_presigned_url`, and `delete_object` |
| SQLAlchemy | 2.0.36 | Typed declarative models (`Mapped`/`mapped_column`) and the async session API |
| aiosqlite | 0.20.0 | Async SQLite driver, so metadata queries do not block the event loop |
| Pydantic | 2.10.4 | Request/response validation built into FastAPI |
| pydantic-settings | 2.7.1 | Environment configuration with typed fields; missing AWS credentials fail at startup, not at first upload |
| python-multipart | 0.0.20 | Required by FastAPI to parse `multipart/form-data` uploads |
| httpx | 0.28.1 | Async test client driving the app through `ASGITransport` |
| pytest / pytest-asyncio | 8.3.4 / 0.25.0 | Test runner and async test support |
| Docker Compose | file format 3.9 | Single-service local environment with `.env` injection |

## Architecture

```
                  X-API-Key
                     |
   Client  ---- POST /files/upload ------> FastAPI (Uvicorn)
                                             |
                                             |  1. extension allow-list check
                                             |  2. read body, enforce size limit
                                             |  3. put_object under uploads/<uuid>.<ext>
                                             +----------------------------> Amazon S3
                                             |
                                             |  4. INSERT files (metadata)
                                             |  5. INSERT access_logs (UPLOAD)
                                             +----------------------------> SQLite
                                                                            (one transaction,
                                                                             committed by the
                                                                             session dependency)

   Client  ---- GET /files/{id}/download --> FastAPI
                                             |  look up s3_key, log DOWNLOAD_LINK
                                             |  generate_presigned_url(ttl)
                                             v
                                          presigned URL (60s .. 12h)
                                             |
   Client  ------------------------------ GET presigned URL ------------> Amazon S3
                                          (bytes never traverse the API)
```

Request path through the code: `app/main.py` mounts three routers; each handler resolves three dependencies before running: `verify_api_key` (`app/middleware/access_logger.py`), `get_db` (`app/database.py`), and `get_s3_service` (`app/services/s3_service.py`). Tables are created at startup by `init_db()` in the FastAPI lifespan handler.

## Endpoints

Seven routes, all except `/health` behind the API key dependency.

| Method | Route | Behaviour |
|---|---|---|
| POST | `/files/upload` | Validates extension and size, writes to S3, inserts metadata, logs `UPLOAD`. Returns 201 |
| GET | `/files/` | Lists metadata ordered by `uploaded_at` descending. `skip` >= 0, `limit` 1..100 (default 20) |
| GET | `/files/{file_id}/download` | Issues a presigned GET URL, logs `DOWNLOAD_LINK`. `expiration` 60..43200 seconds |
| DELETE | `/files/{file_id}` | Deletes the S3 object, deletes the metadata row, logs `DELETE` |
| GET | `/logs/` | Access log, newest first. Optional `action` filter, `limit` 1..200 (default 50) |
| GET | `/logs/file/{file_id}` | Full access history for one file, including user agent |
| GET | `/health` | Liveness response; the only unauthenticated route |

## Engineering properties

**Validation happens before the expensive step.** The extension allow-list is checked against the filename before the request body is read (`S3Service.upload`), so a rejected file type costs no memory and no S3 call. The size limit is enforced after the body is in memory but before `put_object`, so an oversized file costs RAM but never storage or bandwidth to AWS.

**Object keys are server-generated, never client-derived.** Each upload gets `uploads/<uuid4-hex>.<ext>`, where only the extension survives from the client-supplied name. Two clients uploading `report.pdf` cannot collide, and a filename containing `../` cannot influence the key. The original filename is retained only as a metadata column.

**One transaction per request, covering both the operation and its audit record.** The `get_db` dependency yields a session, commits on clean exit, and rolls back on any exception. Handlers call `flush()` rather than `commit()`, so a file row and its `UPLOAD` log entry become visible together or not at all. There is no code path that records an operation without its log entry, or the reverse.

**Explicit failure mapping instead of leaked stack traces.** Every `botocore` `ClientError` is caught in the S3 service and re-raised as an `HTTPException` with status 502, carrying only the AWS-supplied message. Unknown file IDs return 404 from the route layer. A missing or wrong API key returns 403 before any handler body executes.

**Bounded inputs on every list and link operation.** Pagination limits are declared as `Query(ge=..., le=...)` constraints, so Pydantic rejects out-of-range values with a 422 before a query is built. Presigned URL lifetime is clamped to 60 seconds minimum and 12 hours maximum regardless of what the caller asks for.

**Authentication is a dependency, not middleware.** `verify_api_key` is declared per route, which makes the authenticated surface visible in each route signature and keeps `/health` reachable without a key.

**Client IP resolution respects proxy headers.** `get_client_ip` reads the first entry of `X-Forwarded-For` when present and falls back to the socket peer, so audit rows stay meaningful behind a load balancer.

## Getting started

### Prerequisites

- Python 3.12 (or Docker), an AWS account, and an S3 bucket
- IAM credentials permitted to call `PutObject`, `GetObject`, and `DeleteObject` on that bucket

### Configuration

```bash
cp .env.example .env
```

All values below are placeholders. Fill them with your own; `.env` is git-ignored.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `AWS_ACCESS_KEY_ID` | yes | none | Startup fails if unset |
| `AWS_SECRET_ACCESS_KEY` | yes | none | Startup fails if unset |
| `AWS_REGION` | no | `us-east-1` | Region passed to the boto3 client |
| `S3_BUCKET_NAME` | yes | none | Target bucket; startup fails if unset |
| `API_KEY` | no | `change-me` | Expected value of the `X-API-Key` header |
| `MAX_FILE_SIZE_MB` | no | `50` | Upload ceiling, converted to bytes at check time |
| `ALLOWED_EXTENSIONS` | no | `jpg,jpeg,png,gif,pdf,doc,docx,txt,csv,zip` | Comma-separated allow-list, matched case-insensitively |
| `PRESIGNED_URL_EXPIRATION` | no | `3600` | Default link lifetime in seconds |
| `DATABASE_URL` | no | `sqlite+aiosqlite:///./file_upload.db` | SQLAlchemy async URL |
| `APP_NAME` / `APP_ENV` | no | `ScalableFileUpload` / `development` | Metadata surfaced in the OpenAPI title and `/health` |

### Run with Docker

```bash
docker-compose up --build
```

The service listens on port 8000. The compose file bind-mounts the project directory into the container, so the SQLite file is written to the host working directory.

### Run locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive OpenAPI documentation: `http://localhost:8000/docs`.

### Provision the bucket

`scripts/setup_aws.sh <bucket-name> <region>` creates the bucket, applies a full public access block, and enables versioning. It requires the AWS CLI to be installed and configured.

### Example requests

```bash
curl -X POST http://localhost:8000/files/upload \
  -H "X-API-Key: <your-api-key>" \
  -F "file=@document.pdf"

curl "http://localhost:8000/files/<file-id>/download?expiration=900" \
  -H "X-API-Key: <your-api-key>"

curl http://localhost:8000/logs/?action=UPLOAD \
  -H "X-API-Key: <your-api-key>"
```

## Testing

```bash
pytest tests/ -v -o asyncio_mode=auto
```

The suite contains three tests driven through `httpx.ASGITransport`, so no network listener is started:

- `test_upload_without_api_key` asserts that an upload without the `X-API-Key` header is rejected with 403 before reaching the handler
- `test_health_check` asserts the unauthenticated liveness route
- `test_download_not_found` asserts 404 for an unknown file ID

Known state of the suite, as run against this commit: two tests pass and `test_download_not_found` fails with `sqlite3.OperationalError: no such table: files`. The client fixture builds `ASGITransport` directly, which does not execute the application lifespan, so `init_db()` never runs and no schema exists for the query to hit. Fixing it requires a fixture that creates the schema (or uses `LifespanManager`) rather than a change to application code. The `-o asyncio_mode=auto` flag is needed because the async fixture is declared with `@pytest.fixture` and the repository ships no pytest configuration file to set that mode.

What the suite does not cover: the upload happy path, S3 interaction of any kind (no `moto` or stubbed client), deletion, the list and logs endpoints, extension and size rejection paths, presigned URL generation, and expiration bound validation. There is no coverage measurement and no CI workflow in the repository.

## Technical decisions and trade-offs

### 1. Presigned URLs instead of proxying downloads through the API

The problem: something has to serve the bytes on download. Doing it from the API means every download occupies a worker and consumes the application tier's bandwidth for the whole transfer.

Alternatives I considered: streaming the object through FastAPI with a `StreamingResponse`, making the bucket publicly readable, or issuing presigned URLs.

I chose presigned GET URLs with a lifetime bounded between 60 seconds and 12 hours, and kept the bucket private (the provisioning script applies a full public access block).

What I gave up: once a link is issued, it is a bearer capability that cannot be revoked before it expires, and it is not tied to the requester's identity or IP. The API also loses visibility into the transfer itself. The access log can record that a link was issued (`DOWNLOAD_LINK`), never that a download completed, so download counts in this system are link-issuance counts and I documented them as such.

### 2. Buffering the upload in memory instead of streaming to S3

The problem: the size limit must be enforced before the object is stored, and the byte count must be persisted as metadata.

Alternatives I considered: an S3 multipart upload streaming chunk by chunk with an abort once the limit is exceeded, delegating the limit to a reverse proxy's body size cap, or reading the whole body and checking the length.

I chose the last one: `await file.read()`, compare against `MAX_FILE_SIZE_MB`, then a single `put_object`.

What I gave up: peak memory scales with concurrent uploads multiplied by file size, so the 50 MB default is really a statement about memory headroom, not about storage. The check also happens after the bytes have already crossed the network into the process, so it protects S3 cost and not ingress cost. Streaming multipart would have removed both problems at the cost of handling part sequencing, abort-on-overflow, and cleanup of orphaned parts, which was more machinery than this scope justified.

### 3. Opaque server-generated object keys instead of preserving the filename

The problem: client-supplied filenames are neither unique nor safe. Two users upload `invoice.pdf`; a hostile user uploads a name designed to escape the intended prefix.

Alternatives I considered: sanitizing and timestamp-prefixing the original name, scoping keys under a per-user prefix, or discarding the name from the key entirely.

I chose to discard it: the key is `uploads/<uuid4-hex>.<ext>` and the original filename lives only in the `files` table.

What I gave up: the bucket is no longer browsable by a human, and the metadata database becomes load-bearing. If the SQLite file is lost, every object in the bucket is still there and completely unidentifiable. That is an acceptable trade for a system where the database is the index of record, but it means the database needs the same backup discipline as the bucket.

### 4. Transaction boundary in the session dependency instead of per-handler commits

The problem: an audit trail that can disagree with the data it describes is worse than no audit trail.

Alternatives I considered: committing after each write inside handlers, emitting audit records to a separate store or queue, or logging from middleware around the request.

I chose a unit-of-work in the `get_db` dependency: it yields the session, commits once when the handler returns, and rolls back on any exception. Handlers and `LogService` only `flush()`.

What I gave up: this makes the database self-consistent but does nothing about S3, which is not part of the transaction. If `put_object` succeeds and the commit then fails, the object exists with no metadata row and no audit entry. On delete, the ordering is reversed and equally exposed: the S3 object is removed first, so a later failure leaves a metadata row pointing at a key that no longer exists. Closing that gap needs an outbox or a reconciliation sweep comparing bucket contents against the metadata table, neither of which is implemented here.

### 5. SQLite with aiosqlite instead of PostgreSQL

The problem: the service needs a durable, queryable metadata and audit store, without making a reviewer provision infrastructure to run the project.

Alternatives I considered: PostgreSQL as a second compose service, DynamoDB, or storing metadata as S3 object tags and avoiding a database entirely.

I chose SQLite through the async `aiosqlite` driver, with `DATABASE_URL` kept configurable so the engine can be swapped without touching model or query code.

What I gave up: SQLite serializes writers, so the write path does not scale horizontally even though the API tier does. The object-tags alternative would have removed the database entirely, but tags are limited in number and size and cannot answer "newest 20 uploads" without listing the whole bucket, which is why I kept a relational store. Schema is created with `Base.metadata.create_all` at startup, which means there are no migrations: any future column change has to be applied by hand.

### 6. Shared API key instead of per-user authentication

The problem: the endpoints needed an access gate, and the project has no user model.

Alternatives I considered: JWT with a user table, AWS SigV4 request signing, or delegating to an OIDC provider.

I chose a single shared secret sent as `X-API-Key`, verified by a FastAPI dependency that returns 403 when the header is missing or wrong.

What I gave up: there is no principal in the system, so the access log records IP address and user agent but cannot record who acted. There is no rotation path and no scope separation between reading logs and deleting files. The comparison is an ordinary string equality rather than a constant-time compare. For a single-tenant demonstration service that is a deliberate simplification; for anything multi-tenant it is the first thing that would have to change.

## Known limitations and what I would do differently at larger scale

- **boto3 calls block the event loop.** `put_object`, `generate_presigned_url`, and `delete_object` are synchronous calls made from `async def` handlers. For the duration of each S3 round trip, that worker serves no other request. The fix is either `asyncio.to_thread` / `run_in_threadpool` or an async client such as aioboto3.
- **A new boto3 client is constructed per request.** `get_s3_service` returns a fresh `S3Service` on every dependency resolution, so no connection pool or signing session is reused across requests. A module-level client or a cached dependency would remove that setup cost.
- **Retry behaviour is entirely botocore's default.** No explicit `botocore.config.Config(retries=...)` is set, so timeouts and retry counts are whatever the SDK defaults to, and there is no backoff policy chosen for this workload.
- **No idempotency on upload.** A retried POST creates a second object and a second metadata row. An `Idempotency-Key` header checked against a unique index would make retries safe.
- **Deletion is not atomic across the two stores** (see decision 4), and there is no reconciliation job to detect orphaned objects or dangling rows.
- **Offset-based pagination** degrades on large tables and can skip or repeat rows when data changes between pages. Keyset pagination on `(uploaded_at, id)` would be the replacement.
- **Content type is trusted from the client.** Validation is extension-based only; the `Content-Type` stored and sent to S3 is whatever the client declared. There is no magic-byte inspection and no malware scanning.
- **No rate limiting and no request size cap at the edge.** A caller can force repeated full-body reads up to the configured limit before rejection happens.
- **No migrations.** `create_all` builds missing tables and ignores drift; Alembic would be the first addition if the schema were to evolve.
- **No CI pipeline.** The repository has no workflow configuration, so nothing runs the tests on push.
- **The test suite does not currently pass in full** (see Testing) and does not exercise S3 at all.
- **`scripts/setup_aws.sh` always sends `--create-bucket-configuration LocationConstraint`**, including for the default `us-east-1`, where the AWS API rejects that parameter. The region argument needs a conditional branch.
- **Single Uvicorn process in the container.** No worker count is configured and there is no reverse proxy in the compose file, so TLS termination, request buffering, and body limits are unaddressed in the shipped environment.

## License

MIT. See `LICENSE`.
