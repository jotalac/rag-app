from textual.app import ComposeResult
from textual.widgets import Markdown, Static
from textual.containers import VerticalScroll, Horizontal
from enum import Enum


class Role(Enum):
    AI = "AI"
    USER = "You"


class SystemMessageType(Enum):
    ERROR = "Error"
    INFO = "Info"
    SUCCESS = "Success"


class AIMessage(Horizontal):
    def __init__(self, message: str, **kwargs):
        super().__init__(classes=f"message-row {Role.AI.name.lower()}", **kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        formatted_text = f"**{Role.AI.value}**: \n{self.message}"
        self.md_widget = Markdown(formatted_text, classes="message-bubble")
        yield self.md_widget

    def update_text(self, new_text: str) -> None:
        self.message = new_text
        formatted_text = f"**{Role.AI.value}**: \n{self.message}"
        self.md_widget.update(formatted_text)


class UserMessage(Horizontal):
    def __init__(self, message: str, **kwargs):
        super().__init__(classes=f"message-row {Role.USER.name.lower()}", **kwargs)
        self.message = message

    def compose(self) -> ComposeResult:
        formatted_text = f"[b]{Role.USER.value.upper()}[/b]: {self.message}"
        yield Static(formatted_text, classes="message-bubble")


class SystemMessage(Horizontal):
    def __init__(self, message: str, message_type: SystemMessageType, **kwargs):
        super().__init__(classes=f"message-row {message_type.name.lower()}", **kwargs)
        self.message = message
        self.message_type = message_type

    def compose(self) -> ComposeResult:
        formatted_text = f"[b]{self.message_type.value}[/b]:\n\n{self.message}"
        yield Static(formatted_text, classes="message-bubble")


class ChatText(VerticalScroll):
    def __init__(self, **kwargs):
        super().__init__(id="chat-text", **kwargs)

    def add_ai_message(self, message: str) -> None:
        new_msg_widget = AIMessage(message)
        self.mount(new_msg_widget)
        self.scroll_end(animate=False)

    def add_user_message(self, message: str) -> None:
        new_msg_widget = UserMessage(message)
        self.mount(new_msg_widget)
        self.scroll_end(animate=False)

    def add_system_message(self, message: str, message_type: SystemMessageType) -> None:
        self.mount(SystemMessage(message, message_type))
        self.scroll_end(animate=False)
