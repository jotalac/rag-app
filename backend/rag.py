from backend import db
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

llm = ChatOllama(model="llama3.2:3b", temperature=0)

# llm = ChatGoogleGenerativeAI(
#     model="gemini-3.5-flash",
#     api_key="AIzaSyBNh3oQYeMzrwcpkERsXY9pWXgYyQv8dUI",
# )

chat_history: list[HumanMessage | AIMessage] = []

contextualize_q_system_prompt = """You are a rigid, robotic question rewriter. Your ONLY job is to look at the chat history and the user's latest question.
If the latest question contains pronouns (it, they, he, she) or refers to a previous topic, rewrite it into a standalone question.
If the question already makes sense on its own, return the exact original question.

CRITICAL RULES:
- Output ONLY the rewritten question.
- Do NOT answer the question.
- Do NOT apologize.
- Do NOT say "Here is the rewritten question".
- Provide absolutely no conversational text."""

contextualize_q_prompt = ChatPromptTemplate.from_messages([
    ("system", contextualize_q_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

question_rewriter = contextualize_q_prompt | llm | StrOutputParser()

qa_system_prompt = """You are a helpful assistant. Answer the user's question using ONLY the provided context below.
If the context doesn't contain the answer, say "I cannot find that information in the uploaded documents. 
Generate output formatted in markdown for nicer visuals."

Context:
{context}"""


qa_prompt = ChatPromptTemplate.from_messages([
    ("system", qa_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

answer_generator = qa_prompt | llm | StrOutputParser()

def format_docs(docs: list[Document]) -> str:
    return "\n\n".join(doc.page_content for doc in docs)

def generate_message(user_prompt: str):
    question_for_docs = question_rewriter.invoke({
            "chat_history": chat_history,
            "input": user_prompt
        })

    docs = db.retriever.invoke(question_for_docs)
    context_string = format_docs(docs)

    # later there will be some setting to check if the user want to generate messages even when nothing was found in the rag
    if not context_string:
        # context_string = """
        # No data was found with the RAG, nothing in the saved documents,
        # so generate the best answer you can without the resouces,
        # or just answer that you dont know.
        # """
        yield "No relatable data availible."  
        return

    
    full_answer = ""
    # get responses in chunks
    # print("AI response: \n")

    for chunk in answer_generator.stream({
        "context": context_string,
        "chat_history": chat_history,
        "input": user_prompt
    }):
        full_answer += chunk
        yield chunk
        
    # print("\n\n")
    
    # response = answer_generator.invoke({
    #     "context": context_string,
    #     "chat_history": chat_history,
    #     "input": user_prompt
    # })

    # add the new response to the history
    chat_history.append(HumanMessage(user_prompt))
    chat_history.append(AIMessage(full_answer))

    # return full_answer

# rag_chain = (
#     {"context": db.retriever | format_docs, "question": RunnablePassthrough() }
#     | prompt
#     | llm
#     | StrOutputParser()
# )
