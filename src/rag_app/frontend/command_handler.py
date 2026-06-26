# backend/command_handler.py
from enum import Enum
import rag_app.backend.db as db
from rag_app.backend.rag import clear_chat_history
from rag_app.frontend.widgets.chat_widgets import SystemMessageType


class Commands(Enum):
    ADD_RESOURCES = "/add-resources"
    REMOVE_RESOURCES = "/remove-resources"
    LIST_RESOURCES = "/list-resources"
    CLEAR_MEMORY = "/clear-memory"
    EXIT = "/exit"


def _handle_add_resources(args: list[str] | None) -> tuple[SystemMessageType, str]:
    if not args:
        return (SystemMessageType.ERROR, "No filename provided")

    output_message = ""
    for resource_file in args:
        if db.add_resource(resource_file):
            output_message += f"✅ Added: {resource_file}\n"
        else:
            output_message += f"❌ Failed to add: {resource_file}\n"
    return (SystemMessageType.INFO, output_message.strip())


def _handle_remove_resources(args: list[str] | None) -> tuple[SystemMessageType, str]:
    if not args:
        return (SystemMessageType.ERROR, "No filename provided")

    output_message = ""
    for resource_file in args:
        if db.remove_resource(resource_file):
            output_message += f"✅ Deleted: {resource_file}\n"
        else:
            output_message += f"❌ Failed to delete: {resource_file}\n"
    return (SystemMessageType.INFO, output_message.strip())


def _handle_list_resources(args: list[str] | None) -> tuple[SystemMessageType, str]:
    all_resources = db.list_all_uploaded_files()
    if not all_resources:
        return (SystemMessageType.INFO, "No documents uploaded")
    return (SystemMessageType.INFO, "".join([f"📁 {r}\n" for r in all_resources]))


def _handle_clear_history(args: list[str] | None) -> tuple[SystemMessageType, str]:
    clear_chat_history()
    return (SystemMessageType.INFO, "⏱️ Chat memory cleared")


COMMAND_REGISTRY = {
    Commands.ADD_RESOURCES.value: _handle_add_resources,
    Commands.REMOVE_RESOURCES.value: _handle_remove_resources,
    Commands.LIST_RESOURCES.value: _handle_list_resources,
    Commands.CLEAR_MEMORY.value: _handle_clear_history,
}


def handle_command(user_input: str) -> tuple[SystemMessageType, str]:
    parts = user_input.split()
    command = parts[0]
    args = parts[1::] if len(parts) > 1 else None

    handler_function = COMMAND_REGISTRY.get(command)

    if handler_function is not None:
        return handler_function(args)
    else:
        return (SystemMessageType.ERROR, "Invalid command")
