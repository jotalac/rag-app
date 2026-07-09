from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import OptionList, Label
from textual.containers import Vertical


class ThemeMenu(ModalScreen):
    """A floating popup menu to select themes."""

    CSS_PATH = "../styles/style_theme_modal.tcss"

    BINDINGS = [
        ("escape", "close_modal", "Close modal"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="theme-dialog"):
            yield Label("Select Theme", classes="theme-menu-title")
            yield OptionList(id="theme-list")

    def on_mount(self) -> None:
        from textual.widgets.option_list import Option

        available_themes = list(self.app.available_themes.keys())
        theme_list = self.query_one("#theme-list", OptionList)

        options = []
        for theme in available_themes:
            if theme == self.app.theme:
                options.append(Option(f"  [b $success]{theme} (active)[/]", id=theme))
            else:
                options.append(Option(f"  {theme}", id=theme))

        theme_list.add_options(options)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id is not None:
            self.app.theme = event.option.id
        self.dismiss()

    def action_close_modal(self) -> None:
        self.dismiss()
