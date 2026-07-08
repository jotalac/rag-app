from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Label, Input, Button, Collapsible, Checkbox
from textual.containers import Horizontal
from textual import on
from pathlib import Path
from textual.validation import Function, Length, Integer
from rag_app.backend.database import (
    save_workspace_configs,
    remove_all_resources,
    save_configs,
)
from rag_app.backend.config import config, ConfigKeys


class ConfigModal(ModalScreen):

    CSS_PATH = "../styles/style_config_modal.tcss"

    BINDINGS = [
        ("escape", "close_config", "Close config"),
        ("ctrl+s", "save_config", "Save config"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="config-dialog"):
            with Collapsible(
                collapsed=True,
                title="Workspace Config",
                classes="config-collapsible",
                id="workspace-collapsible",
            ):

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

            with Collapsible(
                collapsed=True,
                title="AI Generation Config (global)",
                classes="config-collapsible",
                id="ai-gen-collapsible",
            ):

                # chat history checkbox
                chat_history_checkbox = Checkbox(
                    "Use chat history",
                    value=config.use_chat_history,
                    id="chat-history-checkbox",
                    button_first=False,
                    classes="config-checkbox",
                )
                chat_history_checkbox.tooltip = "LLM will se your previous messages (not recommended for smaller models)"
                yield chat_history_checkbox

                web_search_checkbox = Checkbox(
                    "Use web search fallback",
                    value=config.use_web_search,
                    id="web-search-checkbox",
                    button_first=False,
                    classes="config-checkbox",
                )
                web_search_checkbox.tooltip = "Do web search when the required information is not found in the local resources"
                yield web_search_checkbox

                with Horizontal(classes="config-row"):
                    yield Label(
                        "Maximum number of context documents (chunks) - top-k:",
                        id="k-label",
                    )
                    yield Input(
                        value=str(config.k_value),
                        placeholder="2-20",
                        id="k-input",
                        validators=[Integer(minimum=2, maximum=20)],
                    )

            # save and cancel buttons
            with Horizontal(id="config-actions"):
                yield Button(
                    r"Save & Close \[^s]",
                    variant="success",
                    flat=True,
                    id="btn-save",
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
        k_input = self.query_one("#k-input", Input)
        chat_history_checkbox = self.query_one("#chat-history-checkbox", Checkbox)
        web_search_checkbox = self.query_one("#web-search-checkbox", Checkbox)

        # check if all are valid
        if (
            not resources_dir_input.is_valid
            or not embed_model_input.is_valid
            or not gen_model_input.is_valid
            or not k_input.is_valid
        ):
            self.notify("Invalid values", severity="warning")
            return

        new_old_resources_dir = (
            resources_dir_input.value.strip(),
            config.resources_dir,
        )
        new_old_embed_model = (embed_model_input.value.strip(), config.embed_model)
        new_gen_model = gen_model_input.value.strip()

        save_success = save_workspace_configs(
            resources_dir=new_old_resources_dir[0],
            gen_model=new_gen_model,
            embed_model=new_old_embed_model[0],
        )

        global_configs = {
            ConfigKeys.USE_CHAT_HISTORY.value: str(chat_history_checkbox.value),
            ConfigKeys.USE_WEB_SEARCH.value: str(web_search_checkbox.value),
            ConfigKeys.K_VALUE.value: str(k_input.value),
        }
        global_save_success = save_configs(global_configs)

        if not save_success or not global_save_success:
            self.notify("Error saving config", severity="error")
            return

        # Update in-memory config
        config.use_chat_history = chat_history_checkbox.value
        config.use_web_search = web_search_checkbox.value
        config.k_value = int(k_input.value)

        # delete all resources on embed model change
        if new_old_embed_model[0] != new_old_embed_model[1] or new_old_resources_dir[
            0
        ] != str(new_old_resources_dir[1]):

            self.notify("Deleting all workspace resources", severity="warning")
            remove_all_resources()

        self.notify("Config saved successfully", severity="information")

        self.action_close_config()

    def on_collapsible_expanded(self, event: Collapsible.Expanded) -> None:
        for collapsible in self.query(Collapsible):
            if collapsible.id != event.collapsible.id:
                collapsible.collapsed = True
