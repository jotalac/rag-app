from textual.app import ComposeResult
from textual.events import Mount
from textual.widgets import Markdown, Static, Collapsible, Label
from textual.containers import VerticalScroll, Vertical, Horizontal
from enum import Enum
from pathlib import Path
from rag_app.backend.config import config


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
        with Vertical(classes="message-bubble") as bubble:
            self.bubble = bubble
            formatted_text = f"**{Role.AI.value}**: \n{self.message}"
            self.md_widget = Markdown(formatted_text)
            yield self.md_widget

    def update_text(self, new_text: str) -> None:
        self.message = new_text
        formatted_text = f"**{Role.AI.value}**: \n\n{self.message}"
        self.md_widget.update(formatted_text)

    def add_collapsible_content(self, title: str, content: str) -> None:
        from rich.text import Text

        text_obj = Text(content, style="dim")
        collapsible_widget = Collapsible(
            Label(text_obj, classes="collapsible-label"),
            collapsed=True,
            title=title,
            classes="source-collapsible",
        )
        self.bubble.mount(collapsible_widget, before=self.md_widget)


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
        formatted_text = f"**{self.message_type.value}**: \n\n{self.message}"
        yield Markdown(formatted_text, classes="message-bubble")


class WelcomeMessage(Vertical):
    def __init__(self, **kwargs):
        super().__init__(id="welcome-message-cont", **kwargs)

    def on_mount(self) -> None:
        self.add_welcome_ascii_art()
        self.add_welcome_message()

    def add_welcome_ascii_art(self):
        # add image
        current_dir = Path(__file__).parent.parent.parent
        file_path = current_dir / "resources" / "welcome.txt"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                welcome_text = f.read()

            welcome_label = Static(welcome_text, id="welcome-art")

            self.mount(welcome_label)

        except FileNotFoundError as e:
            print(e)
            error_label = Static("Welcome! (error loading welcome art)")
            self.mount(error_label)

    def add_welcome_message(self):
        # We use a Markdown table to get that clean, key-value aesthetic
        welcome_md = f"""
# Rag App - generation with context

| Configuration | Current Value |
| :--- | :--- |
| **Workspace** | `{config.workspace_name}` |
| **Resources Directory** | `{config.resources_dir}` |
| **Generation Model** | `{config.gen_model}` |
| **Embedding Model** | `{config.embed_model}` |

*Type `/help` to see available commands or simply ask a question.*
        """
        message_container = Markdown(welcome_md, id="welcome-text")
        self.mount(message_container)


class ChatText(VerticalScroll):
    def __init__(self, **kwargs):
        super().__init__(id="chat-text", **kwargs)

    def add_ai_message(self, message: str) -> None:
        new_msg_widget = AIMessage(message)
        self.mount(new_msg_widget)

        self.remove_old_messages()

    def add_user_message(self, message: str) -> None:
        new_msg_widget = UserMessage(message)
        self.mount(new_msg_widget)

        self.remove_old_messages()

    def add_system_message(self, message: str, message_type: SystemMessageType) -> None:
        self.mount(SystemMessage(message, message_type))

        self.remove_old_messages()

    def add_ollama_error_message(self) -> None:
        self.add_system_message(
            message="**Ollama error**  \n\n Make sure:\n- Ollama is running: `ollama serve`\n- You have downloaded the configured model: `ollama pull ...`",
            message_type=SystemMessageType.ERROR,
        )

        self.remove_old_messages()

    def remove_old_messages(self):
        if len(self.children) > 30:
            self.children[0].remove()

        self.scroll_end(animate=False)
