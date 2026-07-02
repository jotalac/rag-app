from typing import TYPE_CHECKING
from rag_app.frontend.command_handler import Commands
from rag_app.frontend.widgets.chat_widgets import ChatText, AIMessage

if TYPE_CHECKING:
    from rag_app.main import RagApp


def route_user_input(app: "RagApp", user_prompt: str, chat_text_box: ChatText) -> None:

    # system ui commands
    if user_prompt == Commands.EXIT.value:
        app.exit()
        return

    if user_prompt == Commands.CONFIG.value:
        app.action_open_config()
        return

    if user_prompt == Commands.WORKSPACE.value:
        app.action_open_workspace_menu()
        return

    # backend commands
    if user_prompt.startswith("/"):
        app.is_working = True
        app.active_ai_widget = None
        app.active_worker = app.run_thread_command(user_prompt, chat_text_box)
        return

    # ai generation
    ai_message_widget = AIMessage("Generating response...")
    chat_text_box.mount(ai_message_widget)
    chat_text_box.scroll_end(animate=False)

    app.is_working = True
    app.active_ai_widget = ai_message_widget
    app.active_worker = app.fetch_ai_response(user_prompt, chat_text_box)
