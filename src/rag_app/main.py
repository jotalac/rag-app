from textual.app import ComposeResult
from textual.widgets import Footer, Static, Header
from rag_app.frontend.widgets.prompt_input import PromptInput
from rag_app.frontend.widgets.chat_widgets import ChatText
from pathlib import Path
from rag_app.frontend.input_router import route_user_input
from rag_app.frontend.widgets.chat_widgets import AIMessage
from rag_app.frontend.widgets.chat_widgets import SystemMessageType, WelcomeMessage
from rag_app.frontend.widgets.config_modal import ConfigModal
from rag_app.frontend.widgets.workspace_menu_modal import WorkspaceMenuModal
from rag_app.backend.config import config
from rag_app.frontend.app_workers import AppWorkers
from textual.worker import Worker, get_current_worker
from rag_app.frontend.widgets.resources_tree_widget import ResourcesTreeWidget


class RagApp(AppWorkers):

    CSS_PATH = "frontend/styles/style.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("/", "focus_input", "Focus input"),
        ("escape", "unfocus_input", "Unfocus input"),
        ("ctrl+l", "clear_chat", "Clear chat"),
        ("ctrl+c", "cancel_execution", "Cancel system execution"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_working = False
        self.active_worker: Worker | None = None
        self.active_ai_widget: AIMessage | None = None

    def compose(self) -> ComposeResult:
        yield Header()

        yield ChatText()

        yield PromptInput()

        yield Footer(show_command_palette=False)

    def on_mount(self):
        self.add_welcome_text()
        self.action_focus_input()
        self.load_all_config_values()

    def load_all_config_values(self):
        config.init_from_db()

    # ACTIONS
    def action_toggle_dark(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_focus_input(self) -> None:
        text_input = self.query_one(PromptInput)
        text_input.focus()

    def action_unfocus_input(self) -> None:
        self.set_focus(None)

    def action_cancel_execution(self) -> None:
        if (
            self.is_working
            and self.active_worker
            and not self.active_worker.is_finished
        ):
            self.active_worker.cancel()

            if self.active_ai_widget:
                self.active_ai_widget.update_text(
                    self.active_ai_widget.message + "\n\n" + "**[Generation canceled]**"
                )
                self.active_ai_widget = None
            else:
                chat_text_box = self.query_one(ChatText)
                chat_text_box.add_system_message(
                    "Canceling... waiting for current operation to finish.",
                    SystemMessageType.INFO,
                )

    async def action_clear_chat(self) -> None:
        print(self.is_working)
        if self.is_working:
            self.notify("Wait for the job to finish")
            return

        chat_text_box = self.query_one(ChatText)
        await chat_text_box.remove_children()
        self.add_welcome_text()

    def action_open_config(self) -> None:
        self.push_screen(ConfigModal())

    def action_open_workspace_menu(self) -> None:
        self.push_screen(WorkspaceMenuModal())

    def add_welcome_text(self) -> None:
        self.query_one(ChatText).mount(WelcomeMessage())

    def on_prompt_input_prompt_submitted(
        self, event: PromptInput.PromptSubmitted
    ) -> None:
        if self.is_working:
            return

        # reset the input
        promptInput = self.query_one(PromptInput)
        promptInput.value = ""
        promptInput.command_history.append(event.text)
        promptInput.history_index = len(promptInput.command_history)

        # add user message
        user_prompt = event.text
        chat_text_box = self.query_one(ChatText)
        chat_text_box.add_user_message(user_prompt)

        route_user_input(self, user_prompt, chat_text_box)


def run_cli():
    app = RagApp()
    app.run()


if __name__ == "__main__":
    run_cli()
