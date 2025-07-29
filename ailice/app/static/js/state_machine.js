import { createMachine, createActor } from 'https://cdn.jsdelivr.net/npm/xstate@5.19.2/+esm';

function createUIStateMachine(initialState) {
    return createMachine({
        id: 'ui',
        initial: initialState,
        states: {
            busy: {
                on: {
                    READY: { target: 'ready' },
                    SETUP: { target: 'ready' }
                }
            },
            ready: {
                on: {
                    INPUT: { target: 'update' },
                    LOAD: { target: 'busy' },
                    DELETE: { target: 'busy' },
                    SETUP: { target: 'ready' }
                }
            },
            update: {
                on: {
                    RESPOND: { target: 'ready' },
                    INTERRUPT: { target: 'interrupt' },
                    STOP: { target: 'stop' },
                    SETUP: { target: 'ready' }
                }
            },
            interrupt: {
                on: {
                    INPUT: { target: 'update' },
                    STOP: { target: 'stop' },
                    SETUP: { target: 'ready' }
                }
            },
            stop: {
                on: {
                    RESPOND: { target: 'ready' },
                    LOAD: { target: 'busy' },
                    SETUP: { target: 'ready' }
                }
            }
        }
    });
}

function updateUI(state) {
    try {
        console.log("updateUI called with state:", state.value);
        document.getElementById('new-chat-button').disabled = (!state.matches('ready') && !state.matches('stop'));
        document.getElementById('text-input').disabled = (!state.matches('ready') && !state.matches('interrupt'));
        //document.getElementById('audio-button').disabled = (!state.matches('ready') && !state.matches('interrupt'));
        document.getElementById('file-button').disabled = (!state.matches('ready') && !state.matches('interrupt'));

        document.getElementById('interrupt-button').style.display = ((state.matches('update') || state.matches('interrupt')) ? 'inline-block' : 'none');
        document.getElementById('stop-button').disabled = !((state.matches('update') || state.matches('interrupt')));
        document.getElementById('stop-button').style.display = ((state.matches('update') || state.matches('interrupt')) ? 'inline-block' : 'none');

        var menubtns = document.getElementsByClassName('menu-button');
        for (var i = 0; i < menubtns.length; i++) {
            menubtns[i].disabled = !state.matches('ready');
        }

        var historyItems = document.getElementsByClassName('history-item');
        if (!state.matches('ready') && !state.matches('stop')) {
            for (var i = 0; i < historyItems.length; i++) {
                if (historyItems[i].historyClickHandler) {
                    historyItems[i].removeEventListener('click', historyItems[i].historyClickHandler);
                }
            }
        } else {
            for (var i = 0; i < historyItems.length; i++) {
                if (historyItems[i].historyClickHandler) {
                    historyItems[i].addEventListener('click', historyItems[i].historyClickHandler);
                }
            }
        }

        if (state.matches('ready')) {
            document.getElementById('text-input').placeholder = "Type a message... (Markdown/LaTeX/code highlighting Supported. Shift+Enter for new line)";
            collapseHistoryPanel();
        }

        if (state.matches('update')) {
            document.getElementById('interrupt-button').textContent = '⏹️';
            expandHistoryPanel();
        }

        if (state.matches('interrupt')) {
            document.getElementById('text-input').placeholder = "Send a message to the currently active agent.";
            document.getElementById('interrupt-button').textContent = 'Send';
        }
    } catch (e) {
        console.error("updateUI FAILED. Exception: ", e);
    }
}

export const uiController = {
    actor: null,

    init(initState = 'ready') {
        if (this.actor) {
            this.actor.stop();
        }
        
        const uiMachine = createUIStateMachine(initState);
        this.actor = createActor(uiMachine);
        
        this.actor.subscribe((state) => {
            updateUI(state);
        });
        
        this.actor.start();
        console.log("State machine started with state: ", initState);
        updateUI(this.actor.getSnapshot());
    }
};