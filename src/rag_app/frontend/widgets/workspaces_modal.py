from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Label, Input, Button, Static
from textual.containers import Horizontal
from textual import on
from rag_app.backend.config import ConfigKeys, config
from pathlib import Path
from textual.validation import Function, Length
import uuid
from rag_app.backend.config import config
from rag_app.backend.db import (
    get_all_workspaces,
    add_workspace,
    exists_workspace_by_name,
    delete_workspace,
    save_configs,
)
from textual.widgets import OptionList
from textual.widgets.option_list import Option
import random


class WorkspaceMenuModal(ModalScreen):
    CSS_PATH = "../styles/style_workspace_modal.tcss"

    BINDINGS = [
        ("escape", "close_modal", "Close modal"),
        ("x", "delete_workspace", "Delete selected workspace"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspaces: dict[str, tuple[str, int]] = get_all_workspaces()

    def create_options_from_dict(self) -> list[Option | None]:
        output_options: list[Option | None] = []

        for key, value in self.workspaces.items():
            name = value[0]
            # show the active keyword if it is active
            if config.workspace_id == uuid.UUID(key):
                name += " (active)"
            option_name = Option(f"  {name}", id=key)

            file_message = (
                f"  └── 📊 {value[1]} files indexed"
                if value[1] != 0
                else "  └── 📁 Empty Workspace"
            )

            option_file_count = Option(file_message, id=key + "-info", disabled=True)

            output_options.append(option_name)
            output_options.append(option_file_count)
            output_options.append(None)

        return output_options

    def compose(self) -> ComposeResult:
        with Vertical(id="workspaces-dialog"):
            yield Label("Workspaces Management", classes="workspaces-menu-title")

            generated_options = self.create_options_from_dict()

            yield OptionList(
                *generated_options,
                id="workspace-options",
            )

            yield Horizontal(
                Label(r"\[x] - delete workspace", classes="label-warning"),
                Label(r"\[Enter] - activate workspace", classes="label-note"),
                id="notes-horizontal",
            )

            yield Label("Create New Workspace:", classes="input-label")
            yield Input(
                value="",
                placeholder="Type name and press Enter...",
                id="add-workspace-input",
                validators=[Length(minimum=1, maximum=256)],
            )

    def update_option_list(self) -> None:
        option_list = self.query_one("#workspace-options", OptionList)
        option_list.clear_options()
        option_list.add_options(self.create_options_from_dict())
        # option_list.scroll_end(animate=True)

    def action_close_modal(self) -> None:
        self.dismiss()

    # when workspace is selected to use
    @on(OptionList.OptionSelected, "#workspace-options")
    def handle_workspace_selection(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option.id

        if option_id is None or option_id.endswith("-info"):
            return

        workspace_name = str(event.option.prompt).strip()
        save_configs({ConfigKeys.WORKSPACE_NAME.value: workspace_name})
        config.workspace_id = uuid.UUID(option_id)
        config.workspace_name = workspace_name

        self.dismiss(option_id)

    # when new workspace is created
    @on(Input.Submitted, "#add-workspace-input")
    def handle_add_new_workspace(self, event: Input.Submitted) -> None:
        new_workspace_name = event.input.value.strip()
        # validate the input
        if not new_workspace_name:
            return

        if exists_workspace_by_name(new_workspace_name):
            self.app.notify("Name must be unique")
            return

        workspace_id = uuid.uuid4()
        id = add_workspace(new_workspace_name, workspace_id)

        if id is None:
            return

        # update the ui with the new workspace
        self.workspaces[str(workspace_id)] = (
            new_workspace_name,
            0,
        )

        self.update_option_list()

        event.input.value = ""

    def action_delete_workspace(self) -> None:
        # cannot delete all workspaces
        if len(self.workspaces) == 1:
            self.app.notify("Cannot delete all workspaces")
            return

        option_list = self.query_one("#workspace-options", OptionList)
        highlighted_index = option_list.highlighted

        if highlighted_index is None:
            return

        selected_option = option_list.get_option_at_index(highlighted_index)
        option_id = selected_option.id

        if option_id is None:
            return

        if option_id in self.workspaces:
            if not delete_workspace(option_id):
                print("Error deleting workspace")
                return

            del self.workspaces[option_id]

            self.update_option_list()
