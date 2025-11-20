# BLOOMBERG RAG - ROADMAP

## WORKFLOW DEL SISTEMA

### Overview
Il sistema estrae email Bloomberg da Outlook, le processa per creare un database vettoriale ricercabile, e permette di interrogare le email tramite un agente RAG che combina ricerca semantica e generazione LLM. La deduplication è gestita tramite cartelle Outlook: email processate vengono spostate automaticamente in sottocartelle dedicate.

### Struttura Cartelle Outlook
```
Inbox/
└── Bloomberg subs/              ← SOURCE (email da processare)
    ├── indexed/                 ← Email complete processate e indicizzate
    ├── stubs/                   ← Stub in attesa di completamento manuale
    └── processed/               ← Stub completati (archivio)
```

### Flusso Completo
```
┌─────────────────────────────────────────────────────────────────┐
│                    FASE 1: DATA INGESTION                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
    Outlook Source Folder → Extract Raw Emails
                              ↓
              ┌───────────────┴────────────────┐
              ↓                                 ↓
         È STUB?                           È COMPLETE?
              ↓                                 ↓
    Estrai Story ID                    Estrai Story ID
    Crea Fingerprint                   Clean Content
    Registra in stub_registry          Extract Metadata
              ↓                                 ↓
    Sposta in /stubs/                  Check stub match
    Genera Report                              ↓
              ↓                         ┌──────┴──────┐
        [Attesa]                        ↓             ↓
              ↓                    Match stub?    No match
     [Manual Terminal]                  ↓             ↓
              ↓                    Sposta stub   Processa
         Complete                  in /processed     ↓
         arriva                          ↓       Generate
              └──────────────────────────┴─→    Embedding
                                                      ↓
                                          Sposta in /indexed/

┌─────────────────────────────────────────────────────────────────┐
│                    FASE 2: EMBEDDING & INDEXING                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
         Email in /indexed/ → Generate Embeddings
                              ↓
              Store in Vector Database (FAISS)
                              ↓
                Save Index + Metadata to Disk

┌─────────────────────────────────────────────────────────────────┐
│                    FASE 3: RETRIEVAL                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
              User Query → Generate Query Embedding
                              ↓
                    Semantic Search (top-K)
                              ↓
              Apply Temporal Scoring (recency boost)
                              ↓
         Apply Metadata Filtering (topics, people, date)
                              ↓
                    Hybrid Ranking & Re-ranking
                              ↓
                    Top-N Relevant Documents

┌─────────────────────────────────────────────────────────────────┐
│                    FASE 4: GENERATION                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
           Build Context from Retrieved Documents
                              ↓
              Construct Prompt with Metadata
                              ↓
              Send to LLM (Claude/GPT)
                              ↓
              Stream Response to User
```

### Deduplication Strategy

**Principio:** Outlook stesso è il "database" di stato. Ogni email esiste in una sola cartella alla volta.

**Regole:**
- Email in `/Bloomberg subs/` (source) → DA PROCESSARE
- Email in `/Bloomberg subs/indexed/` → GIÀ PROCESSATA (skip durante sync)
- Email in `/Bloomberg subs/stubs/` → STUB IN ATTESA (skip durante sync)
- Email in `/Bloomberg subs/processed/` → STUB COMPLETATO (archivio, skip)

**Vantaggi:**
- Zero file di tracking complessi
- Visualmente chiaro in Outlook
- Reversibile (sposta email indietro per riprocessare)
- Outlook backup include tutto lo stato

### Data Flow

**Email → Processed Document:**
- Raw email text + metadata
- Cleaned content (no HTML, disclaimers)
- Extracted Bloomberg metadata (topics, people, author, date)
- Stub status determination (complete/stub)
- Outlook EntryID (ID univoco)
- Bloomberg Story ID (per matching)

**Document → Vector:**
- Full text embedding (384-dim vector)
- Stored with document ID and metadata

**Stub → Complete Matching:**
- Story ID match (primario)
- Fingerprint match (fallback: subject + date)
- Stub originale → /processed/ quando complete arriva

**Query → Response:**
- Query embedding → Semantic search
- Retrieved documents → Temporal + metadata scoring
- Top documents + metadata → LLM prompt
- LLM generation → Final response

---

## FASE 1: DATA INGESTION FOUNDATION

**Obiettivo:** Estrarre email da Outlook e prepararle per l'embedding

### Task 1.1: Configurazione Base
- [ ] Creare struttura cartelle del progetto
- [ ] Setup `config/settings.py` con tutte le configurazioni
- [ ] Definire dataclass per EmailDocument (subject, body, metadata, status, outlook_entry_id)
- [ ] Definire dataclass per Metadata Bloomberg (author, article_date, topics, people, category, story_id)
- [ ] Configurare percorsi cartelle Outlook (source, indexed, stubs, processed)

### Task 1.2: Outlook Extractor
- [ ] Implementare connessione a Outlook via COM
- [ ] Navigare struttura cartelle Outlook
- [ ] Estrarre dati raw da ogni email (subject, body, HTML, sender, date)
- [ ] **Estrarre Outlook EntryID univoco da ogni messaggio**
- [ ] **Implementare metodo per spostare email tra cartelle Outlook**
- [ ] **Implementare scan selettivo (solo source folder, skip indexed/stubs/processed)**
- [ ] Gestire errori di accesso e permessi
- [ ] Implementare sorting per data (più recenti prima)
- [ ] Limitare numero email estratte (per testing)

### Task 1.3: Content Cleaner
- [ ] Rimuovere disclaimer email ("External Email...")
- [ ] Convertire HTML in testo pulito (BeautifulSoup)
- [ ] Correggere encoding issues (â€™ → ', etc.)
- [ ] Rimuovere link footer Bloomberg
- [ ] Normalizzare whitespace
- [ ] Separare header da contenuto principale

### Task 1.4: Metadata Extractor
- [ ] Estrarre categoria Bloomberg dall'oggetto (BFW, BI, BBF)
- [ ] Estrarre data articolo (priorità su data ricezione email)
- [ ] Estrarre autore dal corpo ("By [Name]")
- [ ] **Estrarre Bloomberg Story ID da URL nel body**
- [ ] **Estrarre sezione "People" da fine email**
- [ ] **Estrarre sezione "Topics" da fine email**
- [ ] Validare e normalizzare date
- [ ] Gestire email senza metadati completi

### Task 1.5: Document Builder
- [ ] Combinare dati puliti + metadati in EmailDocument
- [ ] Creare testo completo per embedding (subject + metadata + body)
- [ ] Assegnare ID univoci alle email (Outlook EntryID)
- [ ] Validare completezza documenti

---

## FASE 2: STUB MANAGEMENT

**Obiettivo:** Identificare email incomplete, gestirne il completamento, e cleanup automatico

### Task 2.1: Stub Detector
- [ ] Implementare euristica per identificare stub (content < 200 char + link Bloomberg)
- [ ] Estrarre link Bloomberg da stub
- [ ] Estrarre Story ID da URL Bloomberg
- [ ] Classificare email come "complete" o "stub"

### Task 2.2: Stub Registry & Tracking
- [ ] Creare `stub_registry.json` per tracking minimale stub
- [ ] Schema: {outlook_entry_id, story_id, subject, fingerprint, received_time, status}
- [ ] Registrare stub con status "pending" quando identificato
- [ ] **Implementare fingerprinting per matching fallback (subject + timestamp normalizzato)**
- [ ] Salvare story_id e fingerprint per ogni stub
- [ ] Load/save registry da disco

### Task 2.3: Stub Movement & Organization
- [ ] **Quando stub identificato: spostare in `/stubs/` folder**
- [ ] Aggiornare registry con nuova posizione
- [ ] Mantenere lista stub attivi per report

### Task 2.4: Stub-Complete Matching & Cleanup
- [ ] **Durante processing email complete: estrarre story_id**
- [ ] **Cercare in stub_registry match per story_id (metodo primario)**
- [ ] **Fallback: cercare match per fingerprint se no story_id**
- [ ] **Se match trovato: recuperare stub fisico da /stubs/ tramite EntryID**
- [ ] **Spostare stub originale da /stubs/ a /processed/**
- [ ] Aggiornare registry: status "pending" → "completed"
- [ ] Registrare timestamp completamento
- [ ] Loggare stub completati per report

### Task 2.5: Stub Reporter
- [ ] Generare report testuale degli stub pendenti (in /stubs/)
- [ ] Includere istruzioni dettagliate per completamento manuale via Terminal
- [ ] Listare link Bloomberg da aprire
- [ ] Includere Story ID per ogni stub
- [ ] Contare statistiche (totale stub, completati nella sessione, ancora pendenti)
- [ ] Mostrare stub recentemente completati (spostati in /processed/)

---

## FASE 3: EMBEDDING & VECTOR STORE

**Obiettivo:** Creare rappresentazioni vettoriali delle email e indicizzarle

### Task 3.1: Embedding Generator
- [ ] Inizializzare sentence-transformers model (multilingual)
- [ ] Implementare batch encoding per efficienza
- [ ] Generare embeddings per lista documenti
- [ ] Gestire documenti singoli
- [ ] Normalizzare vettori output (float32)

### Task 3.2: Vector Store
- [ ] Implementare wrapper per FAISS IndexFlatL2
- [ ] Aggiungere vettori all'indice con metadati
- [ ] Implementare ricerca k-nearest neighbors
- [ ] Mappare ID vettore → metadati documento (include Outlook EntryID)
- [ ] Gestire indice vuoto e crescita incrementale

### Task 3.3: Indexing Pipeline
- [ ] Coordinare: documenti → embeddings → vector store
- [ ] **Processare solo email in source folder (skip indexed/stubs/processed)**
- [ ] Gestire batch processing per grandi volumi
- [ ] Mostrare progress durante indicizzazione
- [ ] Validare dimensioni e integrità indice
- [ ] **Dopo embedding success: spostare email in /indexed/**

---

## FASE 4: PERSISTENCE

**Obiettivo:** Salvare e caricare stato del sistema

### Task 4.1: Persistence Manager
- [ ] Salvare lista EmailDocument in pickle
- [ ] Serializzare indice FAISS
- [ ] Salvare mapping metadati (include Outlook EntryID per ogni vettore)
- [ ] **Salvare stub_registry.json separatamente**
- [ ] Caricare tutto lo stato precedente
- [ ] Gestire versioning formato dati
- [ ] Implementare backup automatico

### Task 4.2: Data Directory Management
- [ ] Creare struttura directory `data/`
- [ ] Organizzare file (index.faiss, emails.pkl, stub_registry.json)
- [ ] Gestire file temporanei durante sync
- [ ] Implementare cleanup vecchie versioni
- [ ] **Salvare statistiche sync (last_sync.json) con conteggi folder**

---

## FASE 5: SEMANTIC RETRIEVAL

**Obiettivo:** Ricerca semantica base nei documenti

### Task 5.1: Semantic Retriever
- [ ] Generare embedding per query utente
- [ ] Cercare top-K vettori simili in FAISS
- [ ] Recuperare metadati documenti corrispondenti (include Bloomberg topics/people)
- [ ] Normalizzare distance scores (0-1)
- [ ] Ritornare risultati con score semantico

### Task 5.2: Result Formatting
- [ ] Strutturare risultati (index, score, metadata, content)
- [ ] Troncare contenuto lungo per preview
- [ ] Formattare date in modo human-readable
- [ ] **Includere Bloomberg topics e people nei risultati**
- [ ] Preparare struttura per downstream processing

---

## FASE 6: TEMPORAL & METADATA RANKING

**Obiettivo:** Aggiungere ranking basato su recency e metadati Bloomberg

### Task 6.1: Temporal Scorer
- [ ] Implementare exponential decay basato su article_date
- [ ] Configurare halflife (giorni per dimezzamento score)
- [ ] Calcolare recency score per ogni risultato
- [ ] Gestire documenti senza data (fallback)

### Task 6.2: Metadata Filter
- [ ] **Implementare filtering per Bloomberg topics (exact match da sezione Topics)**
- [ ] **Implementare filtering per Bloomberg people (exact match da sezione People)**
- [ ] Implementare filtering per range di date (article_date)
- [ ] Implementare filtering per autore (By...)
- [ ] Supportare filtri combinati (AND/OR logic)
- [ ] **Query expansion: se query contiene topic conosciuto, boost risultati con quel topic**

### Task 6.3: Hybrid Retriever
- [ ] Combinare semantic score + temporal score con pesi configurabili
- [ ] Applicare metadata filters pre o post similarity search
- [ ] Implementare re-ranking finale
- [ ] Ordinare per score combinato
- [ ] Ritornare top-N risultati finali
- [ ] Permettere tuning dinamico pesi (semantic vs temporal)

---

## FASE 7: LLM INTEGRATION

**Obiettivo:** Integrare LLM per generare risposte basate sui documenti recuperati

### Task 7.1: LLM Client
- [ ] Implementare client per Anthropic Claude
- [ ] Implementare client per OpenAI GPT
- [ ] Gestire API keys da environment o config
- [ ] Implementare retry logic per rate limits
- [ ] Gestire streaming response
- [ ] Gestire errori API

### Task 7.2: Prompt Builder
- [ ] Costruire prompt con contesto dai documenti recuperati
- [ ] **Includere metadati Bloomberg (date, autori, topics, people)**
- [ ] Formattare documenti multipli in modo leggibile
- [ ] Ordinare documenti per rilevanza nel prompt
- [ ] Aggiungere istruzioni sistema (rispondere solo da contesto, citare fonti)
- [ ] Gestire token limit (troncare documenti se necessario)
- [ ] **Supportare citazioni esplicite con data e autore**

### Task 7.3: Response Handler
- [ ] Parsare risposta LLM
- [ ] Estrarre citazioni e riferimenti
- [ ] Formattare risposta per utente
- [ ] Gestire errori e fallback

---

## FASE 8: ORCHESTRATION

**Obiettivo:** Coordinare tutti i componenti in pipeline funzionanti

### Task 8.1: Ingestion Pipeline
- [ ] **Coordinare: extract da source → detect stub → move to stubs OR (clean → metadata → check stub match → move stub to processed → embed → move to indexed)**
- [ ] **Implementare logica decisionale: stub vs complete**
- [ ] **Per email complete: check match con stub esistenti (via story_id o fingerprint)**
- [ ] **Se match: spostare stub da /stubs/ a /processed/ prima di processare**
- [ ] Gestire errori in singole email senza bloccare tutto
- [ ] Logging progresso e statistiche
- [ ] **Report finale: N complete→indexed, N stub→stubs, N stub completed→processed**

### Task 8.2: Indexing Pipeline
- [ ] Coordinare: documenti complete → embeddings → vector store
- [ ] **Processare solo email in source folder (automatic dedup via folder structure)**
- [ ] Gestire indicizzazione incrementale
- [ ] Salvare stato dopo indicizzazione

### Task 8.3: Search Pipeline
- [ ] Coordinare: query → semantic search → temporal ranking → metadata filtering
- [ ] Applicare configurazione weights e filters
- [ ] Ritornare risultati formattati con metadati Bloomberg

### Task 8.4: RAG Agent
- [ ] Integrare search pipeline + LLM
- [ ] Ricevere query utente
- [ ] Recuperare documenti rilevanti
- [ ] Costruire prompt con contesto + metadati Bloomberg
- [ ] Generare risposta via LLM
- [ ] Ritornare risposta finale + documenti source con citazioni

---

## FASE 9: SCRIPTS & AUTOMATION

**Obiettivo:** Creare script standalone per operazioni comuni

### Task 9.1: Sync Script
- [ ] Script `sync_emails.py` per sincronizzazione completa
- [ ] **Scannare solo source folder (Inbox/Bloomberg subs)**
- [ ] **Skip automatico di /indexed/, /stubs/, /processed/**
- [ ] Processare email nuove
- [ ] **Identificare stub → spostare in /stubs/**
- [ ] **Identificare complete → check stub match → se match: stub to /processed/**
- [ ] **Indicizzare email complete → spostare in /indexed/**
- [ ] Generare report stub (ancora in /stubs/)
- [ ] **Mostrare statistiche: N→indexed, N→stubs, N stub completed**

### Task 9.2: Status Script
- [ ] Script `status.py` per visualizzare stato sistema
- [ ] Contare email in ogni cartella Outlook (indexed, stubs, processed)
- [ ] Mostrare dimensione vector store
- [ ] Mostrare statistiche stub (pending, completed)
- [ ] Mostrare data ultimo sync
- [ ] Mostrare top topics e autori indicizzati

### Task 9.3: Interactive Search Script
- [ ] Script `search.py` per testare ricerca
- [ ] Caricare indice esistente
- [ ] Accettare query da command line o interattivo
- [ ] Mostrare top-K risultati con metadati Bloomberg
- [ ] Mostrare score breakdown (semantic, temporal, final)
- [ ] Permettere tuning parametri (weights, top_k, halflife)
- [ ] Supportare filtering per topics/people/date

### Task 9.4: RAG Query Script
- [ ] Script `query_rag.py` per interrogazione completa
- [ ] Interfaccia command line o interattiva
- [ ] Query → RAG agent → risposta LLM
- [ ] Mostrare documenti source utilizzati con metadati
- [ ] Supportare conversazioni multi-turn (memoria temporanea)
- [ ] Mostrare citazioni esplicite

### Task 9.5: Cleanup Script (opzionale)
- [ ] Script `cleanup.py` per manutenzione
- [ ] Opzione: cancellare stub in /stubs/ più vecchi di N giorni
- [ ] Opzione: archiviare /processed/ più vecchi di N mesi
- [ ] Opzione: ricostruire stub_registry da scan cartelle

---

## FASE 10: MAIN APPLICATION

**Obiettivo:** Entry point unificato per tutte le operazioni

### Task 10.1: CLI Interface
- [ ] Implementare `main.py` con argparse o click
- [ ] Comando: `sync` - sincronizza email (source → indexed/stubs/processed)
- [ ] Comando: `status` - mostra statistiche sistema e cartelle
- [ ] Comando: `search <query>` - ricerca interattiva
- [ ] Comando: `query <question>` - RAG agent interattivo
- [ ] Comando: `cleanup` - manutenzione cartelle
- [ ] Help e documentazione comandi
- [ ] **Mostrare folder status prima/dopo ogni operazione**

### Task 10.2: Configuration Management
- [ ] Permettere override config da CLI (weights, halflife, top_k)
- [ ] Supportare config file (YAML/JSON)
- [ ] Validare configurazioni (folder paths, API keys)
- [ ] Mostrare config attiva
- [ ] Template config per casi d'uso (breaking news vs research)

---

## FASE 11: DOCUMENTATION & POLISH

**Obiettivo:** Documentare il sistema e renderlo usabile

### Task 11.1: README
- [ ] Scrivere README.md completo
- [ ] Spiegare architettura sistema e folder-based deduplication
- [ ] **Documentare struttura cartelle Outlook (source/indexed/stubs/processed)**
- [ ] Guida installazione (requirements, setup Outlook)
- [ ] **Guida completamento stub manuale (Bloomberg Terminal workflow)**
- [ ] Esempi d'uso per ogni comando
- [ ] Troubleshooting comune
- [ ] Screenshots/esempi output

### Task 11.2: Code Documentation
- [ ] Docstrings per tutte le classi pubbliche
- [ ] Docstrings per tutte le funzioni pubbliche
- [ ] Type hints completi
- [ ] Commenti per logica complessa (stub matching, folder movement)

### Task 11.3: Configuration Template
- [ ] Creare `config.example.yaml` con tutte le opzioni
- [ ] Documentare ogni parametro
- [ ] **Documentare folder paths Outlook**
- [ ] Valori default sensati
- [ ] Esempi per casi d'uso comuni (breaking news: halflife=7, research: halflife=90)

---

## PRIORITÀ DI SVILUPPO

### MVP (Minimum Viable Product)
**Obiettivo:** Sistema funzionante end-to-end con folder-based deduplication

1. **Fase 1: Data Ingestion** (con folder movement)
   - Task 1.1-1.5: Extract, clean, metadata
   - **Implementare move_email() per spostare tra cartelle**
   
2. **Fase 2: Stub Management** (detection + movement base)
   - Task 2.1: Detect stub
   - Task 2.3: Move to /stubs/
   - Task 2.5: Report generation

3. **Fase 3: Embedding & Vector Store**
   - Task 3.1-3.3: Embedding e FAISS base
   
4. **Fase 4: Persistence** (base)
   - Task 4.1-4.2: Save/load indice e documenti

5. **Fase 5: Semantic Retrieval** (solo semantic search)
   - Task 5.1-5.2: Ricerca base
   
6. **Fase 8.1-8.2: Orchestration Pipeline** (base)
   - Ingestion pipeline con folder movement
   - Indexing pipeline base

7. **Fase 9.1: Sync Script**
   - Script sync base con folder management

### Production Ready
**Obiettivo:** Sistema robusto con stub auto-cleanup e metadati completi

8. **Fase 2: Stub Management** (matching completo)
   - Task 2.2: Stub registry
   - Task 2.4: Stub-complete matching e cleanup automatico
   
9. **Fase 1.4: Metadata Extraction** (Bloomberg Topics/People)
   - Estrazione sezioni People e Topics
   
10. **Fase 6: Temporal & Metadata Ranking**
    - Task 6.1-6.3: Recency + Bloomberg metadata filtering
    
11. **Fase 7: LLM Integration**
    - Task 7.1-7.3: Claude/GPT integration completa
    
12. **Fase 8.4: RAG Agent** completo
    - Search + LLM con metadati Bloomberg
    
13. **Fase 9: Tutti gli scripts**
    - Status, search, query, cleanup

14. **Fase 10: Main application** unificata
    - CLI completa con tutti i comandi

### Polish
**Obiettivo:** Sistema professionale

15. **Fase 11: Documentation** completa
    - README con workflow stub manual
    - Code documentation
    - Config templates

16. **Logging strutturato** in tutto il sistema

17. **Error handling robusto** ovunque

18. **Configuration management** avanzata

---

## NOTE TECNICHE

### Dipendenze Critiche
- `pywin32` - Outlook integration & folder movement
- `sentence-transformers` - Embeddings multilingual
- `faiss-cpu` - Vector search
- `beautifulsoup4` - HTML cleaning
- `anthropic` o `openai` - LLM
- `click` - CLI (opzionale)

### Decisioni Architetturali
- **Deduplication:** Folder-based (Outlook come database), no tracking files complessi
- **Stub cleanup:** Automatico via story_id matching, stub → /processed/
- **Embeddings:** Multilingual model per supportare query ITA/EN
- **Vector DB:** FAISS per semplicità, migrabile a Pinecone/Qdrant dopo
- **Persistence:** Pickle per documenti, JSON per stub_registry
- **LLM:** Provider-agnostic (supporta sia OpenAI che Anthropic)
- **Bloomberg Metadata:** Topics e People estratti da sezioni native Bloomberg

### Extensibility Points
- Aggiungere altri extractors (Gmail, RSS feeds)
- Supportare altri vector stores (Pinecone, Weaviate)
- Aggiungere re-ranking models (cross-encoders)
- Implementare caching LLM responses
- Aggiungere web UI (Streamlit/Gradio)
- Auto-cleanup /processed/ vecchi (archiving)

### Folder Management Best Practices
- Outlook folder paths configurabili
- Atomic move operations (COM)
- Rollback su errori (email torna in source)
- Periodic validation (check folders consistency)
- Backup strategy: backup Outlook include tutto lo stato