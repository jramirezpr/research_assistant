import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, render_template_string
from markitdown import MarkItDown

from langchain.chat_models import init_chat_model
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from letta_client import Letta

load_dotenv()

app = Flask(__name__)
markitdown = MarkItDown()

# Connect to self-hosted Letta
client = Letta(base_url="http://letta_server:8283")
AGENT_NAME = "wild_researcher"
executor = ThreadPoolExecutor(max_workers=3)


def ensure_agent_exists(ag_name=AGENT_NAME):
    agents = client.agents.list(name=ag_name)
    if agents:
        print("agent already existed, retrieving")
        created_agent = agents[0]
    else:
        # Create if missing
        print(f"[Letta] Creating agent: {AGENT_NAME}")
        created_agent = client.agents.create(
            name=AGENT_NAME,
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-3-small",
            memory_blocks=[
                {"label": "human", "limit": 2000,
                "value": "Name: John. Occupation: Researcher."},
                {"label": "persona", "limit": 2000,
                "value": "I am a helpful assistant geared towards research."}
            ],
            tools=["web_search"]
        )
    agent_id = created_agent.id
    return created_agent, agent_id


def background_upload(folder_id, file_path):
    try:
        print(f"[Upload] Starting upload for: {file_path}")
        with open(file_path, "rb") as f:
            job = client.folders.files.upload(folder_id=folder_id, file=f)

        # Optional: Wait for job to complete, but now in background
        while True:
            job_info = client.jobs.retrieve(job.id)
            if job_info.status == "completed":
                print(f"[Upload] Completed: {file_path}")
                break
            elif job_info.status == "failed":
                print(f"[Upload] Failed: {file_path} – {job_info.metadata}")
                break
            time.sleep(1)

    except Exception as e:
        print(f"[Upload] Exception while uploading {file_path}: {e}")

created_agent, agent_id = ensure_agent_exists()

# get an available embedding_config
embedding_configs = client.models.embeddings.list()
# this uses letta-free. text-embedding-3-small also available.
embedding_config = embedding_configs[-2]
print(embedding_config)

# create the folder
folders = client.folders.list(name="uploaded_r_doc")
if not folders:
    print("folder not found, creating")
    folder = client.folders.create(
        name="uploaded_r_doc",
        embedding_config=embedding_config
        )
else:
    print("folder found")
    folder = folders[0]


# Configure LLM
llm = init_chat_model("gpt-4o-mini", model_provider="openai")

# Map and reduce Prompts
map_prompt = ChatPromptTemplate.from_messages(
    [("system", "Write a concise summary of the following:\n\n{context}")]
)
reduce_prompt = ChatPromptTemplate.from_messages(
    [("system",
      "The following are summary fragments:\n\n{summaries}\n\n"
      "Condense into one high-quality final summary.")]
)

# Chunk for summarization AND embedding
text_splitter = CharacterTextSplitter(chunk_size=80000, chunk_overlap=500)


async def map_reduce_summarize(markdown_text: str) -> str:
    docs = text_splitter.split_text(markdown_text)
    docs = [Document(page_content=d) for d in docs]

    async def summarize_doc(doc):
        prompt = map_prompt.invoke({"context": doc.page_content})
        response = await llm.ainvoke(prompt)
        return response.content

    # MAP PHASE: apply summarize_doc
    summaries = await asyncio.gather(*(summarize_doc(doc) for doc in docs))

    # REDUCE PHASE: final summary 
    reduce_input = {"summaries": "\n".join(summaries)}
    final_prompt = reduce_prompt.invoke(reduce_input)
    final_response = await llm.ainvoke(final_prompt)

    return final_response.content


@app.route("/")
def index():
    return render_template_string("""
        <h1>Upload a PDF or Word Document</h1>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf,.docx" required>
            <button type="submit">Upload + Summarize</button>
        </form>
    """)


@app.route("/", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]
    filename = file.filename
    file.save(filename)

    try:
        result = markitdown.convert(filename)
        markdown_text = result.text_content
    except Exception as e:
        return f"Markdown conversion error: {e}", 500
    if not markdown_text:
        return  "file has no text that can be processed as markdown"

    try:
        summary = asyncio.run(map_reduce_summarize(markdown_text))
        summarization_succeeded = True
    except Exception as e:
        summary = f"Summary failed: {e}"
        summarization_succeeded = False

    # Save to Letta (only if summary is good)
    #executor.submit(background_upload, folder.id, filename)

    letta_status = "Not uploaded"
    if summarization_succeeded:
        print(summarization_succeeded)
       

    return render_template_string("""
        <h1>Summary </h1>
        <pre style="white-space: pre-wrap;">{{ summary }}</pre>
        <h1>Markdown</h1>
        <pre style="white-space: pre-wrap; background:#eef;">{{ markdown }}</pre>
        <h2>Letta Upload Status</h2>
        <p>{{ letta }}</p>
        <br><a href="/">← Upload another file</a>
    """, markdown=markdown_text, summary=summary, letta=letta_status)


if __name__ == "__main__":
    app.run(debug=True)
