from textual import work
from textual.worker import get_current_worker
import asyncio
from typing import TYPE_CHECKING
from rag_app.frontend.command_handler import Commands, handle_command
from textual.worker import Worker, get_current_worker
from rag_app.backend.rag import generate_message
from rag_app.frontend.widgets.custom_spinner import CustomSpinner
from rag_app.frontend.widgets.chat_widgets import SystemMessageType
from rag_app.frontend.widgets.chat_widgets import AIMessage
from rag_app.frontend.widgets.chat_widgets import ChatText
from textual.app import App

if TYPE_CHECKING:
    from rag_app.main import RagApp


class AppWorkers(App):
    is_working: bool
    active_ai_widget: AIMessage | None

    @work
    async def fetch_ai_response(
        self, user_prompt: str, chat_text_box: ChatText
    ) -> None:
        worker = get_current_worker()
        acc_response = ""

        ai_widget = self.active_ai_widget

        if not ai_widget:
            print("No active AI widget")
            raise ValueError("No active AI widget")

        try:
            # display the text as it is being generated
            async for chunk in generate_message(user_prompt):
                # append the new generated chunk
                acc_response += chunk
                ai_widget.update_text(acc_response)

                chat_text_box.scroll_end(animate=False)

        except asyncio.CancelledError:
            pass
        except Exception:
            # display error message
            chat_text_box.add_ollama_error_message()

            ai_widget.remove()  # type: ignore

        self.is_working = False
        self.active_ai_widget = None

    # Type
    @work(thread=True)
    def run_thread_command(self, user_prompt: str, chat_text_box: ChatText) -> None:
        worker = get_current_worker()

        # add the loader indicator
        loader = CustomSpinner(
            message="Processing request",
            id="cmd-loader",
        )

        def mount_loader():
            if not chat_text_box.query("#cmd-loader"):
                chat_text_box.mount(loader)
                chat_text_box.scroll_end(animate=False)

        def cleanup():
            loaders = chat_text_box.query("#cmd-loader")
            if loaders:
                loaders.remove()
                chat_text_box.scroll_end(animate=False)

        self.call_from_thread(mount_loader)

        try:
            for status, message in handle_command(user_prompt):

                def post_update(s=status, m=message):
                    cleanup()
                    chat_text_box.add_system_message(m, s)  # type: ignore
                    mount_loader()

                self.call_from_thread(post_update)

                # check if the command wasn't canceled
                if worker.is_cancelled:
                    self.call_from_thread(
                        chat_text_box.add_system_message,
                        "Command canceled!",
                        SystemMessageType.INFO,
                    )
                    break
        except Exception as e:
            print(e)
            self.call_from_thread(chat_text_box.add_ollama_error_message)

        self.call_from_thread(cleanup)

        self.is_working = False
