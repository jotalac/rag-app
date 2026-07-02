from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Label, Input, Button, Static
from textual.containers import Horizontal
from textual import on
from rag_app.backend.config import ConfigKeys
from pathlib import Path
from textual.validation import Function, Length

from rag_app.backend.config import config
from textual.widgets import OptionList
from textual.widgets.option_list import Option


class WorkspaceMenuModal(ModalScreen):
    CSS_PATH = "../styles/style_workspace_modal.tcss"

    BINDINGS = [
        ("escape", "close_modal", "Close modal"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="workspaces-dialog"):
            yield Label("Workspaces Management", classes="workspaces-menu-title")

            yield OptionList(
                Option("  Ktor Workspace (active)", id="wk1"),
                Option("  └── 📊 41 files indexed", id="wk1-info", disabled=True),
                None,
                Option("  Workspace 2", id="wk2"),
                Option("  └── 📊 12 files indexed", id="wk2-info", disabled=True),
                None,
                Option("  Workspace 3", id="wk34"),
                Option("  └── 📁 Empty Workspace", id="wk64-info", disabled=True),
                None,
                Option("  Workspace 3", id="wk4"),
                Option("  └── 📁 Empty Workspace", id="wkh-info", disabled=True),
                None,
                Option("  Workspace 3", id="wk5"),
                Option("  └── 📁 Empty Workspace", id="wkdrg3-info", disabled=True),
                None,
                Option("  Workspace 3", id="wk5dsf"),
                Option("  └── 📁 Empty Workspace", id="wkdrsdefg3-info", disabled=True),
                None,
                Option("  Workspace 3", id="wkdfs5"),
                Option(
                    "  └── 📁 Empty Workspace", id="wkdrsfghdfg3-info", disabled=True
                ),
                None,
                Option("  Workspace 3", id="wk5ddfgsf"),
                Option("  └── 📁 Empty Workspace", id="g3-fginfo", disabled=True),
                None,
                Option("  Workspace 3", id="wkdfghfs5"),
                Option("  └── 📁 Empty Workspace", id="ngdffo", disabled=True),
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

    def action_close_modal(self) -> None:
        self.dismiss()

    @on(OptionList.OptionSelected, "#workspace-options")
    def handle_workspace_selection(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option.id

        print(event.option.prompt)

        # Guard clause: Don't allow clicking the disabled info rows
        if option_id and option_id.endswith("-info"):
            return

        self.dismiss(option_id)
