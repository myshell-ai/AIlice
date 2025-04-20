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
        
        # Process the page and all its frames
        content = await self.AsyncHtmlToMarkdown()
        self.LoadPage(content, "TOP")
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
            
            content = await self.AsyncHtmlToMarkdown()
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
    
    async def AsyncHtmlToMarkdown(self):
        """Convert HTML to Markdown using JavaScript for DOM processing and Python for frame handling"""
        # Initialize URL mapping
        self.urls = {}
        
        # Process the main page and all frames
        result = await self.AsyncProcessPageAndFrames(self.page)
        return result

    async def AsyncProcessPageAndFrames(self, page_or_frame):
        """Process a page or frame and all its child frames recursively"""
        # Process the current page/frame content using JavaScript
        result = await page_or_frame.evaluate("""() => {
            // Helper function to clean text
            function cleanText(text) {
                return text ? text.replace(/\\s+/g, ' ').trim() : '';
            }
            
            // Helper function to ensure element is visible
            function isVisible(element) {
                if (!element) return false;
                
                // Check computed style
                const style = window.getComputedStyle(element);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                    return false;
                }
                
                // Check dimensions
                const rect = element.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) {
                    return false;
                }
                
                return true;
            }
            
            // Process a form element
            function processForm(form) {
                let formInfo = ['\\n\\n```', 'Form:'];
                
                // Extract form attributes
                ['action', 'method', 'name', 'id', 'class'].forEach(attr => {
                    if (form[attr]) {
                        formInfo.push(`- ${attr.charAt(0).toUpperCase() + attr.slice(1)}: ${form[attr]}`);
                    }
                });
                
                // Build selector
                let selector = 'form';
                if (form.id) selector = `form#${form.id}`;
                else if (form.name) selector = `form[name='${form.name}']`;
                else if (form.className) {
                    const className = form.className.split(' ')[0];
                    if (className) selector = `form.${className}`;
                }
                
                formInfo.push(`- Selector: ${selector}`);
                formInfo.push('\\nFields:');
                
                // Process form fields
                const fields = form.querySelectorAll('input, select, textarea, button');
                let fieldCount = 0;
                
                fields.forEach(field => {
                    if (!isVisible(field)) return;
                    
                    fieldCount++;
                    formInfo.push(`${fieldCount}. ${field.nodeName.charAt(0).toUpperCase() + field.nodeName.slice(1).toLowerCase()}:`);
                    
                    ['type', 'name', 'id', 'placeholder', 'required'].forEach(attr => {
                        if (field[attr]) {
                            formInfo.push(`   - ${attr.charAt(0).toUpperCase() + attr.slice(1)}: ${field[attr]}`);
                        }
                    });
                    
                    // Build field selector
                    let fieldSelector = '';
                    if (field.id) fieldSelector = `#${field.id}`;
                    else if (field.name) fieldSelector = `${field.nodeName.toLowerCase()}[name='${field.name}']`;
                    else fieldSelector = `${selector} ${field.nodeName.toLowerCase()}`;
                    if (field.type && !field.id && !field.name) fieldSelector += `[type='${field.type}']`;
                    
                    formInfo.push(`   - Selector: ${fieldSelector}`);
                    
                    if (field.value) {
                        formInfo.push(`   - Value: "${field.value}"`);
                    }
                    
                    if (field.nodeName.toLowerCase() === 'select') {
                        formInfo.push('   - Options:');
                        for (const option of field.options) {
                            formInfo.push(`     * Value: "${option.value}", Text: "${option.text}", Selected: ${option.selected}`);
                        }
                    }
                    
                    if (field.nodeName.toLowerCase() === 'button') {
                        formInfo.push(`   - Text: "${cleanText(field.textContent)}"`);
                    }
                });
                
                formInfo.push('```\\n\\n');
                return formInfo.join('\\n');
            }
            
            // Generate a unique ID
            function generateUniqueId(prefix) {
                return prefix + '_' + Date.now() + '_' + Math.random().toString(36).substring(2, 15);
            }
            
            // Store for URL mappings and iframe positions
            const urlMappings = {};
            const iframePositions = [];
            
            // Process a node recursively
            function processNode(node, strip = true, depth = 0) {
                if (!node) return '';
                
                // Skip invisible elements
                if (node.nodeType === Node.ELEMENT_NODE && !isVisible(node)) {
                    return '';
                }
                
                // Skip comments
                if (node.nodeType === Node.COMMENT_NODE) {
                    return '';
                }
                
                // Skip script, style, etc.
                if (node.nodeType === Node.ELEMENT_NODE) {
                    const tagName = node.nodeName.toLowerCase();
                    if (['script', 'style', 'noscript', 'svg', 'path', 'meta', 'link'].includes(tagName)) {
                        return '';
                    }
                }
                
                // Text node
                if (node.nodeType === Node.TEXT_NODE) {
                    const text = node.textContent || '';
                    return strip ? cleanText(text) : text;
                }
                
                // Element node
                const tagName = node.nodeName.toLowerCase();
                let result = '';
                
                // Process by tag type
                switch (tagName) {
                    case 'form':
                        return processForm(node);
                        
                    case 'li':
                        let liContent = '';
                        for (const child of node.childNodes) {
                            const childContent = processNode(child, strip, depth + 1);
                            if (childContent && childContent.trim()) {
                                liContent += childContent;
                            }
                        }
                        return `- ${liContent.trim()}\\n`;
                        
                    case 'p':
                        let pContent = '';
                        for (const child of node.childNodes) {
                            const childContent = processNode(child, strip, depth + 1);
                            if (childContent && childContent.trim()) {
                                pContent += childContent;
                            }
                        }
                        return `\\n\\n${pContent}\\n\\n`;
                        
                    case 'pre':
                        let preContent = '';
                        for (const child of node.childNodes) {
                            const childContent = processNode(child, false, depth + 1);
                            if (childContent) {
                                preContent += childContent;
                            }
                        }
                        return `\\n\\n\`\`\`\\n${preContent}\\n\`\`\`\\n\\n`;
                        
                    case 'code':
                        let codeContent = '';
                        for (const child of node.childNodes) {
                            const childContent = processNode(child, false, depth + 1);
                            if (childContent) {
                                codeContent += childContent;
                            }
                        }
                        return `\`${codeContent}\``;
                        
                    case 'h1': case 'h2': case 'h3': case 'h4': case 'h5': case 'h6':
                        const level = parseInt(tagName.charAt(1));
                        let headingContent = '';
                        for (const child of node.childNodes) {
                            const childContent = processNode(child, strip, depth + 1);
                            if (childContent) {
                                headingContent += childContent;
                            }
                        }
                        return `\\n\\n${'#'.repeat(level)} ${headingContent.trim()}\\n`;
                        
                    case 'a':
                        const href = node.getAttribute('href') || '';
                        let linkContent = '';
                        for (const child of node.childNodes) {
                            const childContent = processNode(child, strip, depth + 1);
                            if (childContent) {
                                linkContent += childContent;
                            }
                        }
                        
                        if (!linkContent) {
                            linkContent = strip ? cleanText(node.textContent) : node.textContent;
                        }
                        
                        if (linkContent && href) {
                            // Create a unique ID for this link
                            const linkId = generateUniqueId('link');
                            urlMappings[linkId] = {
                                url: href,
                                text: linkContent
                            };
                            return `[${linkContent}](${linkId})`;
                        }
                        return linkContent;
                        
                    case 'img':
                        const src = node.getAttribute('src') || '';
                        const alt = strip ? cleanText(node.getAttribute('alt') || '') : (node.getAttribute('alt') || '');
                        
                        if (src) {
                            if (src.startsWith('data:')) {
                                return alt;
                            }
                            // Create a unique ID for this image
                            const imgId = generateUniqueId('img');
                            urlMappings[imgId] = {
                                url: src,
                                text: alt || 'Image'
                            };
                            return `\\n![${alt || 'Image'}](${imgId})\\n`;
                        }
                        return alt;
                        
                    case 'video':
                        const videoSrc = node.getAttribute('src') || '';
                        if (videoSrc) {
                            // Create a unique ID for this video
                            const videoId = generateUniqueId('video');
                            urlMappings[videoId] = {
                                url: videoSrc,
                                text: 'Video'
                            };
                            return `\\n\\n[Video](${videoId})\\n\\n`;
                        }
                        
                        const sourceElement = node.querySelector('source');
                        if (sourceElement) {
                            const sourceSrc = sourceElement.getAttribute('src') || '';
                            if (sourceSrc) {
                                // Create a unique ID for this video source
                                const sourceId = generateUniqueId('video');
                                urlMappings[sourceId] = {
                                    url: sourceSrc,
                                    text: 'Video'
                                };
                                return `\\n\\n[Video](${sourceId})\\n\\n`;
                            }
                        }
                        return '';
                        
                    case 'iframe':
                        const iframeSrc = node.getAttribute('src') || '';
                        if (iframeSrc) {
                            // Create a placeholder for this iframe
                            const iframeId = generateUniqueId('iframe');
                            const placeholder = `__IFRAME_PLACEHOLDER_${iframeId}__`;
                            
                            // Store iframe information for later processing
                            iframePositions.push({
                                id: iframeId,
                                src: iframeSrc,
                                placeholder: placeholder,
                                name: node.getAttribute('name') || node.getAttribute('id') || 'Unnamed Frame'
                            });
                            
                            return placeholder;
                        }
                        return '';
                        
                    case 'ul': case 'ol':
                        let listContent = '\\n\\n';
                        for (const child of node.childNodes) {
                            const childContent = processNode(child, strip, depth + 1);
                            if (childContent) {
                                listContent += childContent;
                            }
                        }
                        return listContent + '\\n\\n';
                        
                    case 'div': case 'span': case 'section': case 'article': case 'main': case 'header': case 'footer':
                        for (const child of node.childNodes) {
                            const childContent = processNode(child, strip, depth + 1);
                            if (childContent) {
                                result += childContent;
                            }
                        }
                        break;
                        
                    default:
                        for (const child of node.childNodes) {
                            const childContent = processNode(child, strip, depth + 1);
                            if (childContent) {
                                result += childContent;
                            }
                        }
                }
                
                return result;
            }
            
            // Process the document body
            const body = document.body;
            const markdown = processNode(body, true, 0);
            
            return {
                markdown: markdown,
                urls: urlMappings,
                iframes: iframePositions
            };
        }""")
        
        # Extract data from JavaScript result
        markdown = result['markdown']
        urls = result['urls']
        iframes = result['iframes']
        
        # Store URLs in the instance variable
        for id, url_info in urls.items():
            url = url_info['url']
            text = url_info['text']
            
            # Create a unique text for the URL mapping
            unique_text = self.EnsureUnique(text)
            self.urls[unique_text] = urljoin(self.page.url, url)
            
            # Replace the placeholder with the unique text
            markdown = markdown.replace(f"[{text}]({id})", f"[{unique_text}]")
            markdown = markdown.replace(f"![{text}]({id})", f"![{unique_text}]({urljoin(self.page.url, url)})")
        
        # Process iframes
        for iframe in iframes:
            iframe_src = iframe['src']
            placeholder = iframe['placeholder']
            
            if not iframe_src:
                continue
                
            # Find the frame in the page's frame tree
            iframe_content = ""
            iframe_url = urljoin(self.page.url, iframe_src)
            
            for frame in (page_or_frame.frames if hasattr(page_or_frame, "frames") else page_or_frame.child_frames):
                if frame.url == iframe_src or frame.url == iframe_url:
                    try:
                        # Recursively process the frame
                        iframe_content = await self.AsyncProcessPageAndFrames(frame)
                        break
                    except Exception as e:
                        print(f"Error processing iframe: {str(e)}")
            
            if not iframe_content:
                iframe_content = f"[Iframe: {iframe_src}]"
            else:
                iframe_name = iframe['name']
                iframe_content = f"\n\n--- Frame: {iframe_name} ({iframe_src}) ---\n\n{iframe_content}\n\n--- End of Frame ---\n\n"
            
            # Replace the placeholder with the iframe content
            markdown = markdown.replace(placeholder, iframe_content)
        
        return markdown

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