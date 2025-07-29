function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle.querySelector('.theme-icon');
    const themeText = themeToggle.querySelector('.theme-text');

    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme === 'dark' || savedTheme === null) {
        document.documentElement.setAttribute('data-theme', 'dark');
        themeIcon.textContent = '☀️';
        themeText.textContent = 'Light';
        if (savedTheme === null) {
            localStorage.setItem('theme', 'dark');
        }
    }

    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        if (currentTheme === 'dark') {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
            themeIcon.textContent = '🌙';
            themeText.textContent = 'Dark';
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            themeIcon.textContent = '☀️';
            themeText.textContent = 'Light';
        }

        colorPalette.assignedColors.clear();
        colorPalette.colorIndex = 0;

        const messages = document.querySelectorAll('.message');
        messages.forEach(message => {
            const role = Array.from(message.classList).find(c => c !== 'message' && c !== 'USER' && c !== 'ASSISTANT');
            const bubble = message.querySelector('.bubble');
            const colors = colorPalette.getColorForRole(role);
            bubble.style.backgroundColor = colors.bg;
            bubble.style.borderColor = colors.border;
        });
    });
}