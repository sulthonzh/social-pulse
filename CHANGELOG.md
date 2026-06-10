# Changelog

## 0.1.0 (2026-06-10)


### Features

* add admin CLI tooling with Typer (§14.29) ([fc8656a](https://github.com/sulthonzh/social-pulse/commit/fc8656ac2057d791a18a53f434fbb27a2fcb1cc9))
* add data lineage tracking with migration v5 (§14.30) ([58c19eb](https://github.com/sulthonzh/social-pulse/commit/58c19eb2679145166cf29cb7695f8fc98d1b5590))
* add load testing, K8s, SBOM, release and deployment pipeline ([1961cfc](https://github.com/sulthonzh/social-pulse/commit/1961cfc138107b09cdef18e6a1128379b0f6e7a3))
* add pre-commit hooks, dependabot, MIT license ([d52874f](https://github.com/sulthonzh/social-pulse/commit/d52874fe5817623002942bff07ea06f289e1e5d8))
* **api:** add /metrics endpoint and input validation ([2505bd2](https://github.com/sulthonzh/social-pulse/commit/2505bd2aef5a1fb85d1ec1607c0b98569d6fb94a))
* **api:** add versioning, CORS, security headers, compression ([c776ed0](https://github.com/sulthonzh/social-pulse/commit/c776ed01a9fa9dcf38f1318da9ce5f2302d72ae6))
* **api:** enable WAL mode, restrict CORS, harden validation ([fca5dd6](https://github.com/sulthonzh/social-pulse/commit/fca5dd6b7d0f9649e59fff02f995f4dedf3ed839))
* **api:** implement cursor pagination for enriched posts ([f541c22](https://github.com/sulthonzh/social-pulse/commit/f541c22ec14dc178e468d3930e24222511e5cd71))
* **app:** add ListSearchRequests, remove direct SQL from screen ([428d513](https://github.com/sulthonzh/social-pulse/commit/428d513218d06dded462c5163799ae7f1cffbeff))
* **application:** add RawPost boundary validation (§14.4) ([32bc8e8](https://github.com/sulthonzh/social-pulse/commit/32bc8e845395f436fe3ba25633de9c949990a664))
* **backup:** implement rotation policy and backup automation ([7cd54d1](https://github.com/sulthonzh/social-pulse/commit/7cd54d12ce08c73f4fcd59a34f6aa6476d7350bf))
* **data-governance:** add configurable data retention with TTL purge ([a638187](https://github.com/sulthonzh/social-pulse/commit/a6381879204cedc3f99144f6e25f7eb0715e8998))
* **docker:** split into base/ml-base stages, optional ML deps ([117c59c](https://github.com/sulthonzh/social-pulse/commit/117c59c640ad516b945778743484e01719646b37))
* **gold:** implement incremental builds with tracking table ([0259195](https://github.com/sulthonzh/social-pulse/commit/0259195fef237348b14981b5a25c1f3c8f60e18a))
* **infra:** support migration rollback and test factories ([40ecb79](https://github.com/sulthonzh/social-pulse/commit/40ecb79ec8047b92161fd292400a70fd8557d765))
* **observability:** add Prometheus /metrics endpoint ([35ed766](https://github.com/sulthonzh/social-pulse/commit/35ed766174acd4185c7670d26e6bc8b9b6b1c4e3))
* resolve §13.4-13.20 gaps — auth, rate limiting, circuit breaker ([9de37ea](https://github.com/sulthonzh/social-pulse/commit/9de37ea3783cff9d2fe18c4b64e3eb2262a8d344))
* **shared:** add connect_with_retry, refactor worker connections ([81deae1](https://github.com/sulthonzh/social-pulse/commit/81deae1ddf53de20c96be07d36c4ec0c2560c19e))
* **shared:** add HTTP retry with exponential backoff (§14.3) ([3533d57](https://github.com/sulthonzh/social-pulse/commit/3533d57d30c419214adc88ee8b8c6c96c0b0a2df))
* **shared:** add prompt versioning registry ([1bbe14c](https://github.com/sulthonzh/social-pulse/commit/1bbe14c0b08a43237e566607b1ca2085a6503182))
* **shared:** add structured logging config with structlog ([1dc4cab](https://github.com/sulthonzh/social-pulse/commit/1dc4cabc54f41bdb9f64de78173e09122390c82c))
* **shared:** add token budgeting and worker health server ([a00561c](https://github.com/sulthonzh/social-pulse/commit/a00561c809eb1f4e62d8ce47f7e545927b03afe3))
* **shared:** introduce DuckDB maintenance utilities ([ec9d00a](https://github.com/sulthonzh/social-pulse/commit/ec9d00af907ad5f1f9fbc84b68f84807cc5b9f71))
* **worker:** add job re-enqueue CLI for failed AI jobs ([9d459d6](https://github.com/sulthonzh/social-pulse/commit/9d459d62ac0f9d14e4f146cae7b51c420d72240c))
* **worker:** integrate health probes and token budgeting ([1a53a20](https://github.com/sulthonzh/social-pulse/commit/1a53a203a712d4b5a3dd54ccc108f54af71f5329))


### Bug Fixes

* add ignore_missing_imports to mypy overrides for ML libraries ([2cd8000](https://github.com/sulthonzh/social-pulse/commit/2cd8000f4081a48b43faf7074484dd853b74ae58))
* **ci:** mock duckdb, non-blocking security scan, bump starlette ([17f4335](https://github.com/sulthonzh/social-pulse/commit/17f43356cf78f33d31e4036d9d08cbe16f4debc4))
* harden transaction safety, resource cleanup, and security ([a1a7725](https://github.com/sulthonzh/social-pulse/commit/a1a77251cb2e6ee0afb5427a32292498f75ad7cc))
* mount tests/ volume in docker-compose lint service ([1cc6257](https://github.com/sulthonzh/social-pulse/commit/1cc62573e6d62467cf05ddf26d7ee6d259faac72))
* narrow exception catches to domain-specific error types ([c14b9e7](https://github.com/sulthonzh/social-pulse/commit/c14b9e75a606674dafe30af739cf28edb06a7c7f))
* read stored hashtags/topics from campaign summary row with fallback ([fcd56a0](https://github.com/sulthonzh/social-pulse/commit/fcd56a0768fb19ab3a75209f7e2239944fdbac1f))
* resolve PLC0415 ruff errors, bump pre-commit ruff ([d4797ef](https://github.com/sulthonzh/social-pulse/commit/d4797ef58ea176ad4638806d52475c1541d444c1))
* resolve ruff lint and mypy type errors ([3aa43fb](https://github.com/sulthonzh/social-pulse/commit/3aa43fb092763baaa568419cee69df459c9d6a74))
* use read_only=True connections in all presentation screens ([3de6e51](https://github.com/sulthonzh/social-pulse/commit/3de6e517996e0f66d37f5121ce4f7522eb73b714))
