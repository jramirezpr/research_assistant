"use client";

import { useState } from "react";
import {
  uploadFile,
  checkUploadStatus,
  sendChatMessage,
  createAgent,
} from "@/lib/api";

export default function HomePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [summary, setSummary] = useState("");
  const [markdown, setMarkdown] = useState("");
  const [chatMessage, setChatMessage] = useState("");
  const [chatLog, setChatLog] = useState<string[]>([]);
  const [agentId, setAgentId] = useState<string | null>(null);
  const [personality, setPersonality] = useState("helpful");

  // Utility to select correct color scheme
  const personalityColor = () => {
    switch (personality) {
      case "formal":
        return "formal";
      case "casual":
        return "casual";
      default:
        return "helpful";
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return alert("Please select a file first");

    try {
      const data = await uploadFile(selectedFile);
      setSummary(data.summary);
      setMarkdown(data.markdown_text);
      console.log("File uploaded:", data);
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Upload failed, check console for details.");
    }
  };

  const handleCreateAgent = async () => {
    try {
      const agentName = prompt("Enter agent name:") || "no_name";
      const agentData = await createAgent(agentName, personality);
      setAgentId(agentData.agent_id);
      alert(`Agent created! ID: ${agentData.agent_id}`);
    } catch (err) {
      console.error("Agent creation failed:", err);
      alert("Could not create agent, see console for details.");
    }
  };

  const handleChat = async () => {
    if (!agentId) return alert("No agent created yet");
    if (!chatMessage.trim()) return;

    try {
      const chatResponse = await sendChatMessage(agentId, chatMessage);
      setChatLog((prev) => [
        ...prev,
        `You: ${chatMessage}`,
        `Assistant: ${chatResponse.reply}`,
      ]);
      setChatMessage("");
    } catch (err) {
      console.error("Chat failed:", err);
    }
  };

  return (
    <main className="min-h-screen bg-personality-helpful text-white p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <h1 className="text-3xl font-bold mb-6 text-center">
          Local Research Assistant
        </h1>

        {/* Personality selection */}
        <div className="mb-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <label className="font-medium">Assistant Personality:</label>
          <select
            className="text-black border rounded p-2"
            value={personality}
            onChange={(e) => setPersonality(e.target.value)}
          >
            <option value="helpful">Helpful (Default)</option>
            <option value="formal">Formal</option>
            <option value="casual">Casual</option>
          </select>
          <button
            onClick={handleCreateAgent}
            className={`btn btn-${personalityColor()}`}
          >
            Create Agent
          </button>
        </div>

        {/* Upload section */}
        <div className="mb-10 text-center">
          <h2 className="text-lg font-medium mb-2">
            {personality === "formal"
              ? "Please upload a relevant research document for my analysis."
              : personality === "casual"
              ? "Hey ya! Drop a research doc here and I’ll check it out!"
              : "Upload a relevant research document you’d like me to read"}
          </h2>
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={handleFileChange}
            className="mb-3 text-black"
          />
          <br />
          <button
            onClick={handleUpload}
            className={`btn btn-${personalityColor()}`}
          >
            Upload & Summarize
          </button>
        </div>

        {/* Summary section */}
        {summary && (
          <div className="mb-8 bg-white text-black p-4 rounded shadow">
            <h3 className="text-xl font-semibold mb-2 text-center text-personality-helpful">
              Summary
            </h3>
            <pre className="whitespace-pre-wrap">{summary}</pre>
          </div>
        )}

        {/* Markdown display */}
        {markdown && (
          <div className="mb-8 bg-white text-black p-4 rounded shadow">
            <h3 className="text-xl font-semibold mb-2 text-center text-personality-helpful">
              Markdown
            </h3>
            <pre className="whitespace-pre-wrap">{markdown}</pre>
          </div>
        )}

        {/* Chat interface */}
        <div className="mt-10 text-center">
          <h2 className="text-lg font-medium mb-2">Chat with Agent</h2>
          <textarea
            value={chatMessage}
            onChange={(e) => setChatMessage(e.target.value)}
            className="w-full text-black border p-2 rounded mb-3"
            rows={3}
            placeholder={
              personality === "formal"
                ? "Enter your inquiry..."
                : personality === "casual"
                ? "Got a question? Shoot!"
                : "Ask me something about your uploaded documents..."
            }
          />
          <button
            onClick={handleChat}
            className={`btn btn-${personalityColor()}`}
          >
            Send
          </button>

          <div className="mt-4 bg-white text-black p-4 rounded shadow max-h-60 overflow-y-auto text-sm text-left">
            {chatLog.map((msg, i) => (
              <p key={i} className="mb-1">
                {msg}
              </p>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}

