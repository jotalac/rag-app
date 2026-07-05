from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Label, Input, Button
from textual.containers import Horizontal
from textual import on
from rag_app.backend.config import ConfigKeys
from pathlib import Path
from textual.validation import Function, Length
from rag_app.backend.db import (
    save_configs,
    remove_all_resources,
)
from rag_app.backend.config import config


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
                yield Label("Resources directory*:")
                yield Input(
                    value=str(config.resources_dir),
                    placeholder="absolute path eg. /home/user/...",
                    id="cfg-res-dir",
                    validators=[
                        Function(self.validate_path, "Path doesn't t exist"),
                        Length(minimum=1),
                    ],
                )

            yield Label("Model config", classes="config-title")

            with Horizontal(classes="config-row"):
                yield Label("Generation model (LLM):")
                yield Input(
                    value=config.gen_model,
                    placeholder="e.g., llama3.2:4b",
                    id="cfg-model",
                    validators=[Length(minimum=1)],
                )

            with Horizontal(classes="config-row"):
                yield Label("Embedding model*:")
                yield Input(
                    value=config.embed_model,
                    placeholder="e.g., nomic-embed-text",
                    id="cfg-embed-model",
                    validators=[Length(minimum=1)],
                )

            yield Label(
                f"*If changed, all resources from [b]{config.workspace_name}[/b] workspace will be removed",
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

    def validate_path(self, input_value: str) -> bool:
        clean_path = input_value.strip()
        return True if Path(clean_path).exists() else False

    @on(Button.Pressed, "#btn-save")
    def action_save_config(self) -> None:
        # get the values form inputs
        resources_dir_input = self.query_one("#cfg-res-dir", Input)
        embed_model_input = self.query_one("#cfg-embed-model", Input)
        gen_model_input = self.query_one("#cfg-model", Input)

        # check if all are valid
        if (
            not resources_dir_input.is_valid
            or not embed_model_input.is_valid
            or not gen_model_input.is_valid
        ):
            self.notify("Invalid values", severity="warning")
            return

        new_resources_dir = resources_dir_input.value.strip()
        new_embed_model = embed_model_input.value.strip()
        new_gen_model = gen_model_input.value.strip()

        save_success = save_configs(
            {
                ConfigKeys.RESOURCES_DIR.value: new_resources_dir,
                ConfigKeys.EMBED_MODEL.value: new_embed_model,
                ConfigKeys.GEN_MODEL.value: new_gen_model,
            }
        )

        if not save_success:
            self.notify("Error saving config", severity="error")
            return

        # delete all resources on embed model change
        if new_embed_model != config.embed_model or new_resources_dir != str(
            config.resources_dir
        ):
            self.notify("Deleting all saved resources", severity="warning")
            remove_all_resources()

        config.resources_dir = Path(new_resources_dir)
        config.gen_model = new_gen_model
        config.embed_model = new_embed_model

        self.notify("Config saved successfully", severity="information")

        self.action_close_config()
