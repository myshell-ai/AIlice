class MediaPlaceholder extends HTMLElement {
    constructor() {
        super();
        this.hasStartedLoading = false;
    }

    connectedCallback() {
        if (this.hasStartedLoading) {
            return;
        }
        this.hasStartedLoading = true;
        this.loadAndReplace();
    }

    async loadAndReplace() {
        const href = this.dataset.href;
        const title = this.dataset.title;
        const text = this.dataset.text;

        try {
            const mediaType = href.startsWith("blob:") ? text :
                await getContentType(convertToProxyURL(href));

            if (!this.isConnected) {
                return;
            }

            let containerHTML = '<div class="media-container" style="position: relative; display: inline-block;">';

            const fileName = href.split('/').pop() || 'file';

            if (mediaType.startsWith('image')) {
                containerHTML += `<img src="${convertToProxyURL(href)}" alt="${text}" title="${title}" 
                    style="max-width: 100%; height: auto; display: block;"
                    onerror="this.onerror=null; this.innerHTML='Failed to load image';">`;
            } else if (mediaType.startsWith('audio')) {
                containerHTML += `<audio controls><source src="${convertToProxyURL(href)}" type="${mediaType}">Your browser does not support the audio element.</audio>`;
            } else if (mediaType.startsWith('video')) {
                containerHTML += `<video controls><source src="${convertToProxyURL(href)}" type="${mediaType}">Your browser does not support the video element.</video>`;
            } else {
                containerHTML += `
                    <div class="file-preview" style="display: flex; align-items: center; padding: 10px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9; max-width: 300px;">
                        <div style="font-size: 32px; margin-right: 15px;">📄</div>
                        <div style="overflow: hidden; text-overflow: ellipsis;">
                            <div style="font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${fileName}</div>
                            <div style="font-size: 12px; color: #666;">Click to Download</div>
                        </div>
                    </div>`;
            }

            containerHTML += `
                <button class="download-media-btn" data-href="${convertToProxyURL(href)}" data-filename="${fileName}">
                    <span class="download-icon">⬇️</span>Download
                </button>
            </div>`;

            if (this.isConnected) {
                this.outerHTML = containerHTML;

                setTimeout(() => {
                    document.querySelectorAll('.download-media-btn').forEach(btn => {
                        if (!btn.hasListener) {
                            btn.hasListener = true;
                            btn.addEventListener('click', function (e) {
                                e.stopPropagation();
                                const url = this.getAttribute('data-href');
                                const fileName = this.getAttribute('data-filename');
                                downloadMedia(url, fileName);
                            });
                        }
                    });
                }, 0);
            }
        } catch (error) {
            console.error('Error loading media:', error);
            if (this.isConnected) {
                this.innerHTML = 'Failed to load media';
                this.style.color = 'red';
            }
        }
    }
}

customElements.define('media-placeholder', MediaPlaceholder);


function convertToProxyURL(href) {
    if (href.startsWith("/proxy?href=")) {
        return href
    }
    else if (href.startsWith("blob:")) {
        return href
    }
    else {
        const encodedURL = encodeURIComponent(href);
        return `/proxy?href=${encodedURL}`;
    }
}


async function getContentType(url) {
    try {
        const extension = url.split('.').pop().toLowerCase();
        if (['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'aiff', 'wma', 'opus', 'ra', 'mid'].includes(extension)) {
            return `audio/${extension}`;
        } else if (['mp4', 'webm', 'ogg', 'wmv', 'mov', 'avi', 'flv', 'mkv', 'mpeg', 'vob', 'rm', '3gp', 'ogv', 'm4v', 'h264', 'ts', 'm2ts', 'divx'].includes(extension)) {
            return `video/${extension}`;
        } else if (['jpg', 'jpeg', 'bmp', 'png', 'gif', 'tiff', 'tif', 'webp', 'svg', 'heif', 'heic', 'raw'].includes(extension)) {
            return `image/${extension}`;
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        const response = await fetch(url, {
            method: 'HEAD',
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (response.ok) {
            return response.headers.get("Content-Type");
        }
        throw new Error("Failed to fetch Content-Type");
    } catch (error) {
        console.error("Error getting content type:", error);
        return "";
    }
}

function mathsExpression(expr, force) {
    if (expr.match(/^\$\$[\s\S]*\$\$$/)) {
        expr = expr.substr(2, expr.length - 4);
        return [`$$${expr}$$`, true];
    } else if (expr.match(/^\$[\s\S]*\$$/)) {
        expr = expr.substr(1, expr.length - 2);
        return [`\\(${expr}\\)`, true];
    } else if (force) {
        return [`$$${expr}$$`, true];
    }
    else {
        return [expr, false]
    }
}

function downloadMedia(url, fileName) {
    fetch(url)
        .then(response => response.blob())
        .then(blob => {
            const a = document.createElement('a');
            const objectUrl = URL.createObjectURL(blob);
            a.href = objectUrl;
            a.download = fileName;
            a.click();
            URL.revokeObjectURL(objectUrl);
        })
        .catch(error => {
            console.error('Error downloading media:', error);
            alert('Failed to download media');
        });
}