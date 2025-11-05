// src/lib/api.ts
// A lightweight helper to talk to your Flask + Letta APIs.
// Centralizes environment variables and fetch calls.

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
export const LETTA_URL = process.env.NEXT_PUBLIC_LETTA_URL;

if (!API_BASE_URL) console.warn("NEXT_PUBLIC_API_BASE_URL not set");
if (!LETTA_URL) console.warn(" NEXT_PUBLIC_LETTA_URL not set");

/**
 * Upload a document file to the Flask API.
 * Returns JSON: { summary, markdown_text, file_id, folder_id }
 */
export async function uploadFile(file: File, agentId: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("agent_id", agentId);

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Upload failed: ${response.status} - ${text}`);
  }

  return response.json();
}


/**
 * Poll upload status by folder_id and file_id.
 * Returns JSON: { file_id, status }
 */
export async function checkUploadStatus(folderId: string, fileId: string) {
  const response = await fetch(
    `${API_BASE_URL}/api/upload/status?folder_id=${folderId}&file_id=${fileId}`
  );

  if (!response.ok) {
    throw new Error("Failed to check upload status");
  }

  return response.json();
}

/**
 * Send a chat message to the agent.
 * Returns JSON with conversation and reply.
 */
export async function sendChatMessage(agentId: string, message: string) {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_id: agentId, message }),
  });

  if (!response.ok) {
    throw new Error(`Chat failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new Letta agent with a given personality.
 * Returns JSON with the agent info (agent_id, folder_id, etc.)
 */
export async function createAgent(
  agentName: string,
  personality: string = "helpful"
) {
  const response = await fetch(`${API_BASE_URL}/api/agent/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_name: agentName, personality }),
  });

  if (!response.ok) {
    throw new Error(`Failed to create agent: ${response.statusText}`);
  }

  return response.json();
}
