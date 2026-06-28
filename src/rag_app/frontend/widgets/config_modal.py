from textual.app import ComposeResult
from textual.widgets import Switch
from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Switch, Label, Input, Select, Button
from textual.containers import Vertical, Horizontal
from textual import on
from rag_app.backend.rag import gen_model
from rag_app.backend.db import resources_dir, embed_model


class ConfigModal(ModalScreen):

    CSS_PATH = "../styles/style_config_modal.tcss"

    BINDINGS = [
        ("escape", "close_config", "Close config"),
        ("ctrl+s", "save_config", "Save config"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="config-dialog"):
            yield Label("Application Config", classes="config-title")

            with Horizontal(classes="config-row"):
                yield Label("Resources directory:")
                yield Input(
                    value=str(resources_dir),
                    placeholder="absolute path eg. /home/user/...",
                    id="cfg-res-dir",
                )

            yield Label("Model config", classes="config-title")

            with Horizontal(classes="config-row"):
                yield Label("Generation model (LLM):")
                yield Input(
                    value=gen_model, placeholder="e.g., llama3.2:4b", id="cfg-model"
                )

            with Horizontal(classes="config-row"):
                yield Label("Embedding model*:")
                yield Input(
                    value=embed_model,
                    placeholder="e.g., nomic-embed-text",
                    id="cfg-embed-model",
                )

            yield Label(
                "*After changing embedding model all resources will be removed",
                classes="label-note",
            )

            # with Horizontal(classes="config-row"):
            #     yield Label("Temperature:")
            #     yield Select(
            #         options=[
            #             ("0.0 (Default)", 0.0),
            #             ("0.7 (Balanced)", 0.7),
            #             ("1.0 (Creative)", 1.0),
            #         ],
            #         value=0.0,
            #         id="cfg-temperature",
            #     )

            with Horizontal(id="config-actions"):
                yield Button(
                    r"Save & Close \[^s]", variant="success", flat=True, id="btn-save"
                )
                yield Button(
                    r"Cancel \[esc]",
                    variant="error",
                    flat=True,
                    id="btn-cancel",
                )

    @on(Button.Pressed, "#btn-cancel")
    def action_close_config(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#btn-save")
    def action_save_config(self) -> None:
        print("Saving config")
