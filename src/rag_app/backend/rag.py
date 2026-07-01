from rag_app.backend.db import get_retriever
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from rag_app.backend.config import config

# llm = ChatGoogleGenerativeAI(
#     model="gemini-3.5-flash",
#     api_key="...",
# )

# adding history context to the llm
_chat_history: list[HumanMessage | AIMessage] = []
MAX_HISTORY_LENGTH = 5

_contextualize_q_system_prompt = """You are not a conversational assistant. You are a strict linguistic text processor.
Your ONLY job is to read the chat history and rewrite the final user question so it is a standalone sentence.
Do not engage in conversation. Do not answer the question. Do not explain yourself. Output NOTHING but the rewritten question.
If the question make sense by it self DO NOT change it.

EXAMPLES:

History: 
Human: What is Python?
AI: Python is a popular programming language.
Question: Is it hard to learn?
Output: Is Python hard to learn?

History: 
Human: What is the capital of France?
AI: Paris.
Question: What is a variable in programming?
Output: What is a variable in programming?

History:
Human: How do I install dependencies?
AI: You can use pip or uv.
Question: Which one is faster?
Output: Which dependency manager is faster, pip or uv?

Now process the following real input.
"""

_contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "Question: {input}\nOutput:"),
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


async def generate_message(user_prompt: str):
    question_rewriter = _contextualize_q_prompt | config.llm | StrOutputParser()
    answer_generator = _qa_prompt | config.llm | StrOutputParser()

    question_for_docs = await question_rewriter.ainvoke(
        {"chat_history": _chat_history, "input": user_prompt}
    )

    print(f"`Message for the docs: {question_for_docs}`\n")

    docs = await get_retriever().ainvoke(question_for_docs)
    context_string = format_docs(docs)

    print(f"`Context string: {context_string}`\n")

    # later there will be some setting to check if the user want to generate messages even when nothing was found in the rag
    if not context_string:
        # context_string = """
        # No data was found with the RAG, nothing in the saved documents,
        # so generate the best answer you can without the resouces,
        # or just answer that you dont know.
        # """
        yield "I couldn't find any specific information in your documents related to that query"
        return

    full_answer = ""

    async for chunk in answer_generator.astream(
        {"context": context_string, "chat_history": _chat_history, "input": user_prompt}
    ):
        if not chunk:
            return

        full_answer += chunk
        yield chunk

    # add the new response to the history
    _chat_history.append(HumanMessage(user_prompt))
    _chat_history.append(AIMessage(full_answer))

    manage_history_window()


def clear_chat_history():
    global _chat_history
    _chat_history = []


# rag_chain = (
#     {"context": db.retriever | format_docs, "question": RunnablePassthrough() }
#     | prompt
#     | llm
#     | StrOutputParser()
# )
