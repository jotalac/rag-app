# backend/command_handler.py
from enum import Enum
import rag_app.backend.db as db
from rag_app.backend.rag import clear_chat_history
from rag_app.frontend.widgets.chat_widgets import SystemMessageType


class Commands(Enum):
    ADD_RESOURCES = "/add-resources"
    ADD_RESOURCES_DIR = "/add-resources-dir"
    REMOVE_RESOURCES = "/remove-resources"
    LIST_RESOURCES = "/list-resources"
    CLEAR_MEMORY = "/clear-memory"
    EXIT = "/exit"


def _add_resource(resource_name: str) -> str:
    if db.add_resource(resource_name):
        return f"✅ Added: {resource_name}\n"
    else:
        return f"❌ Failed to add: {resource_name}\n"


def _handle_add_resources(args: list[str] | None) -> tuple[SystemMessageType, str]:
    if not args:
        return (SystemMessageType.ERROR, "No filename provided")

    output_message = ""
    for resource_file_name in args:
        output_message += _add_resource(resource_file_name)

    return (SystemMessageType.INFO, output_message.strip())


def _handle_add_resources_dir(args: list[str] | None) -> tuple[SystemMessageType, str]:
    if not args:
        return (SystemMessageType.ERROR, "No directory provided")
    if len(args) > 1:
        return (SystemMessageType.ERROR, "You can add only one directory at time.")

    output_message = ""

    dir_name = args[0]
    target_dir = db.DOCUMENT_BASE_DIR / dir_name

    print(target_dir)

    if not target_dir.exists() or not target_dir.is_dir():
        return (SystemMessageType.ERROR, f"❌ Directory not found: {dir_name}.")

    file_found = False

    # go through all file recursively in the dir
    for file_path in target_dir.rglob("*"):
        if file_path.is_file():
            file_found = True

        # get relative path
        file_relative_path = str(file_path.relative_to(db.DOCUMENT_BASE_DIR))

        output_message += _add_resource(file_relative_path)

    if not file_found:
        return (SystemMessageType.ERROR, f"No files found in directory: {dir_name}")
    else:
        return (SystemMessageType.INFO, output_message.strip())


def _handle_remove_resources(args: list[str] | None) -> tuple[SystemMessageType, str]:
    if not args:
        return (SystemMessageType.ERROR, "No filename provided")

    output_message = ""
    for resource_file in args:
        if db.remove_resource(resource_file):
            output_message += f"🗑️ Deleted: {resource_file}\n"
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
    Commands.ADD_RESOURCES_DIR.value: _handle_add_resources_dir,
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
