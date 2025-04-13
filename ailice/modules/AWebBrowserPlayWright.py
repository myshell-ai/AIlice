import os
import re
import random
import traceback
import threading
import asyncio
from contextlib import AsyncExitStack
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment, Tag
from playwright.async_api import async_playwright

from ailice.modules.AScrollablePage import AScrollablePage


class AWebBrowser(AScrollablePage):
    def __init__(self, functions: dict[str, str]):
        super(AWebBrowser, self).__init__(functions=functions)
        self.inited = False
        self.exit_stack = AsyncExitStack()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.urls = {}
        self.prompt = '''
The text with links are enclosed in square brackets to highlight it. If you need to open the page linked to a certain text, please call GET-LINK<!|text: str, session: str|!> function to get the url, and then call BROWSE<!|url: str, session: str|!>. Please note that the text parameter of GET-LINK must exactly match the content in the square brackets (excluding the square brackets themselves).
The forms on the webpage have been listed in text format, and you can use the EXECUTE-JS<!|js_code: str, session: str|!> function to operate the form, such as entering text, clicking buttons, etc. Use triple quotes on your code. Example: 
!EXECUTE-JS<!|"""
document.querySelector('form.mini-search input[name="query"]').value = "hello world";
document.querySelector('form.mini-search').submit();
""", "arxiv_session"|!>
'''
        # Set up event loop and thread
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.RunEventLoop, daemon=True)
        self.thread.start()
        
    def RunEventLoop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        
    def RunCoroutine(self, coro, timeout=60):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=timeout)
        except Exception as e:
            if not future.done():
                future.cancel()
            raise e
    
    async def AsyncInit(self):
        if self.inited:
            return True, ""
        
        try:
            self.playwright = await self.exit_stack.enter_async_context(async_playwright())
            
            browser_args = []
            if os.path.exists('/.dockerenv'):
                browser_args.append('--no-sandbox')
            
            browser_instance = await self.playwright.chromium.launch(
                headless=True,
                args=browser_args
            )
            self.browser = await self.exit_stack.enter_async_context(browser_instance)

            context_instance = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            self.context = await self.exit_stack.enter_async_context(context_instance)
            
            await self.context.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,otf,eot}", lambda route: route.abort())
            self.page = await self.context.new_page()
            self.inited = True
            return True, ""
        except Exception as e:
            await self.exit_stack.aclose()
            return False, f"Browser initialization failed: {str(e)}\n{traceback.format_exc()}"
    
    def Init(self):
        return self.RunCoroutine(self.AsyncInit())
    
    async def AsyncBrowse(self, url):
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return "Invalid URL. Please provide a complete URL starting with http:// or https://"
        except Exception:
            return "Invalid URL format. Please check the URL and try again."
        
        succ, msg = await self.AsyncInit()
        if not succ:
            raise Exception(msg)
        
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await self.page.wait_for_timeout(2000)
        self.LoadPage(await self.AsyncHtmlToMarkdown(await self.page.content(), url), "TOP")
        return self() + self.prompt
    
    def Browse(self, url):
        return self.RunCoroutine(self.AsyncBrowse(url))
    
    def GetFullText(self):
        return self.txt if (self.txt is not None) else ""
    
    def GetLink(self, text):
        if text in self.urls:
            return self.urls[text]
        else:
            import difflib
            prompt = "Please note that the text you use to query the URL should be the part enclosed in square brackets (excluding the square brackets themselves), otherwise the search will not yield results."
            similars = '\n'.join(['[' + key + '](' + self.urls[key] + ')' for key in difflib.get_close_matches(text, self.urls, n=3)])
            if similars == "":
                return "No url found on specified text. \n" + prompt
            else:
                return f"No exact match found, the most similar URLs are as follows:\n {similars} \n{prompt}"
    
    def ScrollDown(self):
        return super(AWebBrowser, self).ScrollDown() + self.prompt
    
    def ScrollUp(self):
        return super(AWebBrowser, self).ScrollUp() + self.prompt
    
    def SearchDown(self, query):
        return super(AWebBrowser, self).SearchDown(query) + self.prompt
    
    def SearchUp(self, query):
        return super(AWebBrowser, self).SearchUp(query) + self.prompt
    
    async def AsyncExecuteJS(self, js_code):
        succ, msg = await self.AsyncInit()
        if not succ:
            return msg
        
        try:
            if not self.page or self.page.is_closed():
                return "No active page. Please browse to a URL first."
            
            result = await self.page.evaluate(js_code)
            await self.page.wait_for_timeout(2000)
            
            content = await self.AsyncHtmlToMarkdown(await self.page.content(), self.page.url)
            result_str = "JavaScript executed successfully." if result is None else str(result)
            self.LoadPage(f"JS execution returned: {result_str}\n\n---\n\nThe current page content is as follows:\n\n{content}", "TOP")
            return self() + self.prompt
        except Exception as e:
            return f"Error executing JavaScript: {str(e)}\n{traceback.format_exc()}"
    
    def ExecuteJS(self, js_code):
        return self.RunCoroutine(self.AsyncExecuteJS(js_code))
    
    def EnsureUnique(self, text):
        if not text or text.isspace():
            text = "Link"
        
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            text = "Link"
        
        ret = text
        while ret in self.urls:
            ret = text + " |" + str(random.randint(0, 10000000))
        return ret
    
    async def AsyncHtmlToMarkdown(self, html_content, base_url):
        soup = BeautifulSoup(html_content, 'html.parser')
        self.urls = {}
        body = soup.find('body')
        return await self.AsyncProcessNode(body if body else soup, base_url)

    async def AsyncProcessNode(self, node, base_url, strip=True, depth=0):
        if node is None:
            return ''
        
        if isinstance(node, Comment):
            return ''
        
        if isinstance(node, Tag) and node.has_attr('style') and 'display:none' in node.get('style', ''):
            return ''
        
        if node.name in ['script', 'style', 'noscript', 'svg', 'path', 'meta', 'link']:
            return ''
        
        if node.name is None:
            text = node.string or ''
            return text.strip() if strip and text else text or ''
        
        result = ''
        
        if node.name == 'form':
            form_info = self.ProcessForm(node)
            return f"\n\n```\n{form_info}\n```\n\n"
        
        elif node.name == 'li':
            content = ''
            for child in node.children:
                child_content = await self.AsyncProcessNode(child, base_url, strip, depth+1)
                if child_content and not child_content.isspace():
                    content += child_content
            return f"- {content.strip()}\n"
        
        elif node.name == 'p':
            content = ''
            for child in node.children:
                child_content = await self.AsyncProcessNode(child, base_url, strip, depth+1)
                if child_content and not child_content.isspace():
                    content += child_content
            return f"\n\n{content}\n\n"
        
        elif node.name == 'pre':
            content = ''
            for child in node.children:
                child_content = await self.AsyncProcessNode(child, base_url, False, depth+1)
                if child_content:
                    content += child_content
            return f"\n\n```\n{content}\n```\n\n"
        
        elif node.name == 'code':
            content = ''
            for child in node.children:
                child_content = await self.AsyncProcessNode(child, base_url, False, depth+1)
                if child_content:
                    content += child_content
            return f"`{content}`"
        
        elif node.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(node.name[1])
            content = ''
            for child in node.children:
                child_content = await self.AsyncProcessNode(child, base_url, strip, depth+1)
                if child_content:
                    content += child_content
            return f"\n\n{'#' * level} {content.strip()}\n"
        
        elif node.name == 'a':
            href = node.get('href', '')
            content = ''
            for child in node.children:
                child_content = await self.AsyncProcessNode(child, base_url, strip, depth+1)
                if child_content:
                    content += child_content
            
            if not content:
                content = node.get_text().strip() if strip else node.get_text()
            
            if content and href:
                try:
                    full_url = urljoin(base_url, href)
                    unique_text = self.EnsureUnique(content)
                    self.urls[unique_text] = full_url
                    return f"[{unique_text}]"
                except Exception as e:
                    print(f"Error processing URL {href}: {str(e)}")
                    return content
            return content
        
        elif node.name == 'img':
            src = node.get('src', '')
            alt = node.get('alt', '').strip() if strip else node.get('alt', '')
            
            if src:
                try:
                    full_url = urljoin(base_url, src)
                    if not full_url.startswith('data:'):
                        unique_text = self.EnsureUnique(alt or "Image")
                        self.urls[unique_text] = full_url
                        return f"\n![{unique_text}]({full_url})\n"
                except Exception as e:
                    print(f"Error processing image URL {src}: {str(e)}")
                    return alt
            return alt
        
        elif node.name == 'video':
            src = node.get('src', '')
            if src:
                try:
                    full_url = urljoin(base_url, src)
                    return f"\n\n[Video]({full_url})\n\n"
                except Exception:
                    return ''
            
            source = node.find('source')
            if source:
                src = source.get('src', '')
                if src:
                    try:
                        full_url = urljoin(base_url, src)
                        return f"\n\n[Video]({full_url})\n\n"
                    except Exception:
                        return ''
            return ''
        
        elif node.name == 'iframe':
            try:
                src = node.get('src', '')
                if src:
                    iframe_url = urljoin(base_url, src)
                    return await self.AsyncProcessIFrame(iframe_url)
            except Exception as e:
                print(f"Error processing iframe: {str(e)}")
            return ''
            
        elif node.name in ['ul', 'ol']:
            content = "\n\n"
            for child in node.children:
                child_content = await self.AsyncProcessNode(child, base_url, strip, depth+1)
                if child_content:
                    content += child_content
            return content + "\n\n"
        
        elif node.name in ['div', 'span', 'section', 'article', 'main', 'header', 'footer']:
            for child in node.children:
                child_content = await self.AsyncProcessNode(child, base_url, strip, depth+1)
                if child_content:
                    result += child_content
        
        else:
            for child in node.children:
                child_content = await self.AsyncProcessNode(child, base_url, strip, depth+1)
                if child_content:
                    result += child_content
        
        return result
    
    def ProcessForm(self, node):
        """Process a form element and return its structure"""
        form_info = []
        form_info.append(f"Form:")
        
        for attr in ['action', 'method', 'name', 'id', 'class']:
            if node.has_attr(attr):
                form_info.append(f"- {attr.capitalize()}: {node[attr]}")
        
        selector = ""
        if node.has_attr('id'):
            selector = f"form#{node['id']}"
        elif node.has_attr('name'):
            selector = f"form[name='{node['name']}']"
        elif node.has_attr('class'):
            selector = f"form.{node['class'][0].replace(' ', '.')}" if isinstance(node['class'], list) else f"form.{node['class'].replace(' ', '.')}"
        else:
            selector = "form"
        
        form_info.append(f"- Selector: {selector}")
        
        form_info.append("\nFields:")
        field_count = 0
        
        for field in node.select('input, select, textarea, button'):
            field_count += 1
            field_info = [f"{field_count}. {field.name.capitalize()}:"]
            
            for attr in ['type', 'name', 'id', 'placeholder', 'required']:
                if field.has_attr(attr):
                    field_info.append(f"   - {attr.capitalize()}: {field[attr]}")
            
            field_selector = ""
            if field.has_attr('id'):
                field_selector = f"#{field['id']}"
            elif field.has_attr('name'):
                field_selector = f"{field.name}[name='{field['name']}']"
            else:
                field_selector = f"{selector} {field.name}"
                if field.has_attr('type'):
                    field_selector += f"[type='{field['type']}']"
            
            field_info.append(f"   - Selector: {field_selector}")
            
            if field.has_attr('value'):
                field_info.append(f"   - Value: \"{field['value']}\"")
            
            if field.name == 'select':
                field_info.append("   - Options:")
                for option in field.select('option'):
                    value = option.get('value', '')
                    text = option.get_text().strip()
                    is_selected = option.has_attr('selected')
                    field_info.append(f"     * Value: \"{value}\", Text: \"{text}\", Selected: {str(is_selected).lower()}")
            
            if field.name == 'button':
                field_info.append(f"   - Text: \"{field.get_text().strip()}\"")
            
            form_info.append("\n".join(field_info))
        
        return "\n".join(form_info)

    async def AsyncProcessIFrame(self, iframe_url):
        try:
            iframe_page = await self.context.new_page()
            await iframe_page.goto(iframe_url, wait_until="domcontentloaded", timeout=10000)
            await iframe_page.wait_for_timeout(1000)
            iframe_content = await iframe_page.content()
            
            iframe_soup = BeautifulSoup(iframe_content, 'html.parser')
            iframe_body = iframe_soup.find('body')
            if iframe_body:
                iframe_result = await self.AsyncProcessNode(iframe_body, iframe_url)
                return f"\n\n--- Iframe Content from {iframe_url} ---\n\n{iframe_result}\n\n--- End of Iframe Content ---\n\n"
        except Exception as e:
            print(f"Error loading iframe content: {str(e)}")
        finally:
            await iframe_page.close()
        return f"\n\n[Iframe: {iframe_url}]\n\n"
    
    async def AsyncDestroy(self):
        try:
            await self.exit_stack.aclose()
            
            self.inited = False
            self.playwright = None
            self.browser = None
            self.context = None
            self.page = None
            self.urls = {}
            
            return True, "Resources destroyed successfully"
        except Exception as e:
            return False, f"Error during cleanup: {str(e)}\n{traceback.format_exc()}"

    def Destroy(self):
        result = self.RunCoroutine(self.AsyncDestroy())
        
        def shutdown_loop():
            for task in asyncio.all_tasks(self.loop):
                if not task.done():
                    task.cancel()
            
            self.loop.call_later(1, self.loop.stop)
        
        self.loop.call_soon_threadsafe(shutdown_loop)
        self.thread.join(timeout=5)
        
        if self.thread.is_alive():
            print("Warning: Event loop thread did not terminate within timeout")
        return result