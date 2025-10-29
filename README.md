# Local Research assistant

This project provides a **local research knowledge pipeline** that:

Uploads documents documents  
- Converts them to Markdown using **MarkItDown**  
- Performs **map-reduce summarization** for large files  
- Splits documents into **vector-embedded chunks** (RAG-ready)  
- Stores both chunks + summary in a **self-hosted Letta server**  

You can later query / chat over all stored knowledge using Letta.



##  Initialization

```bash
docker compose up --build
```

This launches:

| Service | Purpose |
|--------|---------|
| `letta_db` | pgvector database for storing the documents. We connect it with Letta |
| `letta_server` | Letta knowledge server + LLM routing |
| `endpoint_upload_docu` | The document ingestion + summarization Flask app |
| `letta_nginx` | Optional reverse proxy for Letta UI |

Once running:
- Visit the document upload app at `http://localhost:5000`
- Letta endpoint is available at  `http://localhost:8283`


Here is an example of a summarized blog post:

![Summarized text](images/example_summary.png "summary")

To connect your local server to the ADE (if you have a letta account):
go into Account, click on Projects, then click on Connect to a server, and add the url http://localhost:8283 with whatever name for your sever you might like. If your server is running you should see it listed on the self-hosted tab, and you can click on it to monitor your local agents in the Dashboard.

![Summarized text](images/letta_ADE_local_server.png"
"self-hosted server")

---

##  How It Works


1. User uploads a `.pdf` or `.docx`
2. `MarkItDown` converts the file → Markdown text
3. We **split large documents** into multiple chunks  
   (documents might be larger than 80000 token chunk limit)
4. We run **async map-reduce summarization**:
   - MAP: Summarize each chunk independently → partial summaries
   - REDUCE: Summarize the summaries → final result
5. The Markdown + chunk summaries are uploaded to **Letta Filesystem**:
   -  Stored chunk-by-chunk
   -  Automatically embedded for vector search (RAG-ready)




---

## Flow graph

```
[PDF/DOCX Upload]
        |
        v
[Flask Ingestion App]
        |
        | MarkItDown
        v
[Markdown Text] ----> [Chunking + Embedding] ---> Letta FS (RAG-ready)
        |
        | Async Map-Reduce LLM Summarization
        v
[Final Summary] --------------------------------> Letta FS
```
---

## Requirements

- Docker + Docker Compose installed
- an `.env` file at the root (see .envexample):
- an  `.env` inside /endpoint_upload_doc containing:
```
OPENAI_API_KEY=your_key_here
```

---



## Repository Layout

```
/
├── docker-compose.yml
├── endpoint_upload_doc/
│   ├── app.py  ← Main ingestion + summarization logic
│   └── Dockerfile
├── .persist/postgres_data/  ← Letta DB storage
├── nginx.conf
├──  images ← Used in the readme, ignore this
└── README.md
```

---

