from textual.widgets import Static
from textual.reactive import reactive


class CustomSpinner(Static):

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    step = reactive(0)

    def __init__(self, message: str = "Processing", **kwargs):
        super().__init__(**kwargs)
        self.message = message

    def on_mount(self) -> None:
        self.spinner_time = self.set_interval(0.1, self.increment_step)

    def increment_step(self):
        self.step = (self.step + 1) % len(self.FRAMES)

    def watch_step(self, step: int) -> None:
        self.update(f"{self.FRAMES[step]} {self.message}")
