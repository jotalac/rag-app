from textual.app import App, ComposeResult
from textual.widgets import Label, Collapsible
from textual.containers import VerticalScroll

class TestApp(App):
    CSS = """
    .collapsible-label {
        max-height: 10;
        overflow-y: auto;
    }
    """
    def compose(self) -> ComposeResult:
        content = "a\n" * 100
        yield VerticalScroll(
            Collapsible(
                Label(content, classes="collapsible-label"),
                title="Context"
            )
        )

if __name__ == "__main__":
    TestApp().run()
