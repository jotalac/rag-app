from rag_app.backend.database import get_retriever
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from rag_app.backend.config import config
from pathlib import Path
from enum import Enum
from langchain_core.prompts import PromptTemplate
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.document_loaders import WebBaseLoader
import asyncio
from fake_useragent import UserAgent

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

_contextualize_q_system_prompt = """
Rewrite the last user message so it can be understood without the previous conversation.

Do not answer it.

Return only the rewritten question.
"""

# _contextualize_q_prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", _contextualize_q_system_prompt),
#         MessagesPlaceholder("chat_history"),
#         ("human", "{input}"),
#     ]
# )
_contextualize_q_prompt = PromptTemplate.from_template("""Previous conversation:

{chat_history}

Last user message:
{input}

Rewrite the last user message into a standalone question.

Do not answer.

Rewritten question:""")


_qa_system_prompt = """You are a helpful assistant. Answer the user's question using ONLY the provided context below.
If the context doesn't contain the answer, say "I cannot find that information in the uploaded documents. 
Generate output heavily formatted in markdown for nicer visuals."


Context:
{context}"""


_qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _qa_system_prompt),
        ("human", "{input}"),
    ]
)

_web_search = DuckDuckGoSearchAPIWrapper()


def manage_history_window():
    global _chat_history

    # question and answer
    max_messages = 2 * MAX_HISTORY_LENGTH

    # if there are too many messages, delete the old ones
    if len(_chat_history) > max_messages:
        _chat_history = _chat_history[-max_messages:]


def add_message_to_history(human_message: str, ai_message: str):
    _chat_history.append(HumanMessage(human_message))
    _chat_history.append(AIMessage(ai_message))
    manage_history_window()


def format_docs(docs: list[Document]) -> str:
    return_string = "\n\n".join(doc.page_content for doc in docs)
    print(return_string)
    return "\n\n".join(doc.page_content for doc in docs)


def get_context_docs_names(docs: list[Document], is_remote: bool) -> set[str]:
    all_referenced_files = set()
    for doc in docs:
        source_path = doc.metadata.get("source")
        if source_path:
            all_referenced_files.add(
                str(Path(source_path).relative_to(config.resources_dir))
                if not is_remote
                else source_path
            )

    return all_referenced_files


async def get_docs_context(user_prompt: str) -> list[Document]:
    if not _chat_history or not config.use_chat_history:
        query = user_prompt
    else:
        question_rewriter = (
            _contextualize_q_prompt
            | config.llm.with_config(configurable={"temperature": 0})
            | StrOutputParser()
        )

        query = await question_rewriter.ainvoke(
            {"chat_history": _chat_history, "input": user_prompt}
        )

    print(f"`Message for the docs: {query}`\n")

    return await get_retriever().ainvoke(query)


async def get_web_context(user_prompt: str) -> list[Document]:
    search_results = _web_search.results(user_prompt, max_results=3)

    urls_to_scrape = []
    fallback_docs = []

    for result in search_results:
        if "link" in result:
            urls_to_scrape.append(result["link"])

            fallback_docs.append(
                Document(
                    page_content=result["snippet"],
                    metadata={"source": result["link"], "title": result["title"]},
                )
            )

    if not urls_to_scrape:
        return []

    print(f"Scraping URLs: {urls_to_scrape}")

    try:
        # create fake user agent for the search
        ua = UserAgent()
        random_header = ua.random

        loader = WebBaseLoader(
            web_paths=urls_to_scrape,
            header_template={
                "User-Agent": random_header,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )

        scraped_docs = await asyncio.to_thread(loader.load)

        web_docs = []
        for i, doc in enumerate(scraped_docs):
            clean_text = " ".join(doc.page_content.split())
            doc.page_content = clean_text[:3000]
            doc.metadata["source"] = urls_to_scrape[i]
            web_docs.append(doc)

        return web_docs

    except Exception as e:
        print(f"Web scraping failed, falling back to snippets: {e}")
        return fallback_docs


async def generate_message(user_prompt: str):
    try:
        docs = await get_docs_context(user_prompt)
        used_web_search = False

        if not docs:
            # no documents were found and web search is disabled
            if not config.use_web_search:
                response = "I couldn't find any specific information in your documents related to that query. (web search is disabled)"
                if config.use_chat_history:
                    add_message_to_history(user_prompt, response)

                yield (AIMessageType.TEXT, response)
                return

            # do the web search
            yield (
                AIMessageType.TEXT,
                "*🌐 No local results, doing web search...*\n\n",
            )
            docs = await get_web_context(user_prompt)
            used_web_search = True

        context_string = format_docs(docs)

        yield (AIMessageType.DOC_NAMES, get_context_docs_names(docs, used_web_search))
        yield (AIMessageType.CONTEXT_STRING, context_string)

        answer_generator = _qa_prompt | config.llm | StrOutputParser()

        full_answer = ""

        async for chunk in answer_generator.astream(
            {
                "context": context_string,
                "input": user_prompt,
            }
        ):
            full_answer += chunk
            yield (AIMessageType.TEXT, chunk)

        _chat_history.append(HumanMessage(user_prompt))
        _chat_history.append(AIMessage(full_answer))
        manage_history_window()

    except Exception as e:
        print(e)


def clear_chat_history():
    global _chat_history
    _chat_history = []
