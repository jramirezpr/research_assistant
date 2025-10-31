import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, render_template_string
from markitdown import MarkItDown
from flask import jsonify, request

from langchain.chat_models import init_chat_model
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from modules.AssistantWithFilesys import AssistantWithFilesys

assistant = AssistantWithFilesys(
    agent_name="re_v2",
    folder_name="upload_v2",
    base_url="http://letta_server:8283/",
    personality="helpful"
)

load_dotenv()
app = Flask(__name__)
markitdown = MarkItDown()







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
    file_path = file.filename
    file.save(file_path)

    try:
        result = markitdown.convert(file_path)
        markdown_text = result.text_content.strip()
    except Exception as e:
        return f"Error processing file: {e}", 500

    if not markdown_text:
        return "File has no text that can be processed as markdown.", 400

    try:
        summary = asyncio.run(map_reduce_summarize(markdown_text))
    except Exception as e:
        summary = f"Summary failed: {e}"

    try:
        assistant.upload_file(file_path)
    except Exception as e:
        print(f"[Upload] Failed to queue upload: {e}")

    return render_template("result.html", markdown_text=markdown_text, summary=summary)


@app.route("/api/chat", methods=["POST"])
def chat_with_agent():
    """
    Send a user message to the Letta agent and return the assistant's reply
    along with the recent conversation.
    """
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    print(f"[Chat] User: {user_message}")

    chat_data = assistant.chat(user_message)

    print(f"[Chat] Agent: {chat_data.get('reply')}")
    return jsonify(chat_data)


if __name__ == "__main__":
    app.run(debug=True)
