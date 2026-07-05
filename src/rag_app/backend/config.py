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

    def init_from_db(self) -> None:
        from rag_app.backend.db import (
            get_configs,
            get_workspace_info,
            add_workspace,
        )

        # configs init
        keys_to_fetch = [
            ConfigKeys.WORKSPACE_NAME.value,
        ]

        configs = get_configs(keys_to_fetch)

        if ConfigKeys.WORKSPACE_NAME.value in configs:
            config.workspace_name = configs[ConfigKeys.WORKSPACE_NAME.value]

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
