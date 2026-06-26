from textual.app import App, ComposeResult
from textual.widgets import Footer, Markdown, Static
from textual.containers import VerticalScroll, Horizontal
from enum import Enum
from rag_app.frontend.widgets.prompt_input import PromptInput


class Role(Enum):
    AI = "AI"
    USER = "You"
    SYSTEM = "Sys"


class ChatMessage(Horizontal):
    def __init__(self, message: str, role: Role, **kwargs):
        super().__init__(classes=f"message-row {Role.AI.name.lower()}", **kwargs)
        self.message = message
        self.role = role

    def compose(self) -> ComposeResult:
        formatted_text = f"**{self.role.value.upper()}**: \n{self.message}"
        self.md_widget = Markdown(formatted_text, classes="message-bubble")
        yield self.md_widget

    def update_text(self, new_text: str) -> None:
        self.message = new_text
        formatted_text = f"**{self.role.value.upper()}**: \n{self.message}"
        self.md_widget.update(formatted_text)


class UserMessage(Horizontal):
    def __init__(self, message: str, **kwargs):
        super().__init__(classes=f"message-row {Role.USER.name.lower()}", **kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        formatted_text = f"[b]{Role.USER.value.upper()}[/b]: {self.message}"
        yield Static(formatted_text, classes="message-bubble")


class ErrorMessage(Horizontal):
    def __init__(self, message: str, **kwargs):
        super().__init__(classes="message-row error", **kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        formatted_text = self.message
        yield Static(formatted_text, classes="message-bubble")


class ChatText(VerticalScroll):
    def __init__(self, **kwargs):
        super().__init__(id="chat-text", **kwargs)

    def add_message(self, message: str, role: Role) -> None:
        new_msg_widget = (
            UserMessage(message) if role == Role.USER else ChatMessage(message, role)
        )
        self.mount(new_msg_widget)
        self.scroll_end(animate=False)

    def add_error_message(self, message: str) -> None:
        self.mount(ErrorMessage(message))
        self.scroll_end(animate=False)


class RagApp(App):

    CSS_PATH = "tui.tcss"

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("/", "focus_input", "Type Message"),
        ("escape", "unfocus_input", "Scroll chat"),
    ]

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

    def on_mount(self):
        self.add_welcome_text()

    def add_welcome_text(self) -> None:
        try:
            with open("resources/welcome.txt", "r", encoding="utf-8") as f:
                welcome_text = f.read()

            welcome_label = Static(welcome_text, id="welcome-art")

            self.query_one(ChatText).mount(welcome_label)

        except FileNotFoundError:
            error_label = Static("Welcome! (error loading welcome art)")
            self.query_one(ChatText).mount(error_label)


if __name__ == "__main__":
    app = RagApp()
    app.run()
