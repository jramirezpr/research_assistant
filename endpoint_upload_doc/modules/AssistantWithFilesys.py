import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from letta_client import Letta

# Load environment variables if not already set. Letta client needs this.
if "OPENAI_API_KEY" not in os.environ:
    load_dotenv()


class AssistantWithFilesys:
    """
    A generic class for managing Letta agents and their attached filesystem folders.

    This class encapsulates the setup and management of a Letta agent and an associated
    folder for file storage and retrieval.


    Args:
        agent_name (str): Name of the agent to create or retrieve.
        folder_name (str): Name of the folder to create or retrieve.
        base_url (str, optional): URL of the Letta server. Defaults to "http://letta_server:8283".
        model (str, optional): Model name used when creating a new agent. Defaults to "openai/gpt-4o-mini".
        personality (str, optional): One of {"helpful", "formal", "casual"}. Determines the agent's tone and behavior.

    Attributes:
        base_url (str): Base URL of the connected Letta server.
        client (Letta): Instance of the Letta API client.
        agent_name (str): Name of the managed agent.
        folder_name (str): Name of the managed folder.
        model (str): Model used for the agent.
        personality (str): Personality type for the agent.
        agent (AgentState): The retrieved or newly created Letta agent.
        folder (FolderState): The retrieved or newly created Letta folder.
        executor (ThreadPoolExecutor): Thread pool for background upload jobs.

    Example:
        >>> assistant = AssistantWithFilesys(
        ...     agent_name="research_helper",
        ...     folder_name="uploaded_docs",
        ...     personality="casual"
        ... )
        >>> print(assistant.get_agent_id())
        >>> print(assistant.get_folder_id())
    """

    PERSONALITY_PROFILES = {
        "helpful": "I am Michael, a helpful assistant named geared towards research. No frills, what you see is what you get.",
        "formal": (
            "I am Xavier, a formal and precise assistant who communicates in a structured, "
            "professional tone. I provide thorough explanations and avoid colloquial language."
            "I avoid contractions and imprecise descriptors whenever possible ."

        ),
        "casual": (
            "Hey there! I'm Josh, a chill, easygoing assistant who keeps things simple and fun. "
            "I talk like a friend who's helping you out with your research. Yolo!"
        ),
    }

    def __init__(
        self,
        agent_name: str,
        folder_name: str,
        base_url: str = "http://letta_server:8283",
        model: str = "openai/gpt-4o-mini",
        personality: str = "helpful"
    ):
        """Initialize the Letta client, ensure the agent and folder exist, and attach them."""
        self.base_url = base_url
        self.client = Letta(base_url=self.base_url)
        self.agent_name = agent_name
        self.folder_name = folder_name
        self.model = model
        self.personality = self._validate_personality(personality)
        self.agent = None
        self.folder = None
        self.executor = ThreadPoolExecutor(max_workers=3)

        # Automatically set up on init
        self.agent = self._ensure_agent_exists()
        self.folder = self._ensure_folder_exists()
        self._attach_folder_to_agent()

    def _validate_personality(self, personality: str) -> str:
        """Normalize and validate personality, with fallback to 'helpful'."""
        p = personality.strip().lower() if personality else "helpful"
        if p not in self.PERSONALITY_PROFILES:
            print(f" personality '{personality}'Not available. Defaulting to 'helpful'.")
            return "helpful"
        return p

    def _get_personality_text(self):
        """Return the text for the chosen personality (defaults to 'helpful')."""
        return self.PERSONALITY_PROFILES.get(self.personality, self.PERSONALITY_PROFILES["helpful"])

    def _ensure_agent_exists(self):
        """Retrieve or create a Letta agent."""
        agents = self.client.agents.list(name=self.agent_name)
        if agents:
            print(f"[Letta] Agent '{self.agent_name}' already exists, retrieving.")
            agent = agents[0]
        else:
            print(f"[Letta] Creating new agent '{self.agent_name}' using model '{self.model}' and personality '{self.personality}'...")
            agent = self.client.agents.create(
                name=self.agent_name,
                model=self.model,
                embedding="openai/text-embedding-3-small",
                memory_blocks=[
                    {"label": "human", "limit": 2000,
                     "value": "Occupation: Researcher."},
                    {"label": "persona", "limit": 2000, "read_only": True,
                     "value": self._get_personality_text()},
                ],
                tools=["web_search"]
            )
        return agent

    def _ensure_folder_exists(self):
        """Retrieve or create a Letta folder for document uploads."""
        folders = self.client.folders.list(name=self.folder_name)
        if folders:
            print(f"[Letta] Folder '{self.folder_name}' already exists, retrieving.")
            folder = folders[0]
        else:
            print(f"[Letta] Folder '{self.folder_name}' not found, creating.")
            embedding_configs = self.client.models.embeddings.list()
            if not embedding_configs:
                raise RuntimeError("No embedding configurations available from Letta server.")
            embedding_config = embedding_configs[-2] if len(embedding_configs) >= 2 else embedding_configs[-1]

            folder = self.client.folders.create(
                name=self.folder_name,
                embedding_config=embedding_config
            )
        return folder

    def _attach_folder_to_agent(self):
        """Attach the folder to the agent (if not already attached)."""
        try:
            print(f"[Letta] Attaching folder '{self.folder_name}' to agent '{self.agent_name}'...")
            self.client.agents.folders.attach(agent_id=self.agent.id, folder_id=self.folder.id)
        except Exception as e:
            print(f"[Letta] Folder may already be attached: {e}")

    def upload_file(self, file_path: str) -> str:
        """
        Upload a file asynchronously to the agent's folder.
        Returns the Letta job ID immediately for progress tracking.
        """
        if not self.folder:
            raise RuntimeError("Folder not initialized for this assistant.")

        folder_id = self.folder.id

        # Start upload synchronously to get the job.id
        print(f"[Upload] Starting upload for: {file_path}")
        with open(file_path, "rb") as f:
            job = self.client.folders.files.upload(folder_id=folder_id, file=f)

        job_id = job.id
        print(f"[Upload] Job created with ID: {job_id}")

        # Define background polling task
        def _poll_job():
            try:
                while True:
                    job_info = self.client.jobs.retrieve(job_id)
                    if job_info.status == "completed":
                        print(f"[Upload] Completed: {file_path}")
                        break
                    elif job_info.status == "failed":
                        print(f"[Upload] Failed: {file_path} – {job_info.metadata}")
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"[Upload] Exception while polling {file_path}: {e}")

        # Launch the poller in background
        self.executor.submit(_poll_job)

        return job_id






    def chat(self, message: str) -> dict:
        """
        Send a message to this agent and return the assistant's latest reply
        plus the current conversation history.

        Args:
            message (str): The user's message text.

        Returns:
            dict: {
                "reply": str,
                "conversation": list[dict]
            }
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized.")

        try:
            print(f"[Letta] Sending message to agent '{self.agent.name}'...")

            response = self.client.agents.messages.create(
                agent_id=self.agent.id,
                messages=[
                    {"role": "user", "content": message}
                ]
            )

            reply_text = None
            for msg in response.messages:
                if msg.message_type == "assistant_message":
                    reply_text = msg.content
                    break

            if not reply_text:
                reply_text = "[Letta] No assistant response found."

            conversation = self.get_conversation(limit=50)

            return {
                "reply": reply_text,
                "conversation": conversation
            }

        except Exception as e:
            print(f"[Letta] Chat error: {e}")
            return {"reply": f"[Letta] Chat failed: {e}", "conversation": []}


    def get_conversation(self, limit: int = 50) -> list:
        """
        Retrieve the recent user and assistant messages for this agent.

        Args:
            limit (int): Maximum number of messages to fetch (default=50).

        Returns:
            list[dict]: conversation messages sorted oldest → newest.
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized.")

        try:
            messages = self.client.agents.messages.list(
                agent_id=self.agent.id,
                limit=limit,
                use_assistant_message=True
            )

            conversation = []
            for m in messages:
                if m.message_type == "user_message":
                    role = "user"
                elif m.message_type == "assistant_message":
                    role = "assistant"
                else:
                    continue

                content = m.content if isinstance(m.content, str) else str(m.content)
                conversation.append({
                    "role": role,
                    "content": content,
                    "timestamp": getattr(m, "date", None)
                })

            # Sort from oldest to newest
            conversation = sorted(conversation, key=lambda x: x["timestamp"])
            return conversation

        except Exception as e:
            print(f"[Letta] Conversation fetch error: {e}")
            return []




    def get_agent(self):
        """Return the full Agent object."""
        return self.agent

    def get_folder(self):
        """Return the full Folder object."""
        return self.folder

    def get_agent_id(self):
        """Return the agent's ID."""
        return self.agent.id if self.agent else None

    def get_folder_id(self):
        """Return the folder's ID."""
        return self.folder.id if self.folder else None
