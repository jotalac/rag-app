import asyncio
from langchain_ollama import ChatOllama


async def main():
    llm = ChatOllama(model="gemma4:e4b", temperature=0.0, reasoning=True)
    async for chunk in llm.astream(
        "when there are shells nuts what is the probability that the nut is under the shell?"
    ):
        print("content:", repr(chunk.content))
        print("kwargs:", chunk.additional_kwargs)


asyncio.run(main())
