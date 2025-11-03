import os
import time
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from markitdown import MarkItDown
from modules.AssistantWithFilesys import AssistantWithFilesys

load_dotenv()

app = Flask(__name__)
markitdown = MarkItDown()
LETTA_BASE = "http://localhost:8283/"
agents = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/agent/create", methods=["POST"])
def create_agent():
    data = request.get_json(silent=True) or {}
    agent_name = data.get("agent_name")
    personality = data.get("personality", "helpful")
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

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    agent_id = request.form.get("agent_id")
    if not agent_id or agent_id not in agents:
        return jsonify({"error": "Missing or invalid agent_id"}), 400
    assistant = agents[agent_id]
    filename = file.filename or f"unnamed_{uuid.uuid4().hex[:6]}.txt"
    temp_path = os.path.join("/tmp", filename)
    file.save(temp_path)
    try:
        result = markitdown.convert(temp_path)
        markdown_text = result.text_content
    except Exception as e:
        return jsonify({"error": f"Error processing file: {e}"}), 500
    if not markdown_text:
        return jsonify({"error": "File has no readable text"}), 400
    try:
        summary = assistant.summarize(markdown_text)
    except Exception as e:
        return jsonify({"error": f"Summarization failed: {e}"}), 500
    date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    summary_text = f"API Upload Date: {date_str}\n\n{summary}"
    summary_path = os.path.join("/tmp", f"{filename}_summary.txt")
    markdown_path = os.path.join("/tmp", f"{filename}_markdown.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    file_id_summary = assistant.upload_file(summary_path, filename=f"{filename}_summary.txt")
    file_id_markdown = assistant.upload_file(markdown_path, filename=f"{filename}_markdown.txt")
    folder_id = assistant.get_folder_id()
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
