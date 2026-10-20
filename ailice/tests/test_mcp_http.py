"""Run with: python -m unittest discover -s ailice/tests -p test_mcp_http.py"""
import asyncio
import inspect
import json
import logging
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import uvicorn
from mcp.server.fastmcp import FastMCP

from ailice.common.AConfig import AConfig
from ailice.common.lightRPC import makeClient, destroyClient
from ailice.core.AInterpreter import AInterpreter
from ailice.core.AProcessor import AProcessor
from ailice.modules import AMCPWrapper as wrapper
from ailice.prompts.ARegex import GenerateRE4FunctionCalling


class MCPHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.getLogger('httpx').setLevel(logging.WARNING)
        cls.requests = []
        cls.started = threading.Event()
        mcp = FastMCP('search fixture', stateless_http=True, json_response=True)

        @mcp.tool()
        async def web_search(objective: str, search_queries: list[str], session_id: str = None) -> str:
            if objective == 'slow':
                cls.started.set()
                await asyncio.sleep(5)
            if objective == 'denied':
                raise ValueError('Search permission denied')
            return json.dumps({'url': 'https://example.org/a?q=1&b=2', 'title': objective,
                               'session_id': session_id})

        @mcp.tool()
        def web_fetch(urls: list[str], session_id: str = None) -> str:
            return json.dumps({'urls': urls, 'content': 'A useful page excerpt', 'session_id': session_id})

        cls.mcp = mcp
        app = mcp.streamable_http_app()

        async def record(scope, receive, send):
            if scope['type'] == 'http':
                request = {'path': scope['path'], 'headers': dict(scope['headers']), 'body': b''}
                cls.requests.append(request)

                async def capture():
                    message = await receive()
                    request['body'] += message.get('body', b'')
                    return message

                if scope['path'] == '/denied':
                    await send({'type': 'http.response.start', 'status': 403, 'headers': []})
                    await send({'type': 'http.response.body', 'body': b'Permission denied'})
                    return
                await app(scope, capture, send)
            else:
                await app(scope, receive, send)

        cls.sock = socket.socket()
        cls.sock.bind(('127.0.0.1', 0))
        cls.url = f'http://127.0.0.1:{cls.sock.getsockname()[1]}/mcp'
        cls.server = uvicorn.Server(uvicorn.Config(record, log_level='error'))
        cls.thread = threading.Thread(target=cls.server.run, kwargs={'sockets': [cls.sock]}, daemon=True)
        cls.thread.start()
        deadline = time.monotonic() + 10
        while not cls.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError('Fixture did not start')
            time.sleep(0.01)
        cls.kls, cls.actions = wrapper.MakeWrapper(serverUrl=cls.url, transport='http', timeout=3)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=10)
        cls.sock.close()

    def processor(self, module):
        storage = SimpleNamespace(Store=lambda *args: None)
        processor = AProcessor.__new__(AProcessor)
        processor.modules = {'storage': {'module': storage}}
        processor.collection = 'test'
        processor.services = SimpleNamespace(GetClient=lambda addr: module)
        processor.interpreter = AInterpreter(SimpleNamespace(Get=lambda: None))
        for record in processor.RegisterModules(['fixture']):
            processor.interpreter.RegisterPattern(record['action'], GenerateRE4FunctionCalling(record['signature']), True)
        return processor

    def dispatch(self, processor, action, arguments):
        call = f'!{action}<!|{json.dumps(json.dumps(arguments))}|!>'
        return processor.interpreter.EvalEntries(call)

    def test_runtime_registration_search_fetch_and_wire_headers(self):
        start = len(self.requests)
        processor = self.processor(self.kls())
        result = self.dispatch(processor, 'web_search', {'objective': 'current research', 'search_queries': ['test query']})
        self.assertIn('https://example.org/a?q=1&b=2', result)
        result = self.dispatch(processor, 'web_fetch', {'urls': ['https://example.org/a?q=1&b=2']})
        self.assertIn('A useful page excerpt', result)
        messages = [json.loads(r['body']) for r in self.requests if r['body']]
        self.assertTrue(any(m.get('method') == 'tools/list' for m in messages))
        self.assertTrue(any(m.get('method') == 'tools/call' for m in messages))
        for request in self.requests[start:]:
            self.assertEqual('/mcp', request['path'])
            self.assertEqual(wrapper.USER_AGENT.encode(), request['headers'].get(b'user-agent'))
            self.assertNotIn(b'authorization', request['headers'])

    def test_arguments_are_not_assigned_connection_or_process_identity(self):
        module = self.kls()
        def search(identity):
            return module.web_search(json.dumps({'objective': identity, 'search_queries': ['test'], 'session_id': identity}))
        with ThreadPoolExecutor() as pool:
            first, second = list(pool.map(search, ['conversation-a', 'conversation-b']))
        self.assertIn('conversation-a', first[0])
        self.assertIn('conversation-b', second[0])
        result = module.web_fetch(json.dumps({'urls': ['https://example.org'], 'session_id': 'conversation-a'}))
        self.assertIn('conversation-a', result[0])
        call = module.web_search(json.dumps({'objective': 'fresh', 'search_queries': ['test']}))
        self.assertIsNone(json.loads(call[0])['session_id'])

    def test_tool_errors_invalid_json_and_http_denial_are_consumable(self):
        module = self.kls()
        self.assertIn('Search permission denied', module.web_search(json.dumps({'objective': 'denied', 'search_queries': ['test']}))[0])
        self.assertIn('error', module.web_search('{broken')[0])
        module.serverUrl = self.url.replace('/mcp', '/denied')
        self.assertIn('403', module.web_search(json.dumps({'objective': 'test', 'search_queries': ['test']}))[0])

    def test_timeout_cancels_request_and_followup_still_works(self):
        module = self.kls()
        module.timeout = 0.15
        start = time.monotonic()
        result = module.web_search(json.dumps({'objective': 'slow', 'search_queries': ['test']}))
        self.assertIn('timed out', result[0])
        self.assertLess(time.monotonic() - start, 2)
        module.timeout = 3
        self.assertIn('healthy', module.web_search(json.dumps({'objective': 'healthy', 'search_queries': ['test']}))[0])

    def test_interrupt_cancels_actual_http_call(self):
        self.started.clear()
        original = asyncio.run_coroutine_threadsafe
        futures = []
        def schedule(coro, loop):
            future = original(coro, loop)
            futures.append(future)
            class Interrupted:
                def result(inner):
                    self.assertTrue(self.started.wait(3))
                    raise KeyboardInterrupt()
                def cancel(inner):
                    return future.cancel()
            return Interrupted()
        with patch.object(wrapper.asyncio, 'run_coroutine_threadsafe', side_effect=schedule):
            with self.assertRaises(KeyboardInterrupt):
                self.kls().web_search(json.dumps({'objective': 'slow', 'search_queries': ['test']}))
        self.assertTrue(futures[0].cancelled())

    def test_optional_configuration_and_existing_choices(self):
        config = AConfig()
        self.assertNotIn('parallel', config.services)
        self.assertIn('ADuckDuckGo', config.services['duckduckgo']['cmd'])
        selected = {'cmd': 'my-search --key configured', 'addr': 'tcp://127.0.0.1:59004'}
        config.Update({'services': {'google': selected}})
        self.assertEqual(selected, config.services['google'])
        self.assertNotIn('parallel', config.services)
        self.assertEqual('sse', inspect.signature(wrapper.MakeWrapper).parameters['transport'].default)

    def test_installed_http_service_rpc_and_dispatch(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        address = f'tcp://127.0.0.1:{port}'
        executable = str(Path(sys.executable).parent / 'ailice_mcp_wrapper')
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen([executable, '--addr', address, 'http', '--server_url', self.url],
                                       stdout=output, stderr=output)
            try:
                deadline = time.monotonic() + 10
                while True:
                    try:
                        with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                            break
                    except OSError:
                        if time.monotonic() > deadline or process.poll() is not None:
                            output.seek(0)
                            self.fail(output.read().decode())
                        time.sleep(0.02)
                client = makeClient(address, timeout=3000, retries=1)
                try:
                    processor = self.processor(client)
                    result = self.dispatch(processor, 'web_search', {'objective': 'RPC research', 'search_queries': ['test']})
                    self.assertIn('RPC research', result)
                    result = self.dispatch(processor, 'web_fetch', {'urls': ['https://example.org']})
                    self.assertIn('A useful page excerpt', result)
                finally:
                    destroyClient(client)
            finally:
                process.terminate()
                process.wait(timeout=10)

    def test_installed_cli_http_mode_and_invalid_timeout(self):
        executable = str(Path(sys.executable).parent / 'ailice_mcp_wrapper')
        invalid = subprocess.run([executable, '--addr', 'tcp://127.0.0.1:0', 'parallel', '--timeout', 'nan'], capture_output=True, text=True)
        self.assertNotEqual(0, invalid.returncode)
        self.assertIn('positive finite', invalid.stderr)
        help_result = subprocess.run([executable, '--help'], capture_output=True, text=True)
        self.assertEqual(0, help_result.returncode)
        for mode in ['parallel', 'http', 'sse', 'stdio']:
            self.assertIn(mode, help_result.stdout)


if __name__ == '__main__':
    unittest.main()
