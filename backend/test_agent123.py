import asyncio
from app.agent.orchestrator import get_marketing_agent, connect_to_mcp_server
from mcp import ClientSession
# pyrefly: ignore [missing-import]
from langchain_core.callbacks import AsyncCallbackHandler

class InspectCallbackHandler(AsyncCallbackHandler):
    async def on_chat_model_start(self, serialized, messages, **kwargs):
        print("=== LLM START ===")
        total_chars = 0
        for i, msg_list in enumerate(messages):
            for j, msg in enumerate(msg_list):
                print(f"Message {i}.{j} ({msg.type}): length={len(msg.content)}")
                total_chars += len(msg.content)
                if len(msg.content) > 1000:
                    print(f"  First 500 chars: {msg.content[:500]}")
                    print(f"  Last 500 chars: {msg.content[-500:]}")
        print(f"Total characters in messages: {total_chars}")
        
        # Check tools passed via serialized or kwargs
        # Sometimes tools are in serialized or kwargs or bound to the LLM
        print(f"Serialized keys: {list(serialized.keys()) if serialized else []}")
        print(f"Kwargs keys: {list(kwargs.keys())}")
        if "invocation_params" in kwargs:
            params = kwargs["invocation_params"]
            if "tools" in params:
                print(f"Number of tools in invocation_params: {len(params['tools'])}")
                for t in params["tools"]:
                    t_str = str(t)
                    print(f"  Tool: length={len(t_str)}")
                    if len(t_str) > 500:
                        print(f"    First 300: {t_str[:300]}")
            else:
                print("No tools key in invocation_params")
        else:
            print("No invocation_params in kwargs")

async def run_test():
    async with connect_to_mcp_server() as conn:
        if len(conn) == 3:
            read_stream, write_stream, _ = conn
        else:
            read_stream, write_stream = conn
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            agent = await get_marketing_agent(session)
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": "Tell me about marketing strategies used by big companies in 2026"}]},
                config={"recursion_limit": 50, "callbacks": [InspectCallbackHandler()]}
            )
            print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(run_test())
