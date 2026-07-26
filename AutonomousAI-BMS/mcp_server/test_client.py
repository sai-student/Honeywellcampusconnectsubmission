import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():

    server_params = StdioServerParameters(
        command=r"E:\AutonomousAI-BMS\venv_ai\Scripts\python.exe",
        args=[
            r"E:\AutonomousAI-BMS\mcp_server\server.py"
        ]
    )

    print("=" * 50)
    print("       AUTONOMOUS AI-BMS MCP TEST")
    print("=" * 50)

    async with stdio_client(server_params) as (read, write):

        print("\n[OK] MCP server process started")

        async with ClientSession(read, write) as session:

            await session.initialize()

            print("[OK] MCP session initialized")

            # ----------------------------------
            # LIST TOOLS
            # ----------------------------------

            tools = await session.list_tools()

            print("\nAvailable MCP Tools:")
            print("-" * 50)

            for tool in tools.tools:
                print(f"  -> {tool.name}")

            # ----------------------------------
            # TEST SYSTEM STATUS
            # ----------------------------------

            print("\nTesting get_system_status...")
            result = await session.call_tool(
                "get_system_status",
                {}
            )

            print(result.content)

            # ----------------------------------
            # TEST BUILDING STATE
            # ----------------------------------

            print("\nTesting get_building_state...")
            result = await session.call_tool(
                "get_building_state",
                {}
            )

            print(result.content)

            # ----------------------------------
            # TEST SAFETY
            # ----------------------------------

            print("\nTesting unsafe HVAC proposal...")

            result = await session.call_tool(
                "validate_hvac_action",
                {
                    "heating_setpoint": 25,
                    "cooling_setpoint": 35
                }
            )

            print(result.content)

            print("\n" + "=" * 50)
            print("MCP TEST COMPLETED SUCCESSFULLY")
            print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())