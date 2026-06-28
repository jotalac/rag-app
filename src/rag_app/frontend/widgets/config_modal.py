from textual.app import ComposeResult
from textual.widgets import Switch
from textual.screen import ModalScreen
from textual.containers import Vertical
from textual.widgets import Switch, Label, Input, Select, Button
from textual.containers import Vertical, Horizontal


class ConfigModal(ModalScreen):

    CSS_PATH = "../styles/style_config_modal.tcss"

    BINDINGS = [
        ("esc", "dismiss", "Close config"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="config-dialog"):
            yield Label("Application Settings", id="config-title")

            # 1. Toggle Setting (e.g., Enable Stream Mode)
            with Horizontal(classes="config-row"):
                yield Label("Enable Streaming:")
                yield Switch(value=True, id="cfg-streaming")

            # 2. Text Input Setting (e.g., Change Model Name)
            with Horizontal(classes="config-row"):
                yield Label("Ollama Model:")
                yield Input(
                    value="gemma4:e4b", placeholder="e.g., llama3.1", id="cfg-model"
                )

            # 3. Dropdown Setting (e.g., Temperature Selection)
            with Horizontal(classes="config-row"):
                yield Label("Temperature:")
                yield Select(
                    options=[
                        ("0.0 (Precise)", 0.0),
                        ("0.7 (Balanced)", 0.7),
                        ("1.0 (Creative)", 1.0),
                    ],
                    value=0.0,
                    id="cfg-temperature",
                )

            # 4. Action Buttons
            with Horizontal(id="config-actions"):
                yield Button("Save & Close", variant="primary", id="btn-save")
                yield Button("Cancel", variant="error", id="btn-cancel")
