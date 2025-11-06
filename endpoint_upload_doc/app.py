import asyncio

import os
import time
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from dotenv import load_dotenv
from markitdown import MarkItDown
from modules.AssistantWithFilesys import AssistantWithFilesys
from langchain.chat_models import init_chat_model
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()



# Local LLM for summarization
llm = init_chat_model("gpt-4o-mini", model_provider="openai")

map_prompt = ChatPromptTemplate.from_messages(
    [("system", "Write a concise summary of the following:\n\n{context}")]
)

reduce_prompt = ChatPromptTemplate.from_messages(
    [("system",
      "The following are summary fragments:\n\n{summaries}\n\n"
      "Condense into one high-quality final summary.")]
)

text_splitter = CharacterTextSplitter(chunk_size=80000, chunk_overlap=500)

async def map_reduce_summarize(markdown_text: str) -> str:
    docs = text_splitter.split_text(markdown_text)
    docs = [Document(page_content=d) for d in docs]

    async def summarize_doc(doc):
        prompt = map_prompt.invoke({"context": doc.page_content})
        response = await llm.ainvoke(prompt)
        return response.content

    summaries = await asyncio.gather(*(summarize_doc(doc) for doc in docs))

    reduce_input = {"summaries": "\n".join(summaries)}
    final_prompt = reduce_prompt.invoke(reduce_input)
    final_response = await llm.ainvoke(final_prompt)

    return final_response.content



app = Flask(__name__)
CORS(app)

markitdown = MarkItDown()
LETTA_BASE = "http://letta_server:8283/"
agents = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/agent/create", methods=["POST"])
def create_agent():
    data = request.get_json(silent=True) or {}
    agent_name = data.get("agent_name")
    personality = data.get("personality", "helpful")
    print(f"creating agent {agent_name}")
    if not agent_name:
        agent_name = f"no_name_{uuid.uuid4().hex[:8]}"
    folder_name = f"{agent_name}_research_folder"
    try:
        assistant = AssistantWithFilesys(
            agent_name=agent_name,
            folder_name=folder_name,
            base_url=LETTA_BASE,
            personality=personality
        )
        agent_id = assistant.get_agent_id()
        folder_id = assistant.get_folder_id()
        agents[agent_id] = assistant
        return jsonify({
            "message": "Agent created successfully",
            "agent_name": agent_name,
            "agent_id": agent_id,
            "folder_id": folder_id,
            "personality": personality
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agent/list", methods=["GET"])
def list_agents():
    if not agents:
        return jsonify({"agents": []}), 200
    agent_data = []
    for agent_id, assistant in agents.items():
        agent_data.append({
            "agent_id": agent_id,
            "agent_name": assistant.agent_name,
            "folder_id": assistant.get_folder_id(),
            "personality": assistant.personality
        })
    return jsonify({"agents": agent_data}), 200

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    agent_id = request.form.get("agent_id")

    if not agent_id or agent_id not in agents:
        return jsonify({"error": "Missing or invalid agent_id"}), 400

    assistant = agents[agent_id]

    # Save temp file
    filename = file.filename or f"unnamed_{uuid.uuid4().hex[:6]}"
    temp_path = os.path.join("/tmp", filename)
    file.save(temp_path)

    # Extract Markdown
    try:
        result = markitdown.convert(temp_path)
        markdown_text = result.text_content
    except Exception as e:
        return jsonify({"error": f"Error processing file: {e}"}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    if not markdown_text:
        return jsonify({"error": "File has no readable text"}), 400

    # Summarize via LangChain map-reduce
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        summary = loop.run_until_complete(map_reduce_summarize(markdown_text))
    except Exception as e:
        return jsonify({"error": f"Summarization failed: {e}"}), 500

    # File names
    base_name = os.path.splitext(filename)[0]
    main_filename = f"{base_name}.md"
    summary_filename = f"{base_name}_summary.md"

    # Build summary with metadata header
    summary_with_header = (
        f"---\n"
        f"type: summary\n"
        f"source: {filename}\n"
        f"api_upload_date: {datetime.utcnow().isoformat()}Z\n"
        f"---\n\n"
        f"{summary}"
    )
    print("**** main filename is:",main_filename)

    # Upload to Letta
    try:
        main_file_info = assistant.upload_text_as_file(markdown_text, filename=main_filename)
        summary_file_info = assistant.upload_text_as_file(summary_with_header, filename=summary_filename)

        file_id_markdown = main_file_info["file_id"]
        file_id_summary = summary_file_info["file_id"]
        folder_id = assistant.get_folder_id()
    except Exception as e:
        return jsonify({"error": f"Upload to Letta failed: {e}"}), 500

    # Response
    return jsonify({
        "summary": summary,
        "markdown_text": markdown_text,
        "file_id_summary": file_id_summary,
        "file_id_markdown": file_id_markdown,
        "folder_id": folder_id,
        "agent_id": agent_id
    }), 200


@app.route("/api/upload/status", methods=["GET"])
def check_upload_status():
    folder_id = request.args.get("folder_id")
    file_id = request.args.get("file_id")
    agent_id = request.args.get("agent_id")
    if not folder_id or not file_id or not agent_id:
        return jsonify({"error": "Missing folder_id, file_id, or agent_id"}), 400
    if agent_id not in agents:
        return jsonify({"error": "Unknown agent_id"}), 404
    assistant = agents[agent_id]
    try:
        files = assistant.client.folders.files.list(
            folder_id=folder_id,
            order="desc",
            limit=10
        )
        for f in files:
            if f.id == file_id:
                return jsonify({
                    "file_id": file_id,
                    "status": f.processing_status
                }), 200
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/chat", methods=["POST"])
def chat_with_agent():
    data = request.get_json(silent=True)
    if not data or "message" not in data or "agent_id" not in data:
        return jsonify({"error": "Missing 'message' or 'agent_id'"}), 400
    agent_id = data["agent_id"]
    if agent_id not in agents:
        return jsonify({"error": "Unknown agent_id"}), 404
    assistant = agents[agent_id]
    user_message = data["message"].strip()
    try:
        chat_data = assistant.chat(user_message)
        return jsonify(chat_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
