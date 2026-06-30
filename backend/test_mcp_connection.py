import os
import asyncio
from dotenv import load_dotenv

# Load backend .env variables
load_dotenv()

from app.agent.orchestrator import connect_to_all_mcp_servers

async def test_connection():
    print("=" * 60)
    print("Testing MCP Servers Connections...")
    print("=" * 60)
    
    # Print current environment variables (excluding sensitive values)
    postiz_url = os.getenv("POSTIZ_MCP_URL", "https://api.postiz.com/mcp")
    postiz_key = os.getenv("POSTIZ_API_KEY", "")
    comfyui_url = os.getenv("COMFYUI_URL", "http://localhost:8188")
    
    print(f"ComfyUI URL: {comfyui_url}")
    print(f"Postiz MCP URL: {postiz_url}")
    print(f"Postiz API Key configured: {'Yes (Length: ' + str(len(postiz_key)) + ')' if postiz_key else 'No'}")
    print("-" * 60)

    try:
        async with connect_to_all_mcp_servers() as sessions:
            print("\nSuccessfully established MCP connection blocks!")
            print(f"Active session keys: {list(sessions.keys())}")
            
            # Test ComfyUI MCP Server Tools
            if "comfyui" in sessions:
                print("\n[ComfyUI MCP] Querying tools...")
                try:
                    comfy_tools = await sessions["comfyui"].list_tools()
                    print(f"✓ Connected! Found {len(comfy_tools.tools)} ComfyUI tools:")
                    for idx, tool in enumerate(comfy_tools.tools, 1):
                        print(f"  {idx}. {tool.name}: {tool.description[:60]}...")
                except Exception as e:
                    print(f"✗ Failed to retrieve ComfyUI tools: {e}")
                    
            # Test Postiz MCP Server Tools
            if "postiz" in sessions:
                print("\n[Postiz MCP] Querying tools...")
                try:
                    postiz_tools = await sessions["postiz"].list_tools()
                    print(f"✓ Connected! Found {len(postiz_tools.tools)} Postiz tools:")
                    for idx, tool in enumerate(postiz_tools.tools, 1):
                        print(f"  {idx}. {tool.name}: {tool.description[:60]}...")
                except Exception as e:
                    print(f"✗ Failed to retrieve Postiz tools: {e}")
            else:
                if postiz_key:
                    print("\n[Postiz MCP] ✗ Not connected! (Connection failed or was omitted during context yield)")
                else:
                    print("\n[Postiz MCP] (Omitted because POSTIZ_API_KEY is not set)")
                    
    except Exception as e:
        print(f"\n✗ Critical Error during connection setup: {e}")
        
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_connection())
