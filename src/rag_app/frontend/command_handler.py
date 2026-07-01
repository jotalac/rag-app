# backend/command_handler.py
from enum import Enum
from rag_app.backend.config import config
import rag_app.backend.db as db
from rag_app.backend.rag import clear_chat_history
from rag_app.frontend.widgets.chat_widgets import SystemMessageType
import shlex


class Commands(Enum):
    ADD_RESOURCES = "/add-resources"
    ADD_RESOURCES_DIR = "/add-resources-dir"
    REMOVE_RESOURCES = "/remove-resources"
    REMOVE_RESOURCES_DIR = "/remove-resources-dir"
    REMOVE_RESOURCES_ALL = "/remove-resources-all"
    LIST_RESOURCES = "/list-resources"
    CLEAR_MEMORY = "/clear-memory"
    CONFIG = "/config"
    HELP = "/help"
    EXIT = "/exit"


def _add_resource(resource_name: str) -> tuple[SystemMessageType, str]:
    success, message = db.add_resource(resource_name)
    if success:
        return (SystemMessageType.SUCCESS, f"✅ Added **{resource_name}** - {message}")
    else:
        return (
            SystemMessageType.ERROR,
            f"❌ Failed to add **{resource_name}** - {message}",
        )


def _remove_resource(resource_name: str) -> str:
    if db.remove_resource(resource_name):
        return f"- 🗑️ Removed: {resource_name} \n"
    else:
        return f"- ❌ Failed to delete: {resource_name} \n"


def _handle_add_resources(args: list[str] | None):
    if not args:
        yield (SystemMessageType.ERROR, "No filename provided")
        return

    for resource_file_name in args:
        yield _add_resource(resource_file_name)


def _handle_add_resources_dir(args: list[str] | None):
    if not args:
        yield (SystemMessageType.ERROR, "No directory name provided")
        return
    if len(args) > 1:
        yield (SystemMessageType.ERROR, "You can add only one directory at time.")
        return

    dir_name = args[0]
    target_dir = config.resources_dir / dir_name

    print(target_dir)

    if not target_dir.exists() or not target_dir.is_dir():
        yield (SystemMessageType.ERROR, f"Directory not found: {dir_name}")
        return

    all_files = [f for f in target_dir.rglob("*") if f.is_file()]
    file_count = len(all_files)

    if file_count == 0:
        yield (SystemMessageType.ERROR, f"No files found in directory: {dir_name}")
        return

    yield (SystemMessageType.INFO, f"🔍 Found {file_count} files. Starting indexing...")

    # go through all file recursively in the dir
    for current_file_index, file_path in enumerate(all_files):

        # get relative path
        file_relative_path = str(file_path.relative_to(config.resources_dir))

        yield (
            SystemMessageType.INFO,
            f"[{current_file_index + 1}/{file_count}] - ⏳ Processing: {file_relative_path}",
        )

        add_result = _add_resource(file_relative_path)

        yield (
            SystemMessageType.INFO,
            f"[{current_file_index + 1 }/{file_count}] - {add_result[1]}",
        )

    yield (SystemMessageType.INFO, "Directory processing complete!")


def _handle_remove_resources(args: list[str] | None):
    if not args:
        yield (SystemMessageType.ERROR, "No filename provided")
        return

    output_string = ""
    for resource_file in args:
        output_string += _remove_resource(resource_file)

    yield (SystemMessageType.INFO, output_string)


def _handle_remove_resources_dir(args: list[str] | None):
    if not args:
        yield (SystemMessageType.ERROR, "No directory name provided")
        return
    if len(args) > 1:
        yield (SystemMessageType.ERROR, "You can remove only one directory at time.")
        return

    dir_name = args[0]

    remove_result = db.remove_resources_dir(dir_name)

    if remove_result:
        yield (
            SystemMessageType.INFO,
            f"🗑️ All resources from directory: **{dir_name}** were removed",
        )
    else:
        yield (
            SystemMessageType.INFO,
            f"❌ Failed to remove resources from directory: **{dir_name}**",
        )


def _handle_remove_resources_all(args: list[str] | None):
    db.remove_all_resources()
    yield (SystemMessageType.INFO, "🗑️ All resources were removed")


def _handle_list_resources(args: list[str] | None):
    all_resources = db.list_all_uploaded_files()
    if not all_resources:
        yield (SystemMessageType.INFO, "No documents uploaded")
    else:
        yield (SystemMessageType.INFO, "\n".join([f"- 📁 {r}" for r in all_resources]))


def _handle_clear_history(args: list[str] | None):
    clear_chat_history()
    yield (SystemMessageType.INFO, "⏱️ Chat memory cleared")


def _handle_help(args: list[str] | None):
    help_text = """
# RAG APP
Ask questions about your resources.
        
## Available Commands:

_*all file paths are relative to the **resources directory**_



**`/config`**
Open application config.

### Adding resources:

**`/add-resources [file1] [file2]...`**
Embeds specific files into the database.


**`/add-resources-dir [folder]`**
Recursively embeds all files within a specific folder.

### Removing resources:

**`/remove-resources [file1] [file2]...`**
Deletes specific files from the database.


**`/remove-resources-dir [folder]...`**
Recursively deletes all files within a specific folder.


**`/remove-resources-all`**
Wipes the entire vector database.

### Other:

**`/list-resources`**
Displays a list of all currently indexed files.


**`/clear-memory`**
Wipes the conversational chat history so the previous messages will be forgotten.


**`/help`**
Displays this help message.


**`/exit`**
Closes the application.
"""
    yield (SystemMessageType.INFO, help_text.strip())


COMMAND_REGISTRY = {
    Commands.ADD_RESOURCES.value: _handle_add_resources,
    Commands.ADD_RESOURCES_DIR.value: _handle_add_resources_dir,
    Commands.REMOVE_RESOURCES.value: _handle_remove_resources,
    Commands.REMOVE_RESOURCES_DIR.value: _handle_remove_resources_dir,
    Commands.REMOVE_RESOURCES_ALL.value: _handle_remove_resources_all,
    Commands.LIST_RESOURCES.value: _handle_list_resources,
    Commands.HELP.value: _handle_help,
    Commands.CLEAR_MEMORY.value: _handle_clear_history,
}


def handle_command(user_input: str):
    try:
        parts = shlex.split(user_input)

    except ValueError as e:
        print(f"invalid command syntax {e}")
        yield (SystemMessageType.ERROR, "Invalid command syntax")
        return

    if not parts:
        return

    command = parts[0]
    args = parts[1::] if len(parts) > 1 else None

    handler_function = COMMAND_REGISTRY.get(command)

    if handler_function is not None:
        yield from handler_function(args)
    else:
        yield (SystemMessageType.ERROR, "Invalid command")
