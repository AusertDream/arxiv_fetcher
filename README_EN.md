# arXiv Fetcher

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)

English | [简体中文](README.md)

arXiv AI/LLM Paper Intelligent Retrieval System - Automatically fetch, store, and search the latest academic papers in the field of artificial intelligence.

## Table of Contents

- [Features](#features)
- [Data Download](#data-download)
- [Quick Start](#quick-start)
- [Service Management](#service-management)
- [API Usage Examples](#api-usage-examples)
- [Builder CLI Tool](#builder-cli-tool)
- [Configuration](#configuration)
- [FAQ](#faq)
- [System Architecture](#system-architecture)
- [Directory Structure](#directory-structure)
- [Tech Stack](#tech-stack)
- [Contributing](#contributing)
- [License](#license)
- [Changelog](#changelog)

## Features

- **CSV Persistence Layer** - Separation of fetching and embedding, supports resume and data backup
- **Comprehensive AI Paper Retrieval** - Covers 10 AI-related categories without keyword filtering
- **Staged Execution** - build/update mode supports fetch and embed independent execution
- **Incremental Paper Fetching** - Automatic deduplication, only fetches new papers to CSV
- **Vector Database Storage** - Uses ChromaDB and bge-m3 embedding model (1024-dimensional)
- **Intelligent Semantic Search** - Dual similarity scoring (title + abstract) for improved search accuracy
- **RESTful API** - Complete Swagger/OpenAPI interactive documentation
- **Flexible Data Management** - Shell scripts and CLI tools support multiple operation modes

## Data Download

This project provides preprocessed data of 214,100 AI papers, ready for direct download and use without re-crawling.

### Dataset Information
- **Paper Count**: 214,100
- **Time Range**: January 2024 - January 2026
- **Coverage Areas**: cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, cs.RO, cs.MA, cs.IR, cs.HC, stat.ML (10 AI-related categories)
- **File Size**: 309 MB (CSV format)
- **Fields**: ID, Title, Abstract, Authors, Published Date, URL

### Download Links
- **ModelScope**: [arxiv-papers](https://www.modelscope.cn/datasets/ausertdream/arxiv_ai_paper_data)


### Using Downloaded Data

After downloading the data, place the CSV file at `data/init_data.csv`, then execute:

```bash
# Build vector database from CSV
python scripts/run_builder.py build --mode embed
```

See [DATASET.md](DATASET.md) for detailed instructions.

## Quick Start

### 1. Install Dependencies

```bash
conda activate <your_env>  # Replace with your conda environment name
cd /path/to/arxiv_fetcher   # Replace with your project path
pip install -r requirements.txt
```

### 2. Configuration

Edit `config/default.yaml` to adjust settings as needed (default values usually work).

Key configuration items:
- `database.path` - ChromaDB storage path
- `storage.csv_path` - CSV file storage path
- `embedding.device` - GPU device (e.g., cuda:3)
- `arxiv.max_results` - Maximum fetch count
- `api.port` - API service port

### 3. Initial Database Build

**Option 1: One-step Completion** (Recommended)
```bash
# Complete workflow: fetch → CSV → embed → ChromaDB
python scripts/run_builder.py build --mode all --max-results 1000
# Or use Shell script
./shell/arxiv_service.sh build all
```

**Option 2: Step-by-step Execution** (For debugging or large-scale data)
```bash
# Step 1: Fetch all papers to CSV (may take hours)
python scripts/run_builder.py build --mode fetch --max-results -1

# Step 2: Embed from CSV to ChromaDB (GPU accelerated, faster)
python scripts/run_builder.py build --mode embed
```

### 4. Start API Service

```bash
./shell/arxiv_service.sh start
```

### 5. Access Swagger Documentation

Open your browser and visit: http://localhost:5001/docs

You can test all API endpoints directly in the Swagger UI.

## Service Management

Use the unified Shell script to manage services and data:

### API Service Management

```bash
# Start service
./shell/arxiv_service.sh start

# Stop service
./shell/arxiv_service.sh stop

# Restart service (default command)
./shell/arxiv_service.sh restart
./shell/arxiv_service.sh  # Equivalent to restart

# Check status
./shell/arxiv_service.sh status

# Health check
./shell/arxiv_service.sh health

# View logs in real-time
./shell/arxiv_service.sh logs
```

### Data Management

```bash
# Initial build (complete workflow)
./shell/arxiv_service.sh build all

# Initial build (step-by-step)
./shell/arxiv_service.sh build fetch 1000    # Fetch 1000 papers to CSV
./shell/arxiv_service.sh build embed         # Embed from CSV

# Incremental update (complete workflow)
./shell/arxiv_service.sh update all

# Incremental update (step-by-step)
./shell/arxiv_service.sh update fetch 100    # Fetch 100 new papers
./shell/arxiv_service.sh update embed        # Embed latest CSV

# List all daily CSV files
./shell/arxiv_service.sh list
```

## API Usage Examples

### Search Papers

```bash
curl -X POST http://localhost:5001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "large language models for code generation",
    "top_k": 5
  }'
```

Response example:
```json
{
  "results": [
    {
      "paper_id": "2601.00756v1",
      "title": "Paper Title",
      "authors": ["Author1", "Author2"],
      "published": "2026-01-02",
      "url": "http://arxiv.org/abs/2601.00756v1",
      "score": 1.6945,
      "title_similarity": 0.8683,
      "abstract_similarity": 0.8262
    }
  ],
  "query": "large language models for code generation",
  "top_k": 5,
  "total_results": 5
}
```

### Incremental Database Update

```bash
curl -X POST http://localhost:5001/api/v1/incremental_update \
  -H "Content-Type: application/json" \
  -d '{
    "max_results": 100,
    "batch_size": 50
  }'
```

### View Database Statistics

```bash
curl http://localhost:5001/api/v1/stats
```

### Health Check

```bash
curl http://localhost:5001/api/v1/health
```

## Builder CLI Tool

Command-line tool for database management:

### Build Command (Initial Build)

```bash
# Complete workflow (fetch + embed)
python scripts/run_builder.py build --mode all --max-results -1

# Fetch to CSV only
python scripts/run_builder.py build --mode fetch --max-results 1000

# Embed from CSV only
python scripts/run_builder.py build --mode embed
python scripts/run_builder.py build --mode embed --csv /data2/.../init_data.csv
```

### Update Command (Incremental Update)

```bash
# Complete workflow (recommended - automatically skips existing papers)
python scripts/run_builder.py update --max-results 100

# Fetch new papers to CSV only
python scripts/run_builder.py update --mode fetch --max-results 50

# Embed from CSV only
python scripts/run_builder.py update --mode embed
python scripts/run_builder.py update --mode embed --csv daily/20260109_143025.csv
```

### Other Commands

```bash
# List all daily CSV files
python scripts/run_builder.py list-csv

# View statistics
python scripts/run_builder.py stats

# Add papers from JSON file
python scripts/run_builder.py add --json papers.json

# Clear database (use with caution!)
python scripts/run_builder.py clear
```

## Configuration

Main configuration items (`config/default.yaml`):

| Configuration | Description | Default Value |
|--------------|-------------|---------------|
| `database.path` | ChromaDB storage path | `./data/chromadb_data` |
| `database.collection_name` | Collection name | `ArxivPapers` |
| `storage.csv_path` | CSV file root directory | `./data/papers` |
| `storage.init_filename` | Initial CSV filename | `init_data.csv` |
| `storage.daily_dir` | Incremental CSV directory | `daily` |
| `embedding.model_path` | Embedding model path | bge-m3 path |
| `embedding.device` | GPU device | `cuda:3` |
| `embedding.batch_size` | Batch size | `32` |
| `arxiv.time_filter.enabled` | Enable time filtering | `true` |
| `arxiv.time_filter.mode` | Filter mode | `years` |
| `arxiv.time_filter.value` | Filter value | `2` (last 2 years) |
| `arxiv.max_results` | Maximum fetch count | `-1` (use `-1` for unlimited) |
| `arxiv.batch_size` | Fetch batch size | `50` |
| `arxiv.fetch_interval` | Batch interval (seconds) | `3.0` (supports decimals, 0 to disable) |
| `arxiv.batch_threshold_days` | Batch search stop threshold (days) | `1.0` |
| `arxiv.retry_max_attempts` | HTTP 429 max retry attempts | `3` |
| `arxiv.retry_base_sleep` | Retry base sleep time (seconds) | `5.0` (exponential backoff) |
| `search.default_top_k` | Default result count | `10` |
| `search.title_weight` | Title weight | `1.0` |
| `search.abstract_weight` | Abstract weight | `1.0` |
| `api.host` | API host | `0.0.0.0` |
| `api.port` | API port | `5001` |

### Configuration Priority

The system supports two levels of configuration priority (from high to low):

1. **API Request Parameters / Command-line Arguments** (Highest priority)
2. **config/default.yaml Configuration File** (Default values)

**Example**:
```bash
# No parameters → use 9000 from config
python scripts/run_builder.py update
curl -X POST http://localhost:5001/api/v1/incremental_update -d '{}'

# Passing parameters → override config
python scripts/run_builder.py update --max-results 100
curl -X POST http://localhost:5001/api/v1/incremental_update -d '{"max_results": 100}'
```

**Note**: `None` values mean using config defaults, `0` is a valid value and won't be overridden.

### Batch Size Explanation

The system has two different batch_size settings for different stages:

| Configuration | Stage | Default | Description |
|--------------|-------|---------|-------------|
| `arxiv.batch_size` | Fetch stage | 50 | Save after every 50 papers (resume granularity) |
| `embedding.batch_size` | Embedding stage | 32 | GPU processes 32 documents at once (optimize GPU memory) |

**Data Flow**:
```
Fetch 50 papers → Convert to 100 documents (title + abstract)
  → Split into 4 batches sent to GPU (32+32+32+4) → Store in ChromaDB
```

**Why Not Aligned**:
- `arxiv.batch_size=50` - Optimize network request frequency and storage frequency
- `embedding.batch_size=32` - Optimize GPU memory usage and computation efficiency

### Batch Search Mechanism

The system uses a time-iterative batch search mechanism to avoid timeouts or memory issues from requesting too many papers at once.

**How It Works**:

1. **Time Range Query**: Each batch search uses arXiv API's `submittedDate` range filter
   - Initial range: From start_date (e.g., 2 years ago) to current time
   - Maximum of `batch_size` papers per batch (default 50)

2. **Time Iteration**: Records earliest paper time in each batch, next batch searches from that time backwards
   ```
   Batch 1: [2024-01-07 TO 2026-01-06] → Get 50 papers, earliest: 2026-01-05
   Batch 2: [2024-01-07 TO 2026-01-05] → Get 50 papers, earliest: 2026-01-03
   Batch 3: [2024-01-07 TO 2026-01-03] → Get 50 papers, earliest: 2026-01-01
   ...continue until stop condition
   ```

3. **Smart Stop Conditions**:
   - **Target reached**: `len(new papers) >= max_results` (limited mode)
   - **Near start date**: Earliest time within `start_date + 1 day`
   - **No more papers**: Current batch returns 0 papers

4. **Sparse Time Period Handling**: If a batch returns papers < batch_size but time is still far from start_date, continue searching

**Configuration Parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `arxiv.batch_size` | 50 | Number of papers per batch search |
| `arxiv.batch_threshold_days` | 1.0 | Stop threshold (days), stop when earliest time is within this many days of start_date |
| `arxiv.fetch_interval` | 3.0 | Batch interval (seconds), avoid excessive load on arXiv servers |

**Advantages**:

- ✅ **Avoid Timeouts**: Each batch only requests 50 papers, API requests are fast and reliable
- ✅ **Memory Friendly**: Doesn't load 50000 papers into memory at once
- ✅ **Error Isolation**: Single batch failure doesn't affect other batches
- ✅ **Real-time Progress**: Shows progress and statistics immediately after each batch completes
- ✅ **Resume Support**: Works with incremental update mechanism, already fetched papers are automatically skipped

**Example Output**:

```
======================================================================
Fetching arXiv papers (BATCH MODE)
======================================================================
Categories: cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, cs.RO, cs.MA, cs.IR, cs.HC, stat.ML
Date range: 2024-01-07 to 2026-01-06
Max results: 100
Batch size: 50
Fetch interval: 3.0s (delay between batches)
Existing papers to skip: 6701
======================================================================

Batch 1: 50 papers fetched, earliest: 2026-01-05 15:30 (2.1s)
Sleeping 3.0s...

Batch 2: 50 papers fetched, earliest: 2026-01-03 09:15 (1.8s)
Sleeping 3.0s...

Batch 3: 25 papers fetched, earliest: 2026-01-01 12:00 (1.2s)
Reached max_results limit (100). Stopping.

======================================================================
Fetch complete
======================================================================
Total fetched:       125
Skipped (existing):  25
New papers:          100
======================================================================
```

## FAQ

### 1. How to Update the Paper Database?

The system uses incremental updates by default, automatically skipping existing papers.

**Option 1**: Use API (recommended for automation)
```bash
curl -X POST http://localhost:5001/api/v1/incremental_update \
  -H "Content-Type: application/json" \
  -d '{"max_results": 100}'
```

**Option 2**: Use CLI
```bash
python scripts/run_builder.py update --max-results 100
```

**Fetch All Papers** (unlimited):
```bash
# Use -1 for unlimited, fetch all papers that meet criteria
python scripts/run_builder.py update --max-results -1

# Or via API
curl -X POST http://localhost:5001/api/v1/incremental_update \
  -H "Content-Type: application/json" \
  -d '{"max_results": -1}'
```

**Progress Display**:

- **Normal Mode** (limited quantity): Shows progress bar
  ```
  Fetching papers: 45%|████████       | 450/1000 [01:30<01:50, 5.0 paper/s]
  fetched=600, filtered=500, new=450, skipped=50
  ```

- **Unlimited Mode** (-1 unlimited): Shows dynamic counter
  ```
  Fetching (unlimited): 150 papers | 2.5 paper/s | 00:01:00
  fetched=500, new=150, skipped=350
  ```

  - `150 papers` - Number of new papers added
  - `2.5 paper/s` - Real-time processing speed
  - `00:01:00` - Elapsed time
  - `fetched=500` - Total fetched from arXiv
  - `skipped=350` - Number skipped (already exists or didn't pass filtering)

**Why Doesn't Unlimited Mode Show "Total"?**

The total count returned by arXiv API (e.g., 100,000) is inaccurate because there are multiple filters:
```
API Total 100,000 (all cs.AI/cs.CL/cs.LG)
  ↓ Time filter (last 2 years) → ~30,000
  ↓ Keyword filter (AI/LLM) → ~10,000
  ↓ Deduplication (skip existing) → ~150 new papers
```
Showing "150/100,000 (0.15%)" would mislead users into thinking it will take much longer, when it may finish soon.

**Scheduled Task Example** (update daily at 2 AM):
```bash
# Add to crontab
0 2 * * * cd /path/to/arxiv_fetcher && /path/to/conda/envs/<your_env>/bin/python scripts/run_builder.py update --max-results 100
```

### 2. What to Do When Health Check Fails?

Check logs to troubleshoot:
```bash
# View latest logs
tail -f logs/api.log

# View error logs
tail -f logs/api.err

# View service status (includes log summary)
./shell/arxiv_service.sh status
```

Common issues:
- GPU unavailable: Check `nvidia-smi` to confirm GPU 3 is available
- Port occupied: Modify `api.port` in `config/default.yaml`
- Model loading failed: Check if `embedding.model_path` is correct

### 3. How to Rebuild the Database?

```bash
# Clear database
python scripts/run_builder.py clear

# Rebuild
python scripts/run_builder.py update --max-results 9000
```

### 4. How to Adjust Search Result Relevance?

Edit `config/default.yaml`:

```yaml
search:
  title_weight: 1.5      # Increase title weight
  abstract_weight: 1.0   # Keep abstract weight unchanged
```

Higher weight means that part is more important in similarity calculation.

### 5. How to Control Crawling Speed?

Use `fetch_interval` to set batch intervals, avoiding excessive load on arXiv servers:

```yaml
# config/default.yaml
arxiv:
  batch_size: 50
  fetch_interval: 1.0  # Pause 1 second after each batch
```

**Supports Decimals**:
- `0.5` - Pause 0.5 seconds after each batch
- `1.5` - Pause 1.5 seconds after each batch
- `2.0` - Pause 2 seconds after each batch
- `0` - No pause (fastest speed, not recommended)

**Recommended Settings**:
- Fast crawl: `0.5s` (25 seconds/batch)
- Normal speed: `1.0s` (50 seconds/batch)
- Polite mode: `2.0s` (100 seconds/batch)

**Time Estimation**:
```
Total time = (number of papers / batch_size) × fetch_interval

Example: 10000 papers, batch_size=50, fetch_interval=1.0
Total time = (10000 / 50) × 1.0 = 200 seconds ≈ 3.3 minutes
```

### 6. Service Won't Start?

Check conda environment:
```bash
# Confirm environment exists
conda env list

# If environment name is not myAgent, edit shell/arxiv_service.sh
# Modify CONDA_ENV variable
```

### 7. How to Switch Embedding Models?

**Important Note**: Embedding dimension is not hardcoded, the system automatically detects model dimensions. Currently using bge-m3 (1024-dimensional).

**Case 1: Same Dimension Models** (e.g., both 1024-dimensional)

Can directly modify config, but recommend rebuilding database to ensure search accuracy:

```yaml
# config/default.yaml
embedding:
  model_path: /path/to/new-1024d-model
  device: cuda:3
```

```bash
# Rebuild database (recommended)
python scripts/run_builder.py clear
python scripts/run_builder.py build --mode embed
```

**Case 2: Different Dimension Models** (e.g., 1024→768)

**Must clear old data and rebuild**, as ChromaDB collection dimension is fixed:

```bash
# 1. Clear old data
python scripts/run_builder.py clear

# 2. Modify config
vim config/default.yaml  # Change model_path

# 3. Rebuild (will automatically detect new dimension)
python scripts/run_builder.py build --mode all
```

**Case 3: Keep Old Data to Test New Model** (Recommended)

Use different collection name, new and old data don't affect each other:

```yaml
# config/default.yaml
database:
  collection_name: ArxivPapers_NewModel  # Change collection name

embedding:
  model_path: /path/to/new-model
```

Then just build normally, the system will create a new collection.

**Automatic Dimension Detection**:

The system automatically displays model dimension at startup:
```
Loading embedding model: /path/to/model
Device: cuda:3
✓ Embedding model loaded (dimension: 1024)
```

If dimension doesn't match old collection, query will fail with an error.

## System Architecture

```
┌─────────────────────────────────────┐
│   CLI/Bash (run_builder.py + sh)   │
│   - build fetch/embed               │
│   - update fetch/embed              │
└──────────────┬──────────────────────┘
               ↓
┌──────────────────────────────────────┐
│         Builder (builder.py)         │
│  - build_fetch() → CSV               │
│  - build_embed() → ChromaDB          │
│  - update_fetch() → CSV              │
│  - update_embed() → ChromaDB         │
└──────┬───────────────┬───────────────┘
       ↓               ↓
┌─────────────┐  ┌──────────────┐
│  Fetcher    │  │  CSVManager  │
│  (Fetch)    │  │  (CSV I/O)   │
└─────────────┘  └──────────────┘
                       ↓
                 ┌──────────────┐
                 │ ChromaDB     │
                 │ (Vector DB)  │
                 └──────────────┘
                       ↓
                 ┌──────────────┐
                 │ API Server   │
                 │ (Flask)      │
                 └──────────────┘
```

### Core Components

- **Fetcher** - arXiv paper fetcher
  - Categories: cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, cs.RO, cs.MA, cs.IR, cs.HC, stat.ML (10 categories)
  - No keyword filtering, comprehensive AI-related paper coverage
  - Time filtering: Supports days/weeks/months/years
  - Automatic deduplication: Based on paper ID

- **CSVManager** - CSV persistence manager
  - init_data.csv: Initial build data
  - daily/timestamp.csv: Incremental update data
  - UTF-8 BOM encoding, supports Chinese

- **Builder** - Database builder
  - Staged execution: fetch (crawl) and embed (embedding)
  - build mode: Full build
  - update mode: Incremental update
  - Dual embedding (title + abstract)

- **Searcher** - Semantic search engine
  - Dual similarity scoring
  - Weighted comprehensive ranking

- **API** - RESTful interface
  - Swagger/OpenAPI documentation
  - 6 main endpoints

### Data Flow

**Build Mode (Initial Build)**:
```
arXiv API → Fetcher (10 categories) → init_data.csv →
  Embedding → ChromaDB (Vector Database)
```

**Update Mode (Incremental Update)**:
```
arXiv API → Fetcher (deduplication) → daily/timestamp.csv →
  Embedding → ChromaDB (Incremental addition)
```

**Search Process**:
```
User query → API → Searcher → ChromaDB →
  Dual scoring → Sorted results → Return to client
```

## Directory Structure

```
arxiv_fetcher/
├── config/              # Configuration files
│   └── default.yaml     # Main configuration file
├── shell/               # Shell scripts
│   └── arxiv_service.sh # Service and data management script
├── logs/                # Log files (generated at runtime)
├── src/                 # Source code
│   ├── config/          # Configuration management (OmegaConf)
│   ├── core/            # Core business logic
│   │   ├── fetcher.py   # arXiv crawler
│   │   ├── builder.py   # Database builder
│   │   └── searcher.py  # Semantic search engine
│   ├── storage/         # CSV persistence
│   │   └── csv_manager.py
│   ├── database/        # Database management
│   │   └── chromadb_manager.py
│   └── api/             # API interface
├── scripts/             # Run scripts
│   ├── run_builder.py   # CLI tool
│   └── run_api.py       # API service
└── tests/               # Test files
```

## Data Storage Structure

```
/path/to/data/
├── chromadb_data/       # ChromaDB vector database
└── papers/              # CSV file storage
    ├── init_data.csv    # Initial build data
    └── daily/           # Incremental update data
        ├── 20260109_163622.csv
        ├── 20260110_020000.csv
        └── ...
```

## Tech Stack

- **Vector Database**: ChromaDB 1.4.0
- **Embedding Model**: bge-m3 (1024-dimensional, supports Chinese and English)
- **API Framework**: Flask 3.1.2 + Flask-RESTX 1.3.0
- **Configuration Management**: OmegaConf 2.3.0
- **Crawler**: arxiv 2.1.3 (Python library)
- **Deep Learning**: PyTorch 2.9.1
- **Text Embedding**: sentence-transformers 5.2.0
- **Production Server**: gunicorn 23.0.0 (optional)

## Performance Features

- **GPU Acceleration**: Uses cuda:3 to accelerate embedding computation
- **Batch Processing**: Default batch size 32 (embedding) / 50 (fetching)
- **Incremental Updates**: Automatic deduplication, supports resume
- **Vector Normalization**: Improves search accuracy
- **Dual Scoring**: Considers both title and abstract similarity

## License

MIT License
