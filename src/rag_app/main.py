from textual.app import App, ComposeResult
from textual.widgets import Footer, Static, Header
from textual.containers import Vertical
from rag_app.frontend.widgets.prompt_input import PromptInput
from rag_app.frontend.widgets.chat_widgets import ChatText
from pathlib import Path
from rag_app.frontend.command_handler import Commands, handle_command
from textual import work
from textual.worker import Worker, get_current_worker
from rag_app.backend.rag import generate_message
from rag_app.frontend.widgets.chat_widgets import AIMessage, Role
from rag_app.frontend.widgets.custom_spinner import CustomSpinner
from rag_app.frontend.widgets.chat_widgets import SystemMessageType
from rag_app.frontend.widgets.config_modal import ConfigModal


class RagApp(App):

    CSS_PATH = "frontend/styles/style.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("/", "focus_input", "Focus input"),
        ("escape", "unfocus_input", "Unfocus input"),
        ("ctrl+l", "clear_chat", "Clear chat"),
        ("ctrl+c", "cancel_ai_generation", "Cancel AI generation"),
        ("c", "open_config", "Open Config"),
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

    def action_cancel_ai_generation(self) -> None:
        if (
            self.is_working
            and self.active_worker
            and not self.active_worker.is_finished
        ):
            self.active_worker.cancel()
            self.is_working = False

            if self.active_ai_widget:
                self.active_ai_widget.update_text(
                    self.active_ai_widget.message + "\n\n" + "[Generation canceled]"
                )
                self.active_ai_widget = None

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
        if self.is_working:
            return

        # reset the input
        promptInput = self.query_one(PromptInput)
        promptInput.value = ""
        promptInput.command_history.append(event.text)
        promptInput.history_index = len(promptInput.command_history)

        user_prompt = event.text
        chat_text_box = self.query_one(ChatText)
        chat_text_box.add_user_message(user_prompt)

        # check if the user input was command or prompt
        if user_prompt.startswith("/"):
            if user_prompt == Commands.EXIT.value:
                self.exit()
                return

            self.is_working = True

            self.active_worker = self.run_thread_command(user_prompt, chat_text_box)
            # chat_text_box.add_system_message(message=message, message_type=status)

        else:
            ai_message_widget = AIMessage("Generating response...")
            chat_text_box.mount(ai_message_widget)
            chat_text_box.scroll_end(animate=False)

            self.is_working = True
            self.active_ai_widget = ai_message_widget

            self.active_worker = self.fetch_ai_response(
                user_prompt, chat_text_box, ai_message_widget
            )

    @work(thread=True)
    def fetch_ai_response(
        self, user_prompt: str, chat_text_box: ChatText, message_widget: AIMessage
    ) -> None:
        worker = get_current_worker()
        acc_response = ""

        try:
            # display the text as it is being generated
            for chunk in generate_message(user_prompt):
                # append the new generated chunk
                acc_response += chunk
                self.app.call_from_thread(message_widget.update_text, acc_response)

                self.app.call_from_thread(chat_text_box.scroll_end, animate=False)

                # check if the generation wasn't canceled
                if worker.is_cancelled:
                    break
        except Exception:
            # display error message
            self.app.call_from_thread(
                chat_text_box.add_system_message,
                "**AI generation failed**  \n\n Make sure:\n- Ollama is running: `ollama serve`\n- You have downloaded the configured model: `ollama pull ...`",
                SystemMessageType.ERROR,
            )

            self.app.call_from_thread(message_widget.remove)  # type: ignore

        if not worker.is_cancelled:
            self.is_working = False

    @work(thread=True)
    def run_thread_command(self, user_prompt: str, chat_text_box: ChatText) -> None:
        worker = get_current_worker()

        # add the loader indicator
        loader = CustomSpinner(
            message="Processing request",
            id="cmd-loader",
        )

        def mount_loader():
            if not chat_text_box.query("#cmd-loader"):
                chat_text_box.mount(loader)
                chat_text_box.scroll_end(animate=False)

        def cleanup():
            loaders = chat_text_box.query("#cmd-loader")
            if loaders:
                loaders.remove()
                chat_text_box.scroll_end(animate=False)

        self.app.call_from_thread(mount_loader)

        for status, message in handle_command(user_prompt):

            def post_update(s=status, m=message):
                cleanup()
                chat_text_box.add_system_message(m, s)  # type: ignore
                mount_loader()

            self.app.call_from_thread(post_update)

            # check if the command wasn't canceled
            if worker.is_cancelled:
                self.app.call_from_thread(
                    chat_text_box.add_system_message,
                    "Command canceled!",
                    SystemMessageType.INFO,
                )
                break

        self.app.call_from_thread(cleanup)

        if not worker.is_cancelled:
            self.is_working = False


def run_cli():
    app = RagApp()
    app.run()


if __name__ == "__main__":
    run_cli()
