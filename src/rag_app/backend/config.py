import os
from pathlib import Path
from platformdirs import user_data_path
from langchain_ollama import ChatOllama, OllamaEmbeddings
from enum import Enum
import uuid


class ConfigKeys(Enum):
    RESOURCES_DIR = "resources_dir"
    GEN_MODEL = "generation_model"
    EMBED_MODEL = "embedding_model"
    WORKSPACE_NAME = "active_workspace_id"
    USE_CHAT_HISTORY = "use_chat_history"
    USE_WEB_SEARCH = "use_web_search"
    K_VALUE = "k_value"


# user agent for duckduck go search
os.environ["USER_AGENT"] = "RagApp"


class AppConfig:
    def __init__(self):
        self.user_home_path = Path.home()

        self.data_dir = user_data_path("rag-app")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.default_resources_dir = self.user_home_path / "rag-app-documents"
        self.default_resources_dir.mkdir(parents=True, exist_ok=True)

        self._resources_dir = self.default_resources_dir

        self._gen_model = "llama3.2:3b"
        self._embed_model = "nomic-embed-text"

        self.llm = ChatOllama(model=self._gen_model, temperature=0.0)
        self.embeddings = OllamaEmbeddings(model=self._embed_model)

        self._workspace_name = "default"
        self._workspace_id: uuid.UUID | None = None

        self._use_chat_history = False
        self._use_web_search = False

        self._k_value = 5

    # generational model
    @property
    def gen_model(self) -> str:
        return self._gen_model

    @gen_model.setter
    def gen_model(self, new_model: str) -> None:
        self._gen_model = new_model
        # Rebuild llm when model changes
        self.llm = ChatOllama(model=self._gen_model, temperature=0.0)

    # resources directory
    @property
    def resources_dir(self) -> Path:
        return self._resources_dir

    @resources_dir.setter
    def resources_dir(self, new_dir: Path | str) -> None:
        self._resources_dir = Path(new_dir)
        # if not self._resources_dir.exists():
        # self._resources_dir.mkdir(parents=True, exist_ok=True)

    # embedding model
    @property
    def embed_model(self) -> str:
        return self._embed_model

    @embed_model.setter
    def embed_model(self, new_model: str) -> None:
        self._embed_model = new_model
        self.embeddings = OllamaEmbeddings(model=self._embed_model)

    # workspace
    @property
    def workspace_name(self) -> str:
        return self._workspace_name

    @workspace_name.setter
    def workspace_name(self, new_workspace: str) -> None:
        if new_workspace:
            self._workspace_name = new_workspace

    @property
    def workspace_id(self) -> uuid.UUID | None:
        return self._workspace_id

    @workspace_id.setter
    def workspace_id(self, new_workspace_id: uuid.UUID | str) -> None:
        if isinstance(new_workspace_id, str):
            self._workspace_id = uuid.UUID(new_workspace_id)
        else:
            self._workspace_id = new_workspace_id

    # global config
    @property
    def use_chat_history(self) -> bool:
        return self._use_chat_history

    @use_chat_history.setter
    def use_chat_history(self, new_val: bool) -> None:
        self._use_chat_history = new_val

    @property
    def use_web_search(self) -> bool:
        return self._use_web_search

    @use_web_search.setter
    def use_web_search(self, new_val: bool) -> None:
        self._use_web_search = new_val

    @property
    def k_value(self) -> int:
        return self._k_value

    @k_value.setter
    def k_value(self, new_val: int) -> None:
        if new_val in range(2, 21):
            self._k_value = int(new_val)

    def init_from_db(self) -> None:
        from rag_app.backend.database import (
            get_configs,
            get_workspace_info,
            add_workspace,
        )

        # configs init
        keys_to_fetch = [
            ConfigKeys.WORKSPACE_NAME.value,
            ConfigKeys.USE_CHAT_HISTORY.value,
            ConfigKeys.USE_WEB_SEARCH.value,
            ConfigKeys.K_VALUE.value,
        ]

        configs = get_configs(keys_to_fetch)

        if ConfigKeys.WORKSPACE_NAME.value in configs:
            config.workspace_name = configs[ConfigKeys.WORKSPACE_NAME.value]

        if ConfigKeys.USE_CHAT_HISTORY.value in configs:
            val = configs[ConfigKeys.USE_CHAT_HISTORY.value]
            config.use_chat_history = str(val).lower() in ("true", "1")

        if ConfigKeys.USE_WEB_SEARCH.value in configs:
            val = configs[ConfigKeys.USE_WEB_SEARCH.value]
            config.use_web_search = str(val).lower() in ("true", "1")

        if ConfigKeys.K_VALUE.value in configs:
            config.k_value = int(configs[ConfigKeys.K_VALUE.value])

        # workspace init

        workspace_info = get_workspace_info(self.workspace_name)
        if workspace_info is None:
            self.resources_dir = Path(self.default_resources_dir)
            new_id = add_workspace(config._workspace_name)
            if new_id is not None:
                self.workspace_id = new_id
        else:
            config.resources_dir = Path(workspace_info[0])
            config.workspace_id = workspace_info[1]
            config.gen_model = workspace_info[2]
            config.embed_model = workspace_info[3]


# create singleton
config = AppConfig()
