class StreamManager {
    constructor() {
        this.eventSource = null;
        this.isConnected = false;
        this.isInitializing = false;
        this.content = '';
        this.internalContent = '';
    }

    async initialize() {
        if (this.isInitializing) {
            console.log('Already initializing, skipping...');
            return;
        }

        this.isInitializing = true;
        
        try {
            this.disconnect();
            this.content = '';
            this.internalContent = '';
            this.eventSource = new EventSource('/stream');
            this.isConnected = true;
            this.setupEventHandlers();
        } catch (error) {
            console.error('Failed to initialize stream:', error);
        } finally {
            this.isInitializing = false;
        }
    }

    disconnect() {
        this.isConnected = false;
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
            console.info('Stream disconnected.');
        }
    }

    setupEventHandlers() {
        this.eventSource.onopen = () => {
            console.log('Stream connected');
            document.getElementById('chat-window').innerHTML = '';
            document.getElementById('history-content').innerHTML = '';
            this.content = '';
            this.internalContent = '';
        };

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.routeMessages(data);
            } catch (e) {
                console.error('Error parsing message:', e);
            }
        };

        this.eventSource.onerror = (event) => {
            console.error('Stream error:', event);
            this.isConnected = false;
        };
    }

    routeMessages(data) {
        const messages = Array.isArray(data) ? data : [data];

        messages.forEach((msg, index) => {
            try {
                if (msg.isRoundEnd) {
                    window.uiController.actor.send({ type: 'RESPOND' });
                } else {
                    switch (msg.type) {
                        case 'chat':
                        default:
                            this.handleChatMessage(msg);
                            break;
                    }
                }
            } catch (error) {
                console.error(`Error processing message ${index}:`, error);
            }
        });
    }

    handleChatMessage(data) {
        const roleType = data.role.split('_')[0];
        const roleHTML = `<span class='role'>${data.role}: </span>`;
        const prefix = { "": roleHTML, "open": roleHTML, "append": "", "close": "" };
        const breaks = { "": "<br><br>", "open": "<br><br>", "append": "", "close": "" };
        
        this.updateMessageDisplay(data, roleType, prefix, breaks, 'history-content', 'internalContent');

        if (data.msgType === "user-ailice" && roleType !== "SYSTEM") {
            this.updateMessageDisplay(data, roleType, prefix, breaks, 'chat-window', 'content');
        }
    }

    updateMessageDisplay(data, roleType, prefix, breaks, containerId, contentKey) {
        const container = document.getElementById(containerId);
        const lastElement = container.querySelector(`.message.${roleType}.${data.role}:last-child .bubble`);
        
        if (lastElement) {
            this[contentKey] += breaks[data.action] + data.message;
            lastElement.innerHTML = renderMarkdown(this[contentKey]);
            MathJax.typesetPromise([lastElement]);
        } else {
            this[contentKey] = prefix[data.action] + data.message;
            displayMsg(data.role, this[contentKey], containerId);
        }
        
        const isAtBottom = containerId === 'chat-window' ? chatIsAtBottom : historyIsAtBottom;
        if (isAtBottom) {
            container.scrollTop = container.scrollHeight;
        }
    }
}

export const streamManager = new StreamManager();

class SessionService {
    constructor() {
        this.uiController = null;
    }

    setDependencies(uiController) {
        this.uiController = uiController;
    }

    // Load selected history
    async loadHistory(sessionName, historyItem) {
        this.uiController.actor.send({ type: 'LOAD' });

        const removeLoading = showLoadingState(historyItem, 'history');

        const allItems = document.querySelectorAll('#history-list li');
        allItems.forEach(item => item.classList.remove('selected'));
        historyItem.classList.add('selected');

        try {
            const response = await fetch(`/load_history?name=${sessionName}`);
            if (!response.ok) {
                console.error('Failed to load history');
                return;
            }

            document.getElementById('chat-window').innerHTML = '';
            document.getElementById('history-content').innerHTML = '';
            
            streamManager.initialize();
        } catch (error) {
            console.error('Error loading history:', error);
        }
        finally {
            this.uiController.actor.send({ type: 'READY' });
            removeLoading();
        }
    }

    async getHistory(sessionName, historyItem) {
        try {
            const response = await fetch(`/get_history?name=${encodeURIComponent(sessionName)}`, {
                method: 'GET'
            });

            if (!response.ok) {
                console.error('Failed to get history item');
                return;
            }

            const data = await response.json();
            if (!data) return;

            const jsonStr = JSON.stringify(data, null, 2);
            const blob = new Blob([jsonStr], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${sessionName}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error:', error);
        }
    }

    async deleteHistory(sessionName, historyItem) {
        this.uiController.actor.send({ type: 'DELETE' });

        try {
            const response = await fetch(`/delete_history/${sessionName}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                if (historyItem.classList.contains('selected')) {
                    const chatWindow = document.getElementById('chat-window');
                    chatWindow.innerHTML = '';
                }
                historyItem.remove();
            } else {
                console.error('Failed to delete history item');
            }
        } catch {
            console.error('Error deleting history:', error);
        } finally {
            this.uiController.actor.send({ type: 'READY' });
        }
    }

    async newchat() {
        this.uiController.actor.send({ type: 'LOAD' });

        const newChatButton = document.getElementById('new-chat-button');
        const removeLoading = showLoadingState(newChatButton, 'new-chat');

        try {
            const response = await fetch('/new_chat');
            const data = await response.json();

            const historyList = document.getElementById('history-list');
            const historyItem = createHistoryItem('New Chat', data.sessionName);
            historyList.insertBefore(historyItem, historyList.firstChild);

            const allItems = document.querySelectorAll('#history-list li');
            allItems.forEach(item => item.classList.remove('selected'));
            historyItem.classList.add('selected');

            document.getElementById('chat-window').innerHTML = '';
            document.getElementById('history-content').innerHTML = '';

            streamManager.initialize();
        } catch (error) {
            console.error('Error creating new chat:', error);
        } finally {
            this.uiController.actor.send({ type: 'READY' });
            removeLoading();
        }
    }

    async ensureChat() {
        const selectedItem = document.querySelector('#history-list .selected');
        let newChatPromise = Promise.resolve();

        if (selectedItem == null) {
            newChatPromise = this.newchat();
        }
        return newChatPromise;
    }
}

export const sessionService = new SessionService();

class ChatService {
    constructor() {
        this.fileManager = null;
        this.uiController = null;
    }

    setDependencies(fileManager, uiController) {
        this.fileManager = fileManager;
        this.uiController = uiController;
    }

    async chat(message) {
        const removeLoading = showLoadingState(document.querySelector('.input-container'), 'input');

        try {
            await sessionService.ensureChat();

            const currentHistory = document.querySelector('#history-list .selected');
            if (currentHistory && currentHistory.querySelector('span').textContent === "New Chat") {
                currentHistory.querySelector('span').textContent = message || "Files uploaded";
            }

            const formData = this.fileManager.getFormData();
            formData.append('message', message);

            const response = await fetch('/message', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Chat request failed');
            }

            this.fileManager.clear();
            this.uiController.actor.send({ type: 'INPUT' });
            removeLoading();
        } catch (error) {
            console.error('Error in chat:', error);
            removeLoading();
        }
    }

    async interrupt() {
        try {
            const response = await fetch('/interrupt', {
                method: 'POST'
            });

            if (!response.ok) {
                console.error('Interrupt request failed');
                return false;
            }

            this.uiController.actor.send({ type: 'INTERRUPT' });
            return true;
        } catch (error) {
            console.error('Error during interrupt:', error);
            return false;
        }
    }

    async sendmsg(message) {
        const formData = this.fileManager.getFormData();
        formData.append('message', message);

        try {
            const response = await fetch('/sendmsg', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                this.fileManager.clear();
                displayMsg("USER", message, 'chat-window');
                this.uiController.actor.send({ type: 'INPUT' });
                return true;
            }
            else {
                console.error('Network response was not ok');
                return false;
            }
        } catch (error) {
            console.error('Error:', error);
            return false;
        }
    }

}

export const chatService = new ChatService();