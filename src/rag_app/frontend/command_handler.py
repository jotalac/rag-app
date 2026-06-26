# backend/command_handler.py
from enum import Enum
import rag_app.backend.db as db
from rag_app.backend.rag import clear_chat_history
from rag_app.frontend.widgets.chat_widgets import SystemMessageType


class Commands(Enum):
    ADD_RESOURCES = "/add-resources"
    REMOVE_RESOURCES = "/remove-resources"
    LIST_RESOURCES = "/list-resources"
    CLEAR_HISTORY = "/clear-history"
    EXIT = "/exit"


class CommandHandler:
    @staticmethod
    def handle_command(user_input: str) -> tuple[SystemMessageType, str]:

        parts = user_input.split(maxsplit=1)
        command = parts[0]
        arg = parts[1].strip() if len(parts) > 1 else None

        match command:
            case Commands.ADD_RESOURCES.value:
                if not arg:
                    return (SystemMessageType.ERROR, "No filename provided")

                success = db.add_resource(arg)
                if success:
                    return (SystemMessageType.SUCCESS, "Resource added successfully!")
                else:
                    return (
                        SystemMessageType.ERROR,
                        "Adding resource failed - make sure the file name is valid",
                    )

            case Commands.REMOVE_RESOURCES.value:
                if not arg:
                    return (SystemMessageType.ERROR, "No filename provided")

                if db.remove_resource(arg):
                    return (SystemMessageType.SUCCESS, "Resource deleted successfully!")
                else:
                    return (SystemMessageType.ERROR, "Deleting resource failed")

            case Commands.LIST_RESOURCES.value:
                all_resources = db.list_all_uploaded_files()
                if not all_resources:
                    return (SystemMessageType.INFO, "No documents uploaded")
                else:
                    return (
                        SystemMessageType.INFO,
                        ", ".join(db.list_all_uploaded_files()),
                    )

            case Commands.CLEAR_HISTORY.value:
                clear_chat_history()
                return (SystemMessageType.INFO, "History cleared")

            case _:
                return (SystemMessageType.ERROR, "Invalid command")
