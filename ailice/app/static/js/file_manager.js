class FileManager {
    constructor() {
        this.files = {
            perception: [],
            processing: []
        };
        this.init();
    }

    init() {
        this.fileButton = document.getElementById('file-button');
        this.fileMenu = document.getElementById('file-menu');
        this.fileInput = document.getElementById('file-input');
        this.cameraInput = document.getElementById('camera-input');
        this.videoInput = document.getElementById('video-input');
        this.filePreview = document.getElementById('upload-preview');
        this.fileList = document.getElementById('file-list');
        this.textInput = document.getElementById('text-input');

        this.bindEvents();
    }

    bindEvents() {
        this.fileButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleMenu();
        });

        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                this.handleMenuAction(action);
                this.hideMenu();
            });
        });

        this.fileInput.addEventListener('change', (e) => this.handleFiles(e.target.files));
        this.cameraInput.addEventListener('change', (e) => this.handleFiles(e.target.files));
        this.videoInput.addEventListener('change', (e) => this.handleFiles(e.target.files));

        document.addEventListener('click', () => this.hideMenu());
        this.fileMenu.addEventListener('click', (e) => e.stopPropagation());

        this.fileList.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-btn')) {
                e.stopPropagation();
                const id = parseFloat(e.target.dataset.id);
                this.removeFile(id);
            }
        });
    }

    toggleMenu() {
        this.fileMenu.classList.toggle('show');
    }

    hideMenu() {
        this.fileMenu.classList.remove('show');
    }

    handleMenuAction(action) {
        switch (action) {
            case 'file':
                this.fileInput.click();
                break;
            case 'camera':
                this.cameraInput.click();
                break;
            case 'video':
                this.videoInput.click();
                break;
        }
    }

    handleFiles(files) {
        Array.from(files).forEach(file => this.addFile(file));
        this.updatePreview();
    }

    addFile(file) {
        const category = this.categorizeFile(file);
        const fileObj = {
            file: file,
            id: Date.now() + Math.random(),
            name: file.name,
            type: file.type,
            category: category
        };

        this.files[category].push(fileObj);
    }

    categorizeFile(file) {
        if (file.type.startsWith('image/')) return 'perception';
        if (file.type.startsWith('video/')) return 'perception';
        if (file.source === 'recording') return 'perception';
        return 'processing';
    }

    removeFile(id) {
        Object.keys(this.files).forEach(category => {
            this.files[category] = this.files[category].filter(f => f.id !== id);
        });
        this.updatePreview();
    }

    updatePreview() {
        const allFiles = [...this.files.perception, ...this.files.processing];

        if (allFiles.length === 0) {
            this.filePreview.classList.remove('show');
            this.fileList.innerHTML = '';
            return;
        }

        this.filePreview.classList.add('show');
        this.fileList.innerHTML = allFiles.map(file => this.createFileItem(file)).join('');
    }

    createFileItem(file) {
        const icon = this.getFileIcon(file.type);
        const name = file.name.length > 10 ? file.name.substring(0, 10) + '...' : file.name;

        return `
            <div class="file-item">
                <span class="file-icon">${icon}</span>
                <span class="file-name">${name}</span>
                <button class="delete-btn" data-id="${file.id}">×</button>
            </div>
        `;
    }

    getFileIcon(type) {
        if (type.startsWith('image/')) return '🖼️';
        if (type.startsWith('video/')) return '🎥';
        if (type.startsWith('audio/')) return '🎵';
        if (type.includes('pdf')) return '📄';
        if (type.includes('text')) return '📝';
        return '📎';
    }

    getFormData() {
        const formData = new FormData();

        this.files.perception.forEach(f => {
            formData.append('files_for_perception[]', f.file);
        });

        this.files.processing.forEach(f => {
            formData.append('files_for_processing[]', f.file);
        });

        return formData;
    }

    clear() {
        this.files.perception = [];
        this.files.processing = [];
        this.updatePreview();
    }
}

export const fileManager = new FileManager();