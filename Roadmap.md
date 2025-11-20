# BLOOMBERG RAG - ROADMAP

## WORKFLOW DEL SISTEMA

### Overview
Il sistema estrae email Bloomberg da Outlook, le processa per creare un database vettoriale ricercabile, e permette di interrogare le email tramite un agente RAG (basato su Google ADK) che combina ricerca semantica e generazione LLM. La deduplication e' gestita tramite cartelle Outlook: email processate vengono spostate automaticamente in sottocartelle dedicate.

### Struttura Cartelle Outlook
```
Inbox/
  Bloomberg subs/              <- SOURCE (email da processare)
    |- indexed/                <- Email complete processate e indicizzate
    |- stubs/                  <- Stub in attesa di completamento manuale
    |- processed/              <- Stub completati (archivio)
```

### Flusso Completo
```
+---------------------------------------------------------------+
|                    FASE 1: DATA INGESTION                     |
+---------------------------------------------------------------+
                              |
    Outlook Source Folder -> Extract Raw Emails
                              |
              +---------------+---------------+
              |                               |
         E' STUB?                         E' COMPLETE?
              |                               |
    Estrai Story ID                    Estrai Story ID
    Crea Fingerprint                   Clean Content
    Registra in stub_registry          Extract Metadata
              |                               |
    Sposta in /stubs/                  Check stub match
    Genera Report                             |
              |                         +-----+-----+
        [Attesa]                        |           |
              |                    Match stub?  No match
     [Manual Terminal]                  |           |
              |                    Sposta stub  Processa
         Complete                  in /processed    |
         arriva                          |      Generate
              +--------------------------+->    Embedding
                                                     |
                                         Sposta in /indexed/

+---------------------------------------------------------------+
|                    FASE 2: EMBEDDING & INDEXING               |
+---------------------------------------------------------------+
                              |
         Email in /indexed/ -> Generate Embeddings
                              |
              Store in Vector Database (FAISS)
                              |
                Save Index + Metadata to Disk

+---------------------------------------------------------------+
|                    FASE 3: RETRIEVAL                          |
+---------------------------------------------------------------+
                              |
              User Query -> Generate Query Embedding
                              |
                    Semantic Search (top-K)
                              |
              Apply Temporal Scoring (recency boost)
                              |
         Apply Metadata Filtering (topics, people, date, ticker)
                              |
                    Hybrid Ranking & Re-ranking
                              |
                    Top-N Relevant Documents

+---------------------------------------------------------------+
|                    FASE 4: GENERATION (Google ADK Agent)      |
+---------------------------------------------------------------+
                              |
           Build Context from Retrieved Documents
                              |
              Agent Tools Call (hybrid_search, filters)
                              |
              Send to Google ADK Agent (OpenAI via LiteLLM)
                              |
              Stream Response to User
```

### Deduplication Strategy

**Principio:** Outlook stesso e' il "database" di stato. Ogni email esiste in una sola cartella alla volta.

**Regole:**
- Email in `/Bloomberg subs/` (source) -> DA PROCESSARE
- Email in `/Bloomberg subs/indexed/` -> GIA' PROCESSATA (skip durante sync)
- Email in `/Bloomberg subs/stubs/` -> STUB IN ATTESA (skip durante sync)
- Email in `/Bloomberg subs/processed/` -> STUB COMPLETATO (archivio, skip)

**Vantaggi:**
- Zero file di tracking complessi
- Visualmente chiaro in Outlook
- Reversibile (sposta email indietro per riprocessare)
- Outlook backup include tutto lo stato


### Bloomberg Email Structure

**STUB EMAIL (Incomplete):**
```
Link
Alert: xxxx
Source: XXXXXXX
Tickers (optional)
People (optional)
Topics (optional)
```

**Caratteristiche Stub:**
- **SEMPRE presenti:** `Alert:` e `Source:` (markers obbligatori)
- **Opzionalmente presenti:** `Link`, `Tickers`, `People`, `Topics`
- Contenuto molto breve (< 500 caratteri)
- Contiene URL Bloomberg: `bloomberg.com/news/articles/[STORY_ID]`
- NO contenuto articolo, solo metadati e link

**COMPLETE EMAIL:**
```
[Full article content - substantial text]
[Multiple paragraphs with actual news content]
...
Tickers (optional)
People (optional)
Topics (optional)
```

**Caratteristiche Complete:**
- Contenuto sostanziale PRIMA delle sezioni metadata (> 500 caratteri)
- Sezioni `Tickers`, `People`, `Topics` appaiono ALLA FINE (opzionali)
- NO markers `Alert:` e `Source:`
- Contiene articolo completo leggibile

**Stub Detection Logic:**
1. Check presenza `Alert:` AND `Source:` (se entrambi presenti -> STUB)
2. Check lunghezza contenuto (< 500 char -> probabile STUB)
3. Check presenza URL Bloomberg senza contenuto sostanziale prima
4. Estrai Story ID da URL per matching futuro

**Complete Processing:**
1. Check assenza `Alert:` e `Source:`
2. Estrai contenuto PRIMA delle sezioni `Tickers`/`People`/`Topics`
3. Estrai metadata dalle sezioni finali (opzionali)
4. Check matching con stub esistenti (via Story ID o fingerprint)
5. Se match -> sposta stub in `/processed/`, processa complete

### Data Flow

**Email -> Processed Document:**
- Raw email text + metadata
- Cleaned content (no HTML, disclaimers)
- Extracted Bloomberg metadata (topics, people, author, date)
- Stub status determination (complete/stub)
- Outlook EntryID (ID univoco)
- Bloomberg Story ID (per matching)

**Document -> Vector:**
- Full text embedding (384-dim vector)
- Stored with document ID and metadata

**Stub -> Complete Matching:**
- Story ID match (primario)
- Fingerprint match (fallback: subject + date)
- Stub originale -> /processed/ quando complete arriva

**Query -> Response:**
- Query embedding -> Semantic search
- Retrieved documents -> Temporal + metadata scoring
- Top documents + metadata -> LLM prompt
- LLM generation -> Final response

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
- [ ] Implementare sorting per data (piu' recenti prima)
- [ ] Limitare numero email estratte (per testing)

### Task 1.3: Content Cleaner
- [ ] Rimuovere disclaimer email ("External Email...")
- [ ] Convertire HTML in testo pulito (BeautifulSoup)
- [ ] Correggere encoding issues
- [ ] Rimuovere link footer Bloomberg
- [ ] Normalizzare whitespace
- [ ] Separare header da contenuto principale

### Task 1.4: Metadata Extractor
- [ ] Estrarre categoria Bloomberg dall'oggetto (BFW, BI, BBF)
- [ ] Estrarre data articolo (priorita' su data ricezione email)
- [ ] Estrarre autore dal corpo ("By [Name]")
- [ ] **Estrarre Bloomberg Story ID da URL nel body**
- [ ] **Estrarre sezione "People" da fine email (OPZIONALE, appare dopo contenuto)**
- [ ] **Estrarre sezione "Topics" da fine email (OPZIONALE, appare dopo contenuto)**
- [ ] **Estrarre sezione "Tickers" se presente (OPZIONALE)**
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
- [ ] **Check REQUIRED markers:** presenza `Alert:` AND `Source:` (se entrambi -> STUB)
- [ ] **Check content length:** < 500 caratteri -> probabile stub
- [ ] Check presenza URL Bloomberg: `bloomberg.com/news/articles/[STORY_ID]`
- [ ] Verificare assenza di contenuto sostanziale prima dei metadata markers
- [ ] Estrarre Story ID da URL Bloomberg
- [ ] Classificare email come "complete" o "stub"
- [ ] Per complete: verificare presenza contenuto PRIMA di Tickers/People/Topics

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
- [ ] Aggiornare registry: status "pending" -> "completed"
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
- [x] Inizializzare sentence-transformers model (multilingual)
- [x] Implementare batch encoding per efficienza
- [x] Generare embeddings per lista documenti
- [x] Gestire documenti singoli
- [x] Normalizzare vettori output (float32)

### Task 3.2: Vector Store
- [x] Implementare wrapper per FAISS IndexFlatL2
- [x] Aggiungere vettori all'indice con metadati
- [x] Implementare ricerca k-nearest neighbors
- [x] Mappare ID vettore -> metadati documento (include Outlook EntryID)
- [x] Gestire indice vuoto e crescita incrementale

### Task 3.3: Indexing Pipeline
- [x] Coordinare: documenti -> embeddings -> vector store
- [x] **Processare solo email in source folder (skip indexed/stubs/processed)**
- [x] Gestire batch processing per grandi volumi
- [x] Mostrare progress durante indicizzazione
- [x] Validare dimensioni e integrita' indice
- [x] **Dopo embedding success: spostare email in /indexed/**

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

## FASE 6: TEMPORAL & METADATA RANKING (SEMPLIFICATA)

**Obiettivo:** Aggiungere recency scoring e filtri essenziali ai risultati semantici

### Task 6.1: Temporal Scorer
- [ ] Implementare classe `TemporalScorer` in `src/retrieval/temporal_scorer.py`
- [ ] Metodo `calculate_recency_score(article_date)` - exponential decay basato su data
- [ ] Configurare halflife (giorni per dimezzamento score, es: 30 giorni)
- [ ] Gestire documenti senza data (score default = 0.5)
- [ ] Normalizzare output 0-1

### Task 6.2: Metadata Filter (Solo Essenziali)
- [ ] Implementare classe `MetadataFilter` in `src/retrieval/metadata_filter.py`
- [ ] **Filtro 1: Date Range** - `filter_by_date_range(start_date, end_date)` - filtra per range date
- [ ] **Filtro 2: Topics** - `filter_by_topics(topics_list)` - match any topic
- [ ] **Filtro 3: People** - `filter_by_people(people_list)` - match any person (opzionale)
- [ ] Ritorna indici documenti che matchano i filtri
- [ ] Supporta filtri combinati (AND logic)

### Task 6.3: Hybrid Retriever (Semplificato)
- [ ] Implementare classe `HybridRetriever` in `src/retrieval/hybrid_retriever.py`
- [ ] Metodo `search(query, top_k, filters, recency_weight)`:
  - Semantic search -> top-K risultati
  - Applica metadata filters (se specificati)
  - Calcola recency score per ogni risultato
  - Combine score = (semantic * (1-w)) + (recency * w) dove w=recency_weight (default 0.3)
  - Riordina per score combinato
  - Ritorna top-N finali
- [ ] Configurazione semplice: recency_weight (0.0-1.0, default 0.3)
- [ ] Ritorna risultati con metadati: (doc, semantic_score, recency_score, combined_score)

---


---

## FASE 7: GOOGLE ADK TOOL ADAPTERS

**Obiettivo:** Creare tool definitions per esporre il HybridRetriever come tools per Google ADK Agent

**NOTA ARCHITETTURALE:** Non creiamo un LLM client custom, ma definiamo Python functions che Google ADK può chiamare automaticamente tramite tool/function calling.

### Task 7.1: Tool Definitions
- [ ] Creare `tools/hybrid_search.py` - ricerca completa (semantic + temporal + filters)
- [ ] Creare `tools/semantic_search.py` - ricerca semantica base
- [ ] Creare `tools/filter_by_date.py` - filtra per date range
- [ ] Creare `tools/filter_by_topic.py` - filtra per Bloomberg topics
- [ ] Creare `tools/filter_by_people.py` - filtra per persone menzionate
- [ ] Creare `tools/filter_by_ticker.py` - filtra per Bloomberg tickers
- [ ] Ogni tool è una Python function con docstring dettagliata (Google ADK usa docstring per capire quando chiamare il tool)
- [ ] Ogni tool accetta parametri tipizzati (type hints obbligatori)
- [ ] Ogni tool ritorna dizionario strutturato con risultati + metadati Bloomberg

### Task 7.2: Retrieval Wrapper
- [ ] Creare classe `RetrievalToolkit` in `tools/__init__.py`
- [ ] Load vector store e retriever all'inizializzazione
- [ ] Fornire metodi helper per tool functions
- [ ] Gestire caching risultati (opzionale)
- [ ] Error handling per tool failures

### Task 7.3: Tool Response Formatting
- [ ] Formattare output tools per Google ADK
- [ ] Includere sempre: risultati, metadati Bloomberg (date, author, topics, people, tickers)
- [ ] Struttura consistente tra tutti i tools
- [ ] Gestire risultati vuoti ("no articles found")
- [ ] Truncate se troppi risultati (max 10 articoli per chiamata)

---

## FASE 8: ORCHESTRATION

**Obiettivo:** Coordinare tutti i componenti in pipeline funzionanti

### Task 8.1: Ingestion Pipeline
- [ ] **Coordinare: extract da source -> detect stub -> move to stubs OR (clean -> metadata -> check stub match -> move stub to processed -> embed -> move to indexed)**
- [ ] **Implementare logica decisionale: stub vs complete**
- [ ] **Per email complete: check match con stub esistenti (via story_id o fingerprint)**
- [ ] **Se match: spostare stub da /stubs/ a /processed/ prima di processare**
- [ ] Gestire errori in singole email senza bloccare tutto
- [ ] Logging progresso e statistiche
- [ ] **Report finale: N complete->indexed, N stub->stubs, N stub completed->processed**

### Task 8.2: Indexing Pipeline
- [ ] Coordinare: documenti complete -> embeddings -> vector store
- [ ] **Processare solo email in source folder (automatic dedup via folder structure)**
- [ ] Gestire indicizzazione incrementale
- [ ] Salvare stato dopo indicizzazione

### Task 8.3: Search Pipeline
- [ ] Coordinare: query -> semantic search -> temporal ranking -> metadata filtering
- [ ] Applicare configurazione weights e filters
- [ ] Ritornare risultati formattati con metadati Bloomberg

---

## FASE 9: SCRIPTS & AUTOMATION

**Obiettivo:** Creare script standalone per operazioni comuni

### Task 9.1: Sync Script
- [ ] Script `sync_emails.py` per sincronizzazione completa
- [ ] **Scannare solo source folder (Inbox/Bloomberg subs)**
- [ ] **Skip automatico di /indexed/, /stubs/, /processed/**
- [ ] Processare email nuove
- [ ] **Identificare stub -> spostare in /stubs/**
- [ ] **Identificare complete -> check stub match -> se match: stub to /processed/**
- [ ] **Indicizzare email complete -> spostare in /indexed/**
- [ ] Generare report stub (ancora in /stubs/)
- [ ] **Mostrare statistiche: N->indexed, N->stubs, N stub completed**

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
- [ ] Supportare filtering per topics/people/date/ticker

### Task 9.4: Cleanup Script
- [ ] Script `cleanup.py` per manutenzione
- [ ] Opzione: cancellare stub in /stubs/ piu' vecchi di N giorni
- [ ] Opzione: archiviare /processed/ piu' vecchi di N mesi
- [ ] Opzione: ricostruire stub_registry da scan cartelle

---

## FASE 10: MAIN APPLICATION

**Obiettivo:** Entry point unificato per operazioni di sync e manutenzione

### Task 10.1: CLI Interface
- [ ] Implementare `main.py` con argparse o click
- [ ] Comando: `sync` - sincronizza email (source -> indexed/stubs/processed)
- [ ] Comando: `status` - mostra statistiche sistema e cartelle
- [ ] Comando: `search <query>` - ricerca interattiva (no LLM)
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
- [ ] Guida installazione (requirements, setup Outlook, Google ADK)
- [ ] **Guida completamento stub manuale (Bloomberg Terminal workflow)**
- [ ] Esempi d'uso per ogni comando
- [ ] **Spiegare come usare agent.py con Google ADK**
- [ ] Troubleshooting comune
- [ ] Screenshots/esempi output

### Task 11.2: Code Documentation
- [ ] Docstrings per tutte le classi pubbliche
- [ ] Docstrings per tutte le funzioni pubbliche (CRITICHE per Google ADK tools!)
- [ ] Type hints completi
- [ ] Commenti per logica complessa (stub matching, folder movement)

### Task 11.3: Configuration Template
- [ ] Creare `config.example.yaml` con tutte le opzioni
- [ ] Documentare ogni parametro
- [ ] **Documentare folder paths Outlook**
- [ ] **Documentare Google ADK settings (model, API key)**
- [ ] Valori default sensati
- [ ] Esempi per casi d'uso comuni (breaking news: halflife=7, research: halflife=90)

---

## PRIORITA' DI SVILUPPO

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
**Obiettivo:** Sistema robusto con stub auto-cleanup, metadati completi, e agent Google ADK funzionante

8. **Fase 2: Stub Management** (matching completo)
   - Task 2.2: Stub registry
   - Task 2.4: Stub-complete matching e cleanup automatico
   
9. **Fase 1.4: Metadata Extraction** (Bloomberg Topics/People/Tickers)
   - Estrazione sezioni People, Topics, Tickers
   
10. **Fase 6: Temporal & Metadata Ranking**
    - Task 6.1-6.3: Recency + Bloomberg metadata filtering
    
11. **Fase 7: Google ADK Tool Adapters**
    - Task 7.1-7.3: Tool definitions per retrieval
    
12. **Fase 12: Google ADK Agent**
    - Task 12.1-12.3: Agent completo con OpenAI
    
13. **Fase 9: Tutti gli scripts**
    - Status, search, cleanup

14. **Fase 10: Main application** unificata
    - CLI completa con tutti i comandi

### Polish
**Obiettivo:** Sistema professionale

15. **Fase 11: Documentation** completa
    - README con workflow stub manual
    - Code documentation (CRITICA per Google ADK tools)
    - Config templates

16. **Logging strutturato** in tutto il sistema

17. **Error handling robusto** ovunque

18. **Configuration management** avanzata

---

## FASE 12: GOOGLE ADK AGENT

**Obiettivo:** Creare agente conversazionale usando Google ADK framework con OpenAI via LiteLLM

**NOTA ARCHITETTURALE:** L'agente NON si occupa di ingestion/embedding (gestito da script manuali), ma SOLO di retrieval e conversazione usando Google ADK framework.

### Task 12.1: Agent Core Setup
- [ ] Creare `agent.py` - main Google ADK Agent
- [ ] Inizializzare `LlmAgent` di Google ADK
- [ ] Configurare LiteLLM wrapper per OpenAI (`model=LiteLlm(model="openai/gpt-4o")`)
- [ ] Caricare vector store all'avvio
- [ ] Registrare tutti i tools (hybrid_search, semantic_search, filters)
- [ ] Configurare session service (InMemorySessionService o persistent)
- [ ] Setup Runner per esecuzione agent
- [ ] Error handling e recovery

### Task 12.2: Agent Prompt & Instructions
- [ ] Creare `agent_prompt.py` - system instructions per agent
- [ ] Definire ruolo: "You are a Bloomberg email research assistant"
- [ ] Istruzioni tool calling: quando usare quale tool
- [ ] Guidelines per citazioni (sempre includere data, autore, topics)
- [ ] Guidelines per handling "no results found"
- [ ] Guidelines per follow-up questions
- [ ] Tone e stile (professionale, conciso, data-driven)

### Task 12.3: Agent Execution Loop
- [ ] Implementare async execution loop
- [ ] Gestire streaming response (event-based)
- [ ] Handle tool calls automatici (Google ADK lo fa)
- [ ] Capture final response
- [ ] Logging di tool calls e risultati
- [ ] Session management (user_id, session_id)
- [ ] Graceful shutdown

### Task 12.4: Interactive Interface
- [ ] Interfaccia CLI per interaction con agent
- [ ] Welcome message e istruzioni
- [ ] Command handling (/exit, /clear, /help, /status)
- [ ] Display formattato di risposte (con citazioni)
- [ ] Display di tool calls eseguiti (per debugging)
- [ ] Conversation history display
- [ ] Graceful exit

### Task 12.5: Agent Configuration
- [ ] Aggiungere `AgentConfig` in `config/settings.py`
- [ ] Model selection (OpenAI model via LiteLLM)
- [ ] API key management (OPENAI_API_KEY)
- [ ] Session settings (memory, context window)
- [ ] Tool settings (quali tools abilitare)
- [ ] Response settings (max_length, temperature)
- [ ] Prompt templates customization

---

## NOTE TECNICHE

### Dipendenze Critiche
- `pywin32` - Outlook integration & folder movement
- `sentence-transformers` - Embeddings multilingual
- `faiss-cpu` - Vector search
- `beautifulsoup4` - HTML cleaning
- **`google-adk`** - Google Agent Development Kit framework
- **`litellm`** - LLM provider abstraction (per usare OpenAI in Google ADK)
- **`openai`** - OpenAI API client
- `click` - CLI (opzionale)

### Decisioni Architetturali
- **Deduplication:** Folder-based (Outlook come database), no tracking files complessi
- **Stub cleanup:** Automatico via story_id matching, stub -> /processed/
- **Embeddings:** Model inglese-only per performance (all-mpnet-base-v2)
- **Vector DB:** FAISS per semplicita', migrabile a Pinecone/Qdrant dopo
- **Persistence:** Pickle per documenti, JSON per stub_registry
- **LLM Framework:** Google ADK con OpenAI via LiteLLM
- **Tool Architecture:** Python functions con docstrings dettagliate (Google ADK usa docstring)
- **Bloomberg Metadata:** Topics, People, Tickers estratti da sezioni native Bloomberg
- **Agent Architecture:** Google ADK agent + custom retrieval tools. Separazione netta tra ingestion (script manuali) e retrieval/chat (agente)

### Extensibility Points
- Aggiungere altri extractors (Gmail, RSS feeds)
- Supportare altri vector stores (Pinecone, Weaviate)
- Aggiungere re-ranking models (cross-encoders)
- Aggiungere piu' tools (sentiment analysis, summarization, compare articles)
- Multi-LLM support (Gemini, Claude, altri modelli via LiteLLM)
- Web UI (Streamlit/Gradio)
- Auto-cleanup /processed/ vecchi (archiving)
- Deploy agent su Vertex AI Agent Engine (Google Cloud)

### Folder Management Best Practices
- Outlook folder paths configurabili
- Atomic move operations (COM)
- Rollback su errori (email torna in source)
- Periodic validation (check folders consistency)
- Backup strategy: backup Outlook include tutto lo stato

### Google ADK Best Practices
- **Tool docstrings sono CRITICI** - Google ADK usa docstring per decidere quando chiamare il tool
- Type hints obbligatori per tool parameters
- Tool responses strutturati (dizionari con keys consistenti)
- Context window management (OpenAI ha limiti token)
- Safety settings configurate per contesto Bloomberg
- Streaming abilitato per risposte lunghe
- Error handling graceful per tool failures
- Session persistence per conversation memory