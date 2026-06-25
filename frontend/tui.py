from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input, Markdown, Static
from textual.containers import VerticalScroll, Horizontal
from textual.validation import Function, Length
from textual import work
from enum import Enum
import backend.rag as rag
import backend.db as db

class Role(Enum):
    AI = "AI"
    USER = "You"
    SYSTEM = "Sys"


class PrompInput(Input):

    def __init__(self, **kwargs):
        super().__init__(
            placeholder = "Ask about your resources...",
            id = "chat-input",
            **kwargs
        )

        self.is_generating = False

    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handles the Enter key being pressed directly inside this widget."""

        # if we are waiting for generation dont send another mesage
        if self.is_generating:
            return

        user_prompt = event.value.strip()

        if not user_prompt:
            return
        
        # clear the input box, after submitting
        self.value = ""


        chat_text_box = self.app.query_one(ChatText)

        chat_text_box.add_message(user_prompt, Role.USER)

        #check if the user input was command or prompt
        if user_prompt.startswith("/"):
            command_output = self.handle_command(user_prompt)
            if command_output:
                chat_text_box.add_message(command_output, Role.SYSTEM)
            else:
                chat_text_box.add_error_message("Invalid command")

        else:
            # call the llm for the generation
            ai_message_widget = ChatMessage("", Role.AI)
            chat_text_box.mount(ai_message_widget)
            chat_text_box.scroll_end(animate=False)

            self.is_generating = True
            self.fetch_ai_response(user_prompt, chat_text_box, ai_message_widget)

    def handle_command(self, user_input: str) -> str:
        match user_input:
            case "/exit":
                self.app.exit()
                return ""
            
            case "/add-resource":
                return ""
            
            case "/remove-resource":
                return ""

            case "/list-resources":
                return ", ".join(db.list_all_uploaded_files())

            case "/history":
                return ""

            case _:
                return ""

    @work(thread=True)
    def fetch_ai_response(self, user_prompt: str, chat_text_box: ChatText, message_widget: ChatMessage) -> None:
        acc_response = ""

        # displat the text as it is being generated
        for chunk in rag.generate_message(user_prompt):
            acc_response += chunk
            self.app.call_from_thread(message_widget.update_text, acc_response)

            self.app.call_from_thread(chat_text_box.scroll_end, animate=False)


        self.is_generating = False    


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
        formatted_text = f"Error: {self.message}"
        yield Static(formatted_text, classes="message-bubble")



class ChatText(VerticalScroll):
    def __init__(self, **kwargs):
        super().__init__(
            id = "chat-text",
            **kwargs
        )

    def add_message(self, message: str, role: Role) -> None:
        new_msg_widget = UserMessage(message) if role == Role.USER else ChatMessage(message, role) 
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
        ("escape", "unfocus_input", "Scroll chat")
        ]

    def compose(self) -> ComposeResult:
        # yield Header()

        yield ChatText()

        yield PrompInput()

        yield Footer(show_command_palette=False)

    def action_toggle_dark(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_focus_input(self) -> None:
        text_input = self.query_one(PrompInput)
        text_input.focus()

    def action_unfocus_input(self) -> None:
        self.set_focus(None)

    def on_mount(self):
        self.add_welcome_text()

    def add_welcome_text(self) -> None:
        try:
            with open('resources/welcome.txt', 'r', encoding='utf-8') as f:
                welcome_text = f.read()

            welcome_label = Static(welcome_text, id="welcome-art")

            self.query_one(ChatText).mount(welcome_label)
        
        except FileNotFoundError:
            error_label = Static("Welcome! (error loading welcome art)")
            self.query_one(ChatText).mount(error_label)


if __name__ == "__main__":
    app = RagApp()
    app.run()