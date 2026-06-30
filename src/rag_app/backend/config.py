import os
from pathlib import Path
from langchain_ollama import ChatOllama, OllamaEmbeddings
from enum import Enum


class ConfigKeys(Enum):
    RESOURCES_DIR = "resources_dir"
    GEN_MODEL = "generation_model"
    EMBED_MODEL = "embedding_model"


class AppConfig:
    def __init__(self):
        self.root_path = Path(__file__).parent.parent.parent.parent

        self.data_dir = self.root_path / ".rag_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._resources_dir = self.root_path / "documents"
        if not self._resources_dir.exists():
            self._resources_dir.mkdir(parents=True, exist_ok=True)

        self._gen_model = "llama3.2:3b"
        self._embed_model = "nomic-embed-text"

        # 3. Initialize LangChain Objects
        self.llm = ChatOllama(model=self._gen_model, temperature=0.0)
        self.embeddings = OllamaEmbeddings(model=self._embed_model)

    @property
    def gen_model(self) -> str:
        return self._gen_model

    @gen_model.setter
    def gen_model(self, new_model: str) -> None:
        self._gen_model = new_model
        # Rebuild llm when model changes
        self.llm = ChatOllama(model=self._gen_model, temperature=0.0)

    @property
    def resources_dir(self) -> Path:
        return self._resources_dir

    @resources_dir.setter
    def resources_dir(self, new_dir: Path | str) -> None:
        self._resources_dir = Path(new_dir)
        if not self._resources_dir.exists():
            self._resources_dir.mkdir(parents=True, exist_ok=True)

    @property
    def embed_model(self) -> str:
        return self._embed_model

    @embed_model.setter
    def embed_model(self, new_model: str) -> None:
        self._embed_model = new_model
        self.embeddings = OllamaEmbeddings(model=self._embed_model)

    def init_from_db(self) -> None:
        from rag_app.backend.db import get_configs

        keys_to_fetch = [
            ConfigKeys.RESOURCES_DIR.value,
            ConfigKeys.GEN_MODEL.value,
            ConfigKeys.EMBED_MODEL.value,
        ]

        configs = get_configs(keys_to_fetch)

        if ConfigKeys.RESOURCES_DIR.value in configs:
            config.resources_dir = Path(configs[ConfigKeys.RESOURCES_DIR.value])

        if ConfigKeys.GEN_MODEL.value in configs:
            config.gen_model = configs[ConfigKeys.GEN_MODEL.value]

        if ConfigKeys.EMBED_MODEL.value in configs:
            config.embed_model = configs[ConfigKeys.EMBED_MODEL.value]


# create singleton
config = AppConfig()
