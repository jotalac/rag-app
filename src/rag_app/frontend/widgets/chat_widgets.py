from textual.app import ComposeResult
from textual.widgets import Markdown, Static
from textual.containers import VerticalScroll, Horizontal
from enum import Enum


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
