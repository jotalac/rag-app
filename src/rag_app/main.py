from textual.app import App, ComposeResult
from textual.widgets import Footer, Static
from rag_app.frontend.widgets.prompt_input import PromptInput
from rag_app.frontend.widgets.chat_widgets import ChatText
from pathlib import Path
from rag_app.frontend.command_handler import CommandHandler, Commands
from textual import work
from rag_app.backend.rag import generate_message
from rag_app.frontend.widgets.chat_widgets import AIMessage, Role


class RagApp(App):

    CSS_PATH = "frontend/tui.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("/", "focus_input", "Focus input"),
        ("escape", "unfocus_input", "Unfocus input"),
        ("ctrl+l", "clear_text", "Clear chat"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_generating = False

    def compose(self) -> ComposeResult:
        # yield Header()

        yield ChatText()

        yield PromptInput()

        yield Footer(show_command_palette=False)

    def action_toggle_dark(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_focus_input(self) -> None:
        text_input = self.query_one(PromptInput)
        text_input.focus()

    def action_unfocus_input(self) -> None:
        self.set_focus(None)

    def action_clear_chat(self) -> None:
        pass

    def on_mount(self):
        self.add_welcome_text()

    def add_welcome_text(self) -> None:
        current_dir = Path(__file__).parent
        file_path = current_dir / "resources" / "welcome.txt"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                welcome_text = f.read()

            welcome_label = Static(welcome_text, id="welcome-art")

            self.query_one(ChatText).mount(welcome_label)

        except FileNotFoundError:
            print("File not found")
            error_label = Static("Welcome! (error loading welcome art)")
            self.query_one(ChatText).mount(error_label)

    def on_prompt_input_prompt_submitted(
        self, event: PromptInput.PromptSubmitted
    ) -> None:
        if self.is_generating:
            return

        user_prompt = event.text
        chat_text_box = self.query_one(ChatText)
        chat_text_box.add_user_message(user_prompt)

        # check if the user input was command or prompt
        if user_prompt.startswith("/"):
            if user_prompt == Commands.EXIT.value:
                self.exit()
                return

            status, message = CommandHandler.handle_command(user_prompt)
            chat_text_box.add_system_message(message=message, message_type=status)

        else:
            ai_message_widget = AIMessage("")
            chat_text_box.mount(ai_message_widget)
            chat_text_box.scroll_end(animate=False)

            self.is_generating = True

            self.fetch_ai_response(user_prompt, chat_text_box, ai_message_widget)

    @work(thread=True)
    def fetch_ai_response(
        self, user_prompt: str, chat_text_box: ChatText, message_widget: AIMessage
    ) -> None:
        acc_response = ""

        # display the text as it is being generated
        for chunk in generate_message(user_prompt):
            acc_response += chunk
            self.app.call_from_thread(message_widget.update_text, acc_response)

            self.app.call_from_thread(chat_text_box.scroll_end, animate=False)

        self.is_generating = False


def run_cli():
    app = RagApp()
    app.run()


if __name__ == "__main__":
    run_cli()
