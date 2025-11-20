bloomberg-rag/
│
├── agent.py                 # 🆕 FASE 12: Google ADK Agent (main entry point)
├── agent_prompt.py          # 🆕 FASE 12: System instructions per agent
│
├── tools/                   # 🆕 FASE 7: Google ADK Tools (uno per file)
│   ├── __init__.py
│   ├── hybrid_search.py     # Tool: ricerca ibrida (semantic + temporal + filters)
│   ├── semantic_search.py   # Tool: ricerca semantica base
│   ├── filter_by_date.py    # Tool: filtra per date range
│   ├── filter_by_topic.py   # Tool: filtra per Bloomberg topics
│   ├── filter_by_people.py  # Tool: filtra per people menzionati
│   └── filter_by_ticker.py  # Tool: filtra per Bloomberg tickers
│
├── config/
│   └── settings.py          # ✅ COMPLETATO - Tutte le configurazioni
│
├── src/
│   ├── __init__.py          # ✅ COMPLETATO - Package marker
│   │
│   ├── models.py            # ✅ COMPLETATO - Dataclasses (EmailDocument, BloombergMetadata)
│   │
│   ├── outlook/             # ✅ COMPLETATO - FASE 1: Data Ingestion (SOLO per script sync)
│   │   ├── __init__.py      
│   │   └── extractor.py     # Connessione Outlook + estrazione + folder management (UNIFICATO)
│   │
│   ├── processing/          # ✅ COMPLETATO - FASE 1-2: Cleaning & Metadata (SOLO per script sync)
│   │   ├── __init__.py
│   │   ├── cleaner.py       # Pulizia HTML, encoding, disclaimers
│   │   ├── metadata_extractor.py  # Estrae metadati Bloomberg (author, topics, people, story_id, tickers)
│   │   └── document_builder.py    # Combina tutto in EmailDocument
│   │
│   ├── stub/                # ✅ COMPLETATO - FASE 2: Stub Management (SOLO per script sync)
│   │   ├── __init__.py
│   │   ├── detector.py      # Identifica stub vs complete
│   │   ├── registry.py      # Gestisce stub_registry.json
│   │   ├── manager.py       # Organizza e sposta stub
│   │   ├── matcher.py       # Match stub↔complete (story_id + fingerprint)
│   │   └── reporter.py      # Genera report stub per utente
│   │
│   ├── embedding/           # FASE 3: Embeddings
│   │   ├── __init__.py
│   │   ├── generator.py     # Sentence-transformers wrapper
│   │   └── batch_processor.py  # Batch encoding per efficienza
│   │
│   ├── vectorstore/         # FASE 3: Vector Database
│   │   ├── __init__.py
│   │   ├── faiss_store.py   # Wrapper FAISS (add, search, save/load)
│   │   └── metadata_mapper.py  # Mapping vector_id ↔ EmailDocument
│   │
│   ├── retrieval/           # FASE 5-6: Search & Ranking (USATO da Google ADK tools)
│   │   ├── __init__.py
│   │   ├── semantic_retriever.py   # Ricerca semantica base
│   │   ├── temporal_scorer.py      # Recency scoring (exponential decay)
│   │   ├── metadata_filter.py      # Filtering per topics/people/date/ticker
│   │   └── hybrid_retriever.py     # Combina semantic + temporal + filters
│   │
│   ├── orchestration/       # FASE 8: Pipeline Coordination (SOLO per script sync)
│   │   ├── __init__.py
│   │   ├── ingestion_pipeline.py  # Source → clean → stub check → indexed/stubs
│   │   └── indexing_pipeline.py   # Documents → embeddings → FAISS
│   │
│   └── utils/               # Utilities trasversali
│       ├── __init__.py
│       ├── persistence.py   # Save/load pickle, JSON
│       ├── logger.py        # Logging configurato
│       └── progress.py      # Progress bars (tqdm)
│
├── scripts/                 # FASE 9: Script Eseguibili (Manual sync/maintenance)
│   ├── sync_emails.py       # Sincronizza Outlook → vector store
│   ├── status.py            # Mostra stato sistema (folders, index size, stats)
│   ├── search.py            # Ricerca interattiva (no LLM)
│   └── cleanup.py           # Manutenzione (archivia vecchi stub)
│
├── data/                    # FASE 4: Persistence (creato automaticamente)
│   ├── faiss_index.bin      # Indice FAISS
│   ├── documents_metadata.pkl  # Mapping vector_id → metadati
│   ├── emails.pkl           # Lista completa EmailDocument
│   ├── stub_registry.json   # Tracking stub (story_id, status, timestamps)
│   └── last_sync.json       # Statistiche ultimo sync
│
├── logs/                    # Log files (creato automaticamente)
│   └── bloomberg_rag.log
│
├── main.py                  # FASE 10: Entry point CLI unificato (sync/status/maintenance)
├── requirements.txt         # ✅ COMPLETATO - Dipendenze Python
└── README.md                # FASE 11: Documentazione