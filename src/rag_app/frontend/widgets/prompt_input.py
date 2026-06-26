from textual.widgets import Input
from textual.suggester import SuggestFromList
from textual.message import Message
from rag_app.frontend.command_handler import Commands


class PromptInput(Input):

    BINDINGS = [
        ("tab", "apply_autocomplete", "Apply autocomplete"),
        ("up", "browse_history_up", "Previous command"),
        ("down", "browse_history_down", "Next command"),
    ]

    def __init__(self, **kwargs):
        super().__init__(
            placeholder="Ask about your resources...",
            suggester=SuggestFromList(
                [c.value for c in Commands], case_sensitive=False
            ),
            id="chat-input",
            **kwargs,
        )

        self.command_history: list[str] = []
        self.history_index = 0
        self.is_generating = False

    class PromptSubmitted(Message):
        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_prompt = self.value.strip()

        if not user_prompt:
            return

        self.post_message(self.PromptSubmitted(user_prompt))

    # actions
    def action_apply_autocomplete(self) -> None:
        self.action_cursor_right()

    def action_browse_history_up(self) -> None:
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.value = self.command_history[self.history_index]
            self.action_end()

    def action_browse_history_down(self) -> None:
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.value = self.command_history[self.history_index]
            self.action_end()
        elif self.history_index == len(self.command_history) - 1:
            self.history_index += 1
            self.value = ""
