from rag_app.backend.database import get_retriever
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from rag_app.backend.config import config
from pathlib import Path
from enum import Enum

# llm = ChatGoogleGenerativeAI(
#     model="gemini-3.5-flash",
#     api_key="...",
# )


class AIMessageType(Enum):
    TEXT = "message"
    DOC_NAMES = "doc_names"
    CONTEXT_STRING = "context_string"


# adding history context to the llm
_chat_history: list[HumanMessage | AIMessage] = []
MAX_HISTORY_LENGTH = 5

_contextualize_q_system_prompt = """Given a chat history and the latest user question, rewrite the user's question so it is a standalone question that can be understood without the chat history.
CRITICAL: You MUST replace any pronouns (it, they, this, etc.) or implicit references (like "i" mistakenly used for "it") with the specific noun or topic from the chat history.
Do NOT answer the question. ONLY output the rewritten question."""

_contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _contextualize_q_system_prompt),
        (
            "human", 
            "Chat History:\nHuman: What is a log widget?\nAI: It is a widget.\n\nLatest Question: give me code for it\n\nStandalone Question:"
        ),
        ("assistant", "Give me code for the log widget."),
        (
            "human", 
            "Chat History:\nHuman: What is Ktor?\nAI: Ktor is a framework.\n\nLatest Question: can i be used for web server\n\nStandalone Question:"
        ),
        ("assistant", "Can Ktor be used as a web server?"),
        (
            "human",
            "Chat History:\n{chat_history_str}\n\nLatest Question: {input}\n\nStandalone Question:",
        ),
    ]
)

_qa_system_prompt = """You are a helpful assistant. Answer the user's question using ONLY the provided context below.
If the context doesn't contain the answer, say "I cannot find that information in the uploaded documents. 
Generate output formatted in markdown for nicer visuals."


Context:
{context}"""


_qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)


def manage_history_window():
    global _chat_history

    # question and answer
    max_messages = 2 * MAX_HISTORY_LENGTH

    # if there are too many messages, delete the old ones
    if len(_chat_history) > max_messages:
        _chat_history = _chat_history[-max_messages:]


def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(doc.page_content for doc in docs)


def get_context_docs_names(docs: list[Document]) -> set[str]:
    all_referenced_files = set()
    for doc in docs:
        source_path = doc.metadata.get("source")
        if source_path:
            all_referenced_files.add(
                str(Path(source_path).relative_to(config.resources_dir))
            )

    return all_referenced_files


async def get_docs_context(user_prompt: str) -> list[Document]:
    question_rewriter = _contextualize_q_prompt | config.llm | StrOutputParser()

    chat_history_str = "\n".join(
        [
            (
                f"Human: {msg.content}"
                if isinstance(msg, HumanMessage)
                else f"AI: {msg.content}"
            )
            for msg in _chat_history
        ]
    )

    question_for_docs = await question_rewriter.ainvoke(
        {"chat_history_str": chat_history_str, "input": user_prompt}
    )

    print(f"`Message for the docs: {question_for_docs}`\n")

    return await get_retriever().ainvoke(question_for_docs)


async def generate_message(user_prompt: str):
    try:
        answer_generator = _qa_prompt | config.llm | StrOutputParser()

        docs = await get_docs_context(user_prompt)
        context_string = format_docs(docs)

        # later there will be some setting to check if the user want to generate messages even when nothing was found in the rag
        if not context_string:
            # context_string = """
            # No data was found with the RAG, nothing in the saved documents,
            # so generate the best answer you can without the resouces,
            # or just answer that you dont know.
            # """
            yield (
                AIMessageType.TEXT,
                "I couldn't find any specific information in your documents related to that query",
            )
            return

        # list the referenced resources
        print(context_string)
        yield (AIMessageType.DOC_NAMES, get_context_docs_names(docs))
        yield (AIMessageType.CONTEXT_STRING, context_string)

        full_answer = ""

        async for chunk in answer_generator.astream(
            {
                "context": context_string,
                "chat_history": _chat_history,
                "input": user_prompt,
            }
        ):
            if not chunk:
                return

            full_answer += chunk
            yield (AIMessageType.TEXT, chunk)

        # add the new response to the history
        _chat_history.append(HumanMessage(user_prompt))
        _chat_history.append(AIMessage(full_answer))

        manage_history_window()

    except Exception as e:
        print(e)


def clear_chat_history():
    global _chat_history
    _chat_history = []
