import os
import json
import time
import threading
import asyncio
import mcp
import traceback
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.server.fastmcp import Image
from mcp.client.stdio import stdio_client

from ailice.common.lightRPC import makeServer
from ailice.common.ADataType import AImage, AVideo


loop = None
def run_event_loop():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_forever()

loop_thread = threading.Thread(target=run_event_loop, daemon=True)
loop_thread.start()

while loop is None:
    time.sleep(0.01)

async def LoadMeta(serverParams):
    async with stdio_client(serverParams) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            toolsInfo = await session.list_tools()
            return toolsInfo

def ConstructPrompt(name: str, tool) -> str:
    return f"{name} is a tool called through stringified json. Its description is: {tool.description}. Its schema is: {str(tool.inputSchema)}. You need to put json in triple quotes as a string type parameter."

def AddActionMethod(kls, name: str, tool):
    async def async_action_method(self, jsonParam: str) -> str:
        try:
            return await self.session.call_tool(name, arguments=json.loads(jsonParam))
        except Exception as e:
            return json.dumps({"error": str(e)})
            
    def action_method(self, jsonParam: str) -> list:
        ret = asyncio.run_coroutine_threadsafe(async_action_method(self, jsonParam), loop).result()
        result = []
        for item in ret.content:
            if type(item) == mcp.types.TextContent:
                result.append(str(item))
            elif type(item) == mcp.types.ImageContent:
                result.append(AImage.FromJson({"data": item.data}))
            elif type(item) == mcp.types.EmbeddedResource:
                result.append("[Unsupported EmbeddedResource content]")
        return result
    
    action_method.__name__ = name
    action_method.__qualname__ = f"{kls.__name__}.{name}"
    setattr(kls, name, action_method)
    
    kls.MODULE_INFO["ACTIONS"][name] = {"func": name, "prompt": ConstructPrompt(name, tool), "type": "primary"}
    return


def MakeWrapper(serverParams):
    class AMCPWrapper():
        #TODO. How to get the module name?
        MODULE_INFO = {"NAME": serverParams.args[0], "ACTIONS": {}}
        
        def __init__(self, serverParams):
            self.serverParams = serverParams
            self.exit_stack = None
            self.stdio = None
            self.write = None
            self.session = None
            asyncio.run_coroutine_threadsafe(self.initialize(), loop).result()
            return

        def __del__(self):
            if hasattr(self, 'exit_stack') and self.exit_stack:
                try:
                    asyncio.run_coroutine_threadsafe(self.close(), loop).result()
                except Exception as e:
                    print(f"Error closing resources: {e}")
        
        async def initialize(self):
            self.MODULE_INFO["NAME"] = self.serverParams.args[0]
            self.exit_stack = AsyncExitStack()
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(self.serverParams))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
            await self.session.initialize()
            
        async def close(self):
            if self.exit_stack:
                await self.exit_stack.aclose()

        def ModuleInfo(self):
            return self.MODULE_INFO
    
    maxRetries = 3
    for attempt in range(maxRetries):
        try:
            toolsInfo = asyncio.run_coroutine_threadsafe(LoadMeta(serverParams), loop).result()
            break
        except Exception as e:
            if attempt == maxRetries - 1:
                raise
            print(f"Attempt {attempt+1} failed: {e}, retrying...")
            time.sleep(1)
    
    actions = []
    for tool in toolsInfo.tools:
        print(tool)
        actions.append(tool.name)
        AddActionMethod(AMCPWrapper, tool.name, tool)
    return AMCPWrapper, actions

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--addr', type=str, help="The address where the service runs on.")

    parser.add_argument('cmd', help='The command to be executed.')
    parser.add_argument('cmd_args', nargs='*', help='Command arguments.')
    parser.add_argument('--env', action='append', dest='env_vars', metavar='KEY=VALUE', help='Set up env variables, the format should be: KEY=VALUE')
    args = parser.parse_args()
    
    env = os.environ.copy()
    if args.env_vars:
        for env_var in args.env_vars:
            try:
                key, value = env_var.split('=', 1)
                env[key] = value
            except ValueError:
                print(f"Warning: Incorrect environment variable format: {env_var}, should be KEY=VALUE format.")
    
    try:
        serverParams = StdioServerParameters(command=args.cmd, args=args.cmd_args, env=env)
        kls, actions = MakeWrapper(serverParams)
        server = makeServer(kls, {"serverParams": serverParams}, args.addr, ["ModuleInfo"] + actions)
        server.Run()
    except Exception as e:
        print(f"Error in main: {e}", traceback.print_tb(e.__traceback__))
    finally:
        if loop is not None:
            loop.call_soon_threadsafe(loop.stop)
            loop_thread.join(timeout=5)
    
if __name__ == '__main__':
    main()