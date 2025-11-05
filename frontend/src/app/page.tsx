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
  const [loading, setLoading] = useState(false);
  const [creatingAgent, setCreatingAgent] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return alert("Please select a file first.");

    setLoading(true);
    try {
      const data = await uploadFile(selectedFile, agentId as string);
      setSummary(data.summary);
      setMarkdown(data.markdown_text);
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Upload failed. Check console.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAgent = async () => {
    try {
      setCreatingAgent(true);
      const agentName = prompt("Enter agent name:") || "no_name";
      const agentData = await createAgent(agentName, personality);
      setAgentId(agentData.agent_id);
      alert(`Agent created. ID: ${agentData.agent_id}`);
    } catch (err) {
      console.error("Agent creation failed:", err);
      alert("Could not create agent.");
    } finally {
      setCreatingAgent(false);
    }
  };

  const handleChat = async () => {
    if (!agentId) return alert("Create an agent first.");
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

  const buttonClasses =
    "px-4 py-2 rounded bg-white text-teal-700 font-semibold border border-white hover:bg-gray-100 transition";

  return (
    <div className="min-h-screen bg-teal-500 text-white p-10">
      <h1 className="text-center text-4xl font-bold mb-10">
        Local Research Assistant
      </h1>

      {/* Agent creation section */}
      <div className="flex gap-3 mb-8 justify-center">
        <select
          className="border rounded px-3 py-2 text-black"
          value={personality}
          onChange={(e) => setPersonality(e.target.value)}
          disabled={creatingAgent || !!agentId} // disable while creating or after creation
        >
          <option value="helpful">Helpful</option>
          <option value="formal">Formal</option>
          <option value="casual">Casual</option>
        </select>

        <button
          onClick={handleCreateAgent}
          className={buttonClasses}
          disabled={creatingAgent || !!agentId}
        >
          Create Agent
        </button>
      </div>

      {/* Spinner while creating agent */}
      {creatingAgent && (
        <div className="flex flex-col items-center mb-10">
          <div className="w-8 h-8 border-4 border-white border-t-transparent rounded-full animate-spin mb-2"></div>
          <p>Please wait, creating agent...</p>
        </div>
      )}

      {/* File upload & chat: only visible after agent creation */}
      {agentId && !creatingAgent && (
        <>
          {/* File upload */}
          <div className="text-center mb-10">
            <input type="file" onChange={handleFileChange} className="mb-3" />

            <button onClick={handleUpload} className={buttonClasses}>
              Upload & Summarize
            </button>

            {loading && (
              <div className="mt-4 flex justify-center">
                <div className="w-6 h-6 border-4 border-white border-t-transparent rounded-full animate-spin"></div>
              </div>
            )}
          </div>

          {/* Summary & Markdown */}
          {summary && (
            <div className="bg-white text-black p-4 rounded shadow mb-6">
              <h3 className="text-xl mb-2 font-bold">Summary</h3>
              <pre className="whitespace-pre-wrap">{summary}</pre>
            </div>
          )}

          {markdown && (
            <div className="bg-gray-100 text-black p-4 rounded shadow mb-6">
              <h3 className="text-xl mb-2 font-bold">Markdown</h3>
              <pre className="whitespace-pre-wrap overflow-x-auto">{markdown}</pre>
            </div>
          )}

          {/* Chat */}
          <div className="bg-white text-black p-4 rounded shadow">
            <h2 className="font-bold mb-2">Chat with Agent</h2>

            <textarea
              className="w-full border p-2 rounded mb-2 text-black"
              rows={3}
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              placeholder="Ask something about your uploaded documents..."
            />

            <button onClick={handleChat} className={buttonClasses}>
              Send
            </button>

            <div className="mt-3 max-h-48 overflow-y-auto text-sm">
              {chatLog.map((m, i) => (
                <p key={i} className="mb-1">
                  {m}
                </p>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}



