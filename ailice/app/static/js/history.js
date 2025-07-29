function createHistoryItem(txt, sessionName) {
    const historyItem = document.createElement('li');
    historyItem.dataset.sessionName = sessionName;

    const textSpan = document.createElement('span');
    textSpan.textContent = txt;
    textSpan.classList.add('history-span');

    const menuButton = document.createElement('button');
    menuButton.textContent = '⋮';
    menuButton.classList.add('menu-button');

    const dropdownMenu = document.createElement('div');
    dropdownMenu.classList.add('dropdown-menu');
    
    const downloadOption = document.createElement('a');
    downloadOption.textContent = 'Download';
    downloadOption.href = '#';
    downloadOption.addEventListener('click', (event) => {
        event.stopPropagation();
        event.preventDefault();
        window.sessionService.getHistory(sessionName, historyItem);
    });
    dropdownMenu.appendChild(downloadOption);
    
    const deleteOption = document.createElement('a');
    deleteOption.textContent = 'Delete';
    deleteOption.href = '#';
    deleteOption.addEventListener('click', (event) => {
        event.stopPropagation();
        event.preventDefault();
        window.sessionService.deleteHistory(sessionName, historyItem);
    });
    dropdownMenu.appendChild(deleteOption);

    historyItem.appendChild(textSpan);
    historyItem.appendChild(menuButton);
    historyItem.appendChild(dropdownMenu);
    historyItem.classList.add('history-item');

    function historyClickHandler() {
        window.sessionService.loadHistory(sessionName, historyItem);
    }
    historyItem.addEventListener('click', historyClickHandler);
    historyItem.historyClickHandler = historyClickHandler;

    menuButton.addEventListener('click', (event) => {
        event.stopPropagation();
        dropdownMenu.style.display = dropdownMenu.style.display === 'block' ? 'none' : 'block';
    });

    document.addEventListener('click', (event) => {
        if (!historyItem.contains(event.target)) {
            dropdownMenu.style.display = 'none';
        }
    });

    return historyItem;
}
