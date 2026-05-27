# Geo Expert RAG Embedding Upgrade

## Current Default

Geo Expert currently defaults to the `hash` backend for local Chroma ingest.

Why this is the default:

- stable
- offline
- deterministic
- does not block on model download

This is suitable for development and workflow validation, but not ideal for production semantic retrieval quality.

## Available Backends

### `hash`

- deterministic
- offline-safe
- best default for smoke tests and local verification

### `sentence_transformers`

- better semantic retrieval quality
- requires local package and local model availability
- only enabled when explicitly selected

### `chroma_default`

- may initialize external/default embedding behavior
- may be slower or less predictable in offline setups
- not recommended as the default for this repo

## Usage

```powershell
py -3.11 scripts\ingest_geo_expert_local_chroma.py --embedding-backend hash
py -3.11 scripts\ingest_geo_expert_local_chroma.py --embedding-backend sentence_transformers --embedding-model <local-model-name-or-path>
py -3.11 scripts\ingest_geo_expert_local_chroma.py --embedding-backend chroma_default
```

## Local Sentence Transformers

If you want to try `sentence_transformers`, make sure:

- the package is installed
- the model is already available locally

You can also set:

```powershell
$env:GEO_EXPERT_RAG_EMBEDDING_MODEL="<local-model-name-or-path>"
```

## Avoiding Hangs

- keep `hash` as the default
- do not rely on automatic model download
- do not switch to `chroma_default` unless you understand the environment behavior
- use `--dry-run` before writing to Chroma

## Roll Back to Hash

If the optional semantic backend is unavailable or slow, switch back immediately:

```powershell
py -3.11 scripts\ingest_geo_expert_local_chroma.py --embedding-backend hash
```

Only use `--reset` when you explicitly want to recreate the target collection.
