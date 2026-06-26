import src.rag_app.backend.db as db
import src.rag_app.backend.rag as rag
from langchain_core.messages import HumanMessage, AIMessage
import logging

logging.getLogger("langchain_core.vectorsstores").setLevel(logging.ERROR)


def main():
    # db.add_resource("DSA.pdf")

    chat_history: list[HumanMessage | AIMessage] = []

    while True:
        print("Enter your prompt:")
        user_prompt = input().strip()

        if user_prompt.startswith("/"):
            match user_prompt:
                case "/exit":
                    return

                case "/add-resource":
                    resource_name = input(
                        "Enter file name (file the /documents folder): "
                    ).strip()
                    if db.add_resource(resource_name):
                        print("Resource added succesfully\n")
                    else:
                        print("Error adding resource")
                    continue

                case "/remove-resource":
                    resource_name = input(
                        "Enter file name (file the /documents folder): "
                    ).strip()
                    if db.remove_resource(resource_name):
                        print("Resource delete successfully\n")
                    else:
                        print("Error deleting resources\n")
                    continue

                case "/list-resources":
                    all_saved_resources = db.list_all_uploaded_files()
                    print(
                        "No resources saved"
                        if len(all_saved_resources) == 0
                        else all_saved_resources
                    )
                    print()
                    continue

                case "/history":
                    print(chat_history)
                    continue

                case _:
                    print("Invalid command\n")
                    continue

        # response = rag.rag_chain.invoke(user_prompt)

        question_for_docs = rag._question_rewriter.invoke(
            {"chat_history": chat_history, "input": user_prompt}
        )

        print("Generated promp for docs: \n" + question_for_docs)

        docs = db.retriever.invoke(question_for_docs)
        context_string = rag.format_docs(docs)

        if not context_string:
            print("No relevant data availible.\n")
            continue

        full_answer = ""
        # get responses in chunks
        print("AI response: \n")
        for chunk in rag._answer_generator.stream(
            {
                "context": context_string,
                "chat_history": chat_history,
                "input": user_prompt,
            }
        ):
            print(chunk, end="", flush=True)

            full_answer += chunk

        print("\n\n")

        # add the new response to the history
        chat_history.append(HumanMessage(user_prompt))
        chat_history.append(AIMessage(full_answer))


if __name__ == "__main__":
    main()
