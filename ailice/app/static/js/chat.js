let chatIsAtBottom = true;
let historyIsAtBottom = true;

const colorPalette = {
    lightColors: [
        { bg: '#e8f5e9', border: '#c8e6c9' },
        { bg: '#e8eaf6', border: '#c5cae9' },
        { bg: '#fff3e0', border: '#ffe0b2' },
        { bg: '#e3f2fd', border: '#bbdefb' },
        { bg: '#f3e5f5', border: '#e1bee7' },
        { bg: '#fff8e1', border: '#ffecb3' },
        { bg: '#e0f7fa', border: '#b2ebf2' },
        { bg: '#fce4ec', border: '#f8bbd0' },
        { bg: '#dcedc8', border: '#c5e1a5' },
        { bg: '#ffebee', border: '#ffcdd2' }
    ],
    darkColors: [
        { bg: '#1f2d2d', border: '#2d4343' },
        { bg: '#2d1f3b', border: '#432d54' },
        { bg: '#1f2d1f', border: '#2d432d' },
        { bg: '#2d1f1f', border: '#432d2d' },
        { bg: '#1a1f3c', border: '#2d3154' },
        { bg: '#2d2d1f', border: '#43432d' },
        { bg: '#1f1f2d', border: '#2d2d43' },
        { bg: '#2d261f', border: '#43392d' },
        { bg: '#261f2d', border: '#392d43' },
        { bg: '#2d1f26', border: '#432d39' }
    ],
    assignedColors: new Map(),
    colorIndex: 0,

    getColorForRole: function (role) {
        const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
        const colors = isDarkMode ? this.darkColors : this.lightColors;

        if (!this.assignedColors.has(role)) {
            const colorSet = colors[this.colorIndex % colors.length];
            this.assignedColors.set(role, colorSet);
            this.colorIndex++;
        }
        return this.assignedColors.get(role);
    }
};

function hideWelcomeSection() {
    const welcomeSection = document.getElementById('welcome-section');
    if (welcomeSection) {
        welcomeSection.style.display = 'none';
    }
}

function displayMsg(role, message, windowID) {
    hideWelcomeSection();
    
    const roleType = role.split('_')[0];
    const roleMap = {
        "USER": "/static/User.JPG",
        "ASSISTANT": "/static/AIlice.png",
    };

    const colors = colorPalette.getColorForRole(role);

    const chatWindow = document.getElementById(windowID);
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${roleType} ${role}`;

    messageDiv.innerHTML = `
        <img src=${roleMap[roleType] || "/static/AIlice.png"} class="avatar">
        <div class="bubble" style="background-color: ${colors.bg}; border-color: ${colors.border}">
            ${renderMarkdown(message)}
        </div>
    `;

    chatWindow.appendChild(messageDiv);
    MathJax.typesetPromise([messageDiv.querySelector('.bubble')]);

    if ((windowID === 'chat-window' && chatIsAtBottom) ||
        (windowID === 'history-content' && historyIsAtBottom)) {
        document.getElementById(windowID).scrollTop = document.getElementById(windowID).scrollHeight;
    }
}

function readResponse(reader) {
    const decoder = new TextDecoder();
    let content = '';
    let internalContent = '';
    let lastBotMessageElement = null;
    let lastInternalElement = null;
    const chatWindow = document.getElementById('chat-window');
    const historyContent = document.getElementById('history-content');

    function read() {
        reader.read().then(({ done, value }) => {
            if (done) {
                window.uiController.actor.send({ type: 'RESPOND' });

                // Reset scroll flags when done
                chatIsAtBottom = true;
                historyIsAtBottom = true;
                return;
            }

            const text = decoder.decode(value, { stream: true });
            const lines = text.split('\n');

            lines.forEach(line => {
                if (line.startsWith('data: ')) {
                    const jsonString = line.replace('data: ', '');
                    try {
                        const responseObject = JSON.parse(jsonString);
                        const responseMessage = responseObject.message;
                        const roleType = responseObject.role.split('_')[0];
                        const roleHTML = "<span class='role'>" + responseObject.role + ": </span>";
                        const prefix = { "": roleHTML, "open": roleHTML, "append": "", "close": "" };
                        const breaks = { "": "<br><br>", "open": "<br><br>", "append": "", "close": "" };

                        lastInternalElement = historyContent.querySelector(`.message.${roleType}.${responseObject.role}:last-child .bubble`);
                        if (lastInternalElement) {

                            internalContent += (breaks[responseObject.action] + responseMessage);
                            lastInternalElement.innerHTML = renderMarkdown(internalContent);
                            MathJax.typesetPromise([lastInternalElement]);
                        } else {
                            internalContent = (prefix[responseObject.action] + responseMessage);
                            displayMsg(responseObject.role, internalContent, 'history-content');
                        }

                        if (historyIsAtBottom) {
                            historyContent.scrollTop = historyContent.scrollHeight;
                        }

                        if ((responseObject.msgType === "user-ailice") && (roleType != "SYSTEM")) {
                            lastBotMessageElement = chatWindow.querySelector(`.message.${roleType}.${responseObject.role}:last-child .bubble`);
                            if (lastBotMessageElement) {
                                content += (breaks[responseObject.action] + responseMessage);
                                lastBotMessageElement.innerHTML = renderMarkdown(content);
                                MathJax.typesetPromise([lastBotMessageElement]);
                            } else {
                                content = responseMessage;
                                displayMsg(responseObject.role, content, 'chat-window');
                            }

                            if (chatIsAtBottom) {
                                chatWindow.scrollTop = chatWindow.scrollHeight;
                            }
                        }
                    } catch (e) {
                        console.error("Error parsing JSON:", e);
                    }
                }
            });
            read();
        });
    }
    read();
}

function expandHistoryPanel() {
    const historyPanel = document.getElementById('history-panel');
    const chatWindow = document.getElementById('chat-window');
    
    chatWindow.style.flexBasis = '50%';
    historyPanel.style.flexBasis = '50%';
    historyPanel.classList.add('expanded');
}

function collapseHistoryPanel() {
    const historyPanel = document.getElementById('history-panel');
    const chatWindow = document.getElementById('chat-window');
    
    chatWindow.style.flexBasis = '100%';
    historyPanel.style.flexBasis = '0%';
    historyPanel.classList.remove('expanded');
}

function toggleHistoryPanel() {
    const historyPanel = document.getElementById('history-panel');
    if (historyPanel.classList.contains('expanded')) {
        collapseHistoryPanel();
    } else {
        expandHistoryPanel();
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const chatWindow = document.getElementById('chat-window');
    const historyContent = document.getElementById('history-content');
    const scrollThreshold = Math.max(15, Math.floor(chatWindow.clientHeight * 0.01));

    chatWindow.addEventListener('wheel', function () {
        isUserInitiatedScroll = true;
        setTimeout(() => { isUserInitiatedScroll = false; }, 100);
    });

    chatWindow.addEventListener('touchmove', function () {
        isUserInitiatedScroll = true;
        setTimeout(() => { isUserInitiatedScroll = false; }, 100);
    });

    chatWindow.addEventListener('keydown', function (e) {
        if ([33, 34, 35, 36, 38, 40].includes(e.keyCode)) {
            isUserInitiatedScroll = true;
            setTimeout(() => { isUserInitiatedScroll = false; }, 100);
        }
    });

    chatWindow.addEventListener('scroll', function () {
        chatIsAtBottom = chatWindow.scrollHeight - chatWindow.scrollTop - chatWindow.clientHeight < scrollThreshold;
    });

    historyContent.addEventListener('wheel', function () {
        isUserInitiatedScroll = true;
        setTimeout(() => { isUserInitiatedScroll = false; }, 100);
    });

    historyContent.addEventListener('touchmove', function () {
        isUserInitiatedScroll = true;
        setTimeout(() => { isUserInitiatedScroll = false; }, 100);
    });

    historyContent.addEventListener('keydown', function (e) {
        if ([33, 34, 35, 36, 38, 40].includes(e.keyCode)) {
            isUserInitiatedScroll = true;
            setTimeout(() => { isUserInitiatedScroll = false; }, 100);
        }
    });

    historyContent.addEventListener('scroll', function () {
        historyIsAtBottom = historyContent.scrollHeight - historyContent.scrollTop - historyContent.clientHeight < scrollThreshold;
    });
});