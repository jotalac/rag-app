from textual.widgets import Markdown


class StreamingMarkdown(Markdown):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selection_locked = False

    @property
    def allow_select(self) -> bool:
        if self._selection_locked:
            return False
        return super().allow_select

    def lock_selection(self, locked: bool) -> None:
        self._selection_locked = locked
