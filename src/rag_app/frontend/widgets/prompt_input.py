from textual.widgets import Input
from textual import work
from rag_app.frontend.widgets.chat_widgets import ChatMessage, ChatText, Role
import rag_app.backend.db as db
from rag_app.backend.rag import generate_message, clear_chat_history
from enum import Enum


class PromptInput(Input):

    def __init__(self, **kwargs):
        super().__init__(
            placeholder="Ask about your resources...", id="chat-input", **kwargs
        )

        self.is_generating = False

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handles the Enter key being pressed directly inside this widget."""

        # if we are waiting for generation dont send another message
        if self.is_generating:
            return

        user_prompt = event.value.strip()

        if not user_prompt:
            return

        # clear the input box, after submitting
        self.value = ""

        chat_text_box = self.app.query_one(ChatText)

        chat_text_box.add_message(user_prompt, Role.USER)

        # check if the user input was command or prompt
        if user_prompt.startswith("/"):

            if user_prompt == "/exit":
                self.app.exit()
                return

            command_output = self.handle_command(user_prompt)
            if command_output.startswith("Error"):
                chat_text_box.add_error_message(command_output)
            else:
                chat_text_box.add_message(command_output, Role.SYSTEM)

        else:
            # call the llm for the generation
            ai_message_widget = ChatMessage("", Role.AI)
            chat_text_box.mount(ai_message_widget)
            chat_text_box.scroll_end(animate=False)

            self.is_generating = True
            self.fetch_ai_response(user_prompt, chat_text_box, ai_message_widget)

    def handle_command(self, user_input: str) -> str:
        parts = user_input.split(maxsplit=1)

        command = parts[0]

        arg = parts[1].strip() if len(parts) > 1 else None

        match command:
            case "/add-resource":
                if not arg:
                    return "Error: No filename provided"

                db.add_resource(arg)
                return "Resource added successfully!"

            case "/remove-resource":
                if not arg:
                    return "Error: No filename provided"

                if db.remove_resource(arg):
                    return "Resource deleted successfully!"
                else:
                    return "Error: Deleting resource failed"

            case "/list-resources":
                return ", ".join(db.list_all_uploaded_files())

            case "/history":
                return "Error: history not implemented yet"

            case _:
                return "Error: Invalid command"

    @work(thread=True)
    def fetch_ai_response(
        self, user_prompt: str, chat_text_box: ChatText, message_widget: ChatMessage
    ) -> None:
        acc_response = ""

        # display the text as it is being generated
        for chunk in generate_message(user_prompt):
            acc_response += chunk
            self.app.call_from_thread(message_widget.update_text, acc_response)

            self.app.call_from_thread(chat_text_box.scroll_end, animate=False)

        self.is_generating = False
