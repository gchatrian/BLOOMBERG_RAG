# Bloomberg RAG - CLI Guide

Complete guide for using the Bloomberg RAG command-line interface.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Commands](#commands)
   - [sync](#sync-command)
   - [status](#status-command)
   - [search](#search-command)
   - [cleanup](#cleanup-command)
4. [Common Workflows](#common-workflows)
5. [Troubleshooting](#troubleshooting)

---

## Overview

The Bloomberg RAG CLI (`main.py`) provides a unified interface for:

- **Syncing** emails from Outlook to the vector store
- **Checking status** of the system
- **Searching** indexed emails without LLM
- **Cleaning up** old stubs and processed emails

**Entry Point:** `python main.py <command> [options]`

---

## Installation

### Prerequisites

1. **Python 3.8+**
2. **Outlook** (Windows COM interface)
3. **Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Setup

1. **Configure Outlook folders:**
   - Create folder structure: `Inbox/Bloomberg subs/` with subfolders:
     - `indexed/` - Processed emails
     - `stubs/` - Incomplete emails
     - `processed/` - Completed stubs

2. **First-time setup:**
   ```bash
   # Check system status
   python main.py status
   
   # Run first sync
   python main.py sync
   ```

---

## Commands

### Quick Reference

```bash
# Sync emails
python main.py sync [--max-emails N] [--verbose]

# Show status
python main.py status [--detailed]

# Search
python main.py search "query" [--top-k N] [--weight W] [filters]
python main.py search --interactive

# Cleanup
python main.py cleanup [--delete-old-stubs DAYS] [--archive-processed MONTHS]
```

---

## SYNC Command

Synchronize emails from Outlook source folder to the vector store.

### Basic Usage

```bash
# Sync all emails in source folder
python main.py sync

# Sync with limit (useful for testing)
python main.py sync --max-emails 100

# Verbose output (show detailed logs)
python main.py sync --verbose
```

### What It Does

1. ✅ Scans `Inbox/Bloomberg subs/` (source folder)
2. ✅ Identifies **stub** vs **complete** emails
3. ✅ For **stubs**:
   - Registers in stub_registry.json
   - Moves to `/stubs/` folder
4. ✅ For **complete** emails:
   - Cleans content
   - Extracts metadata (topics, people, tickers, author, date)
   - Checks for matching stub (by story_id or fingerprint)
   - If match found: moves stub from `/stubs/` to `/processed/`
   - Generates embedding
   - Adds to FAISS vector store
   - Moves email to `/indexed/` folder
5. ✅ Generates stub report (stubs still pending in `/stubs/`)
6. ✅ Shows final statistics

### Output Example

```
============================================================
BLOOMBERG RAG - EMAIL SYNC
============================================================
Started at: 2025-11-20 14:30:00

Initializing components...
Loading existing vector store from data/faiss_index.bin
Starting ingestion pipeline...
Extracted 25 emails from source folder

Processing email: Fed Holds Rates Steady
Detected COMPLETE: Fed Holds Rates Steady
Complete email indexed and moved to /indexed/

Processing email: Tesla Earnings Alert
Detected STUB: Tesla Earnings Alert
Stub registered and moved to /stubs/

============================================================
STUB REPORT
============================================================
Total stubs pending: 5
Stubs awaiting manual completion:
1. Tesla Earnings Alert (Story ID: abc123)
2. Apple Product Launch (Story ID: xyz789)
...

============================================================
SYNC COMPLETED SUCCESSFULLY
============================================================
Total emails processed: 25
Complete emails → /indexed/: 20
New stubs → /stubs/: 3
Stubs completed → /processed/: 2
Errors: 0
Duration: 45.32 seconds
============================================================
```

### Options

| Option | Description | Example |
|--------|-------------|---------|
| `--max-emails N` | Process max N emails | `--max-emails 100` |
| `--verbose, -v` | Show debug logs | `--verbose` |

---

## STATUS Command

Display current system status.

### Basic Usage

```bash
# Quick status
python main.py status

# Detailed status (includes top topics/authors)
python main.py status --detailed
```

### What It Shows

- 📁 **Outlook Folders:** Email counts in source/indexed/stubs/processed
- 🗄️ **Vector Store:** Number of indexed documents, dimension
- 📋 **Stub Statistics:** Total/pending/completed stubs
- 🔄 **Last Sync:** Date, stats from last sync operation
- 📊 **Top Topics/Authors:** (with `--detailed`)

### Output Example

```
============================================================
BLOOMBERG RAG - SYSTEM STATUS
============================================================
Timestamp: 2025-11-20 14:45:00

📁 OUTLOOK FOLDERS
------------------------------------------------------------
  Source folder:       12 emails
  Indexed:           1,234 emails
  Stubs (pending):       5 emails
  Processed (done):     89 emails

🗄️  VECTOR STORE
------------------------------------------------------------
  Documents indexed: 1,234
  Embedding dimension: 768
  Index file: data/faiss_index.bin

📋 STUB STATISTICS
------------------------------------------------------------
  Total stubs:        94
  Pending:             5
  Completed:          89

🔄 LAST SYNC
------------------------------------------------------------
  Date: 2025-11-20 14:30:00
  Emails processed:  25
  → Indexed:         20
  → Stubs created:    3
  → Stubs completed:  2
  Errors:            0
  Duration:          45.32s

============================================================
```

### Options

| Option | Description |
|--------|-------------|
| `--detailed, -d` | Show top topics and authors |

---

## SEARCH Command

Search indexed emails with semantic and temporal ranking.

### Basic Usage

```bash
# Simple search
python main.py search "Federal Reserve interest rates"

# Interactive mode
python main.py search --interactive

# Advanced search with filters
python main.py search "Tesla" --topics Technology --tickers TSLA --top-k 5
```

### Search Modes

#### 1. **Direct Query Mode**
```bash
python main.py search "artificial intelligence regulation"
```
Runs search once and shows results.

#### 2. **Interactive Mode**
```bash
python main.py search --interactive
```

Starts interactive shell:
```
> Federal Reserve interest rates
> /set top_k 20
> /set weight 0.5
> AI regulation Europe
> /exit
```

**Interactive Commands:**
- `/set top_k N` - Set number of results
- `/set weight W` - Set recency weight (0.0-1.0)
- `/help` - Show help
- `/exit` - Exit

### Filtering

```bash
# Filter by date range
python main.py search "Tesla" --start-date 2024-01-01 --end-date 2024-12-31

# Filter by topics
python main.py search "climate" --topics Energy Climate

# Filter by people
python main.py search "policy" --people "Jerome Powell" "Janet Yellen"

# Filter by tickers
python main.py search "earnings" --tickers AAPL GOOGL MSFT

# Combine filters
python main.py search "tech earnings" \
  --start-date 2024-10-01 \
  --topics Technology \
  --tickers AAPL GOOGL
```

### Tuning Parameters

```bash
# Adjust number of results
python main.py search "AI" --top-k 20

# Adjust recency weight (0.0 = semantic only, 1.0 = temporal only)
python main.py search "news" --weight 0.8  # Favor recent articles

# Combine tuning
python main.py search "markets" --top-k 15 --weight 0.5
```

### Output Example

```
============================================================
SEARCH QUERY
============================================================
Query: Federal Reserve interest rates
Top-K: 10
Recency Weight: 0.3

Searching...
Found 10 results

============================================================
RANK #1
============================================================
Subject: Fed Holds Rates Steady at 5.25-5.50%
Date:    2024-10-15
Author:  Jane Doe
Topics:  Finance, Central Banks, Monetary Policy
People:  Jerome Powell
Tickers: 

Scores:
  Semantic:  0.8923
  Temporal:  0.9156
  Combined:  0.8993

Snippet:
The Federal Reserve maintained interest rates at 5.25-5.50% 
at its October meeting, citing ongoing inflation concerns...

============================================================
RANK #2
============================================================
...
```

### Options

| Option | Description | Example |
|--------|-------------|---------|
| `--interactive, -i` | Interactive mode | `--interactive` |
| `--top-k N` | Number of results | `--top-k 20` |
| `--weight W` | Recency weight 0-1 | `--weight 0.5` |
| `--start-date` | Start date (YYYY-MM-DD) | `--start-date 2024-01-01` |
| `--end-date` | End date (YYYY-MM-DD) | `--end-date 2024-12-31` |
| `--topics` | Topic filters | `--topics Technology Finance` |
| `--people` | People filters | `--people "Elon Musk"` |
| `--tickers` | Ticker filters | `--tickers TSLA AAPL` |

---

## CLEANUP Command

Maintenance operations for stubs and processed emails.

### Basic Usage

```bash
# Delete old stubs (older than 30 days)
python main.py cleanup --delete-old-stubs 30

# Archive old processed emails (older than 6 months)
python main.py cleanup --archive-processed 6

# Rebuild stub registry from Outlook folders
python main.py cleanup --rebuild-registry

# Run all cleanup operations
python main.py cleanup --all

# Dry run (show what would happen)
python main.py cleanup --all --dry-run
```

### Operations

#### 1. **Delete Old Stubs**
```bash
python main.py cleanup --delete-old-stubs 30
```
- Deletes stubs in `/stubs/` older than 30 days
- Removes from stub_registry.json
- Asks for confirmation

#### 2. **Archive Processed**
```bash
python main.py cleanup --archive-processed 6
```
- Archives processed stubs in `/processed/` older than 6 months
- Frees up Outlook space
- Asks for confirmation

#### 3. **Rebuild Registry**
```bash
python main.py cleanup --rebuild-registry
```
- Scans `/stubs/` and `/processed/` folders
- Rebuilds stub_registry.json from scratch
- Useful if registry gets corrupted

#### 4. **Dry Run**
```bash
python main.py cleanup --all --dry-run
```
- Shows what WOULD be done
- No actual changes made
- Useful for testing

### Options

| Option | Description | Example |
|--------|-------------|---------|
| `--delete-old-stubs DAYS` | Delete stubs older than N days | `--delete-old-stubs 30` |
| `--archive-processed MONTHS` | Archive processed older than N months | `--archive-processed 6` |
| `--rebuild-registry` | Rebuild stub registry | `--rebuild-registry` |
| `--all` | Run all operations | `--all` |
| `--dry-run` | Show without doing | `--dry-run` |

---

## Common Workflows

### 1. **First-Time Setup**

```bash
# 1. Check system status
python main.py status

# 2. Run initial sync
python main.py sync

# 3. Check status again
python main.py status --detailed
```

### 2. **Daily Sync Routine**

```bash
# Morning: sync new emails
python main.py sync

# Check for new stubs to complete manually
python main.py status

# Complete stubs manually via Bloomberg Terminal
# Then sync again to match completed stubs
python main.py sync
```

### 3. **Research Workflow**

```bash
# 1. Search for topic
python main.py search "semiconductor supply chain" --topics Technology

# 2. Refine search with filters
python main.py search "semiconductor" \
  --start-date 2024-01-01 \
  --topics Technology \
  --tickers TSM INTC

# 3. Interactive exploration
python main.py search --interactive
```

### 4. **Monthly Maintenance**

```bash
# 1. Delete old stubs (30+ days)
python main.py cleanup --delete-old-stubs 30

# 2. Archive old processed (6+ months)
python main.py cleanup --archive-processed 6

# 3. Check status
python main.py status
```

---

## Troubleshooting

### Problem: "Vector store not found"

**Solution:**
```bash
# Run sync first to create the index
python main.py sync
```

### Problem: "Could not access Outlook folders"

**Solution:**
- Ensure Outlook is installed (Windows only)
- Check folder structure: `Inbox/Bloomberg subs/` exists
- Run Outlook at least once manually
- Check permissions

### Problem: Sync is slow

**Solution:**
```bash
# Limit emails processed
python main.py sync --max-emails 100

# Or sync in batches
python main.py sync --max-emails 50
python main.py sync --max-emails 50
```

### Problem: Too many stubs pending

**Solution:**
1. Complete stubs manually via Bloomberg Terminal
2. Save complete articles to Outlook source folder
3. Run sync to match and complete stubs:
   ```bash
   python main.py sync
   ```

### Problem: Stub registry corrupted

**Solution:**
```bash
# Rebuild from Outlook folders
python main.py cleanup --rebuild-registry
```

### Problem: Search returns no results

**Solution:**
- Check if vector store is populated:
  ```bash
  python main.py status
  ```
- Try broader query
- Reduce filters
- Check date ranges

---

## Getting Help

### Command Help

```bash
# General help
python main.py --help

# Command-specific help
python main.py sync --help
python main.py status --help
python main.py search --help
python main.py cleanup --help
```

### Logs

Check `logs/sync_emails.log` for detailed logs.

---

## Summary

| Task | Command |
|------|---------|
| Sync emails | `python main.py sync` |
| Check status | `python main.py status` |
| Quick search | `python main.py search "query"` |
| Interactive search | `python main.py search -i` |
| Delete old stubs | `python main.py cleanup --delete-old-stubs 30` |
| Full cleanup | `python main.py cleanup --all` |

**Next:** Use `agent.py` for LLM-powered queries (see agent documentation).