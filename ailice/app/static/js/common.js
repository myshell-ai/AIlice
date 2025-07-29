function showLoadingState(element, type) {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';

    switch (type) {
        case 'new-chat':
            const originalContent = element.textContent;
            element.textContent = '';
            element.appendChild(spinner);
            return () => {
                element.textContent = originalContent;
            };

        case 'history':
            const menuButton = element.querySelector('.menu-button');
            const originalHTML = menuButton.innerHTML;
            menuButton.innerHTML = '';
            menuButton.appendChild(spinner);
            menuButton.style.display = 'flex';
            menuButton.style.alignItems = 'center';
            menuButton.style.justifyContent = 'center';
            return () => {
                menuButton.innerHTML = originalHTML;
            };

        case 'input':
            const textArea = element;
            const spinnerContainer = document.createElement('div');
            spinnerContainer.style.position = 'absolute';
            spinnerContainer.style.display = 'flex';
            spinnerContainer.style.alignItems = 'center';
            spinnerContainer.style.pointerEvents = 'none';
            spinnerContainer.appendChild(spinner);

            textArea.parentElement.style.position = 'relative';
            textArea.parentElement.appendChild(spinnerContainer);

            const positionSpinner = () => {
                const textAreaRect = textArea.getBoundingClientRect();
                const parentRect = textArea.parentElement.getBoundingClientRect();

                const rightOffset = parentRect.right - textAreaRect.right;

                spinnerContainer.style.right = `${rightOffset + 10}px`;

                const topOffset = textAreaRect.top - parentRect.top;
                const textAreaHeight = textAreaRect.height;
                spinnerContainer.style.top = `${topOffset + textAreaHeight / 2}px`;
                spinnerContainer.style.transform = 'translateY(-50%)';
            };

            positionSpinner();

            const resizeObserver = new ResizeObserver(positionSpinner);
            resizeObserver.observe(textArea);

            return () => {
                resizeObserver.disconnect();
                spinnerContainer.remove();
            };
    }
}