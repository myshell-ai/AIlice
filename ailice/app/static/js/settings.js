
let pendingPatches = [];

function addPatch(path, value) {
    const existingPatchIndex = pendingPatches.findIndex(patch =>
        JSON.stringify(patch.path) === JSON.stringify(path)
    );

    if (existingPatchIndex !== -1) {
        pendingPatches[existingPatchIndex].value = value;
    } else {
        pendingPatches.push({
            op: 'replace',
            path: path,
            value: value
        });
    }
}

function addRemovePatch(path) {
    pendingPatches.push({
        op: 'remove',
        path: path
    });
}

function addAddPatch(path, value) {
    pendingPatches.push({
        op: 'add',
        path: path,
        value: value
    });
}

document.getElementById('settings-button').addEventListener('click', function () {
    pendingPatches = [];

    fetch('/get_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ patches: [] })
    })
        .then(response => response.json())
        .then(data => {
            populateSettingsForm(data.schema);
            document.getElementById('settings-modal').style.display = 'block';
        })
        .catch(error => {
            console.error('Error fetching settings:', error);
        });
    setTimeout(addResetButton, 100);
});

document.querySelector('.close').addEventListener('click', function () {
    document.getElementById('settings-modal').style.display = 'none';
});

window.addEventListener('click', function (event) {
    const modal = document.getElementById('settings-modal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
});

document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', function () {
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        this.classList.add('active');
        const tabId = this.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
    });
});

document.getElementById('save-settings').addEventListener('click', function () {
    if (pendingPatches.length === 0) {
        document.getElementById('settings-modal').style.display = 'none';
        return;
    }

    if (confirm('Are you sure you want to save these settings? This may affect the behavior of the AI.')) {
        fetch('/update_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ patches: pendingPatches })
        })
            .then(response => response.json())
            .then(data => {
                pendingPatches = [];
                document.getElementById('settings-modal').style.display = 'none';
                window.uiController.actor.send({ type: 'SETUP' });
                showNotification('Settings saved successfully!');
            })
            .catch(error => {
                console.error('Error saving settings:', error);
                showNotification('Failed to save settings!', 'error');
            });
    }
});

document.getElementById('cancel-settings').addEventListener('click', function () {
    pendingPatches = [];
    document.getElementById('settings-modal').style.display = 'none';
});

function renderUIComponent(schema, container) {
    if (!schema) return null;

    if (container.hasAttribute('data-disabled') && schema.disabled !== true) {
        schema.disabled = true;
    }

    switch (schema.type) {
        case 'section': return renderSection(schema, container);
        case 'card': return renderCard(schema, container);
        case 'formGroup': return renderFormGroup(schema, container);
        case 'formRow': return renderFormRow(schema, container);
        case 'button': return renderButton(schema, container);
        case 'checkbox': return renderCheckbox(schema, container);
        case 'range': return renderRangeSlider(schema, container);
        case 'table': return renderTable(schema, container);
        case 'tabs': return renderTabs(schema, container);
        default:
            console.warn(`Unknown component type: ${schema.type}`);
            return null;
    }
}

function renderSection(schema, container) {
    const { id, title, description, content, disabled } = schema;

    const html = `
    <div id="${id || ''}" class="settings-section ${disabled ? 'disabled-section' : ''}" ${disabled ? 'data-disabled="true"' : ''}>
    ${title ? `<h3>${title}</h3>` : ''}
    ${description ? `<p>${description}</p>` : ''}
    </div>
`;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const section = tempDiv.firstElementChild;

    if (content) {
        if (Array.isArray(content)) {
            content.forEach(item => renderUIComponent(item, section));
        } else {
            renderUIComponent(content, section);
        }
    }

    container.appendChild(section);
    return section;
}

function renderCard(schema, container) {
    const { id, title, removable, collapsible, content, onRemove, disabled } = schema;

    const html = `
    <div id="${id || ''}" class="model-card ${disabled ? 'disabled-card' : ''}" ${disabled ? 'data-disabled="true"' : ''}>
    <div class="model-card-header">
        <div class="model-card-title">${title}</div>
        <div class="model-card-actions">
        ${removable && !disabled ? '<button class="remove-button">Remove</button>' : ''}
        ${collapsible ? '<button class="collapse-button">►</button>' : ''}
        </div>
    </div>
    <div class="model-card-body ${collapsible ? 'collapsed' : ''}"></div>
    </div>
    `;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const card = tempDiv.firstElementChild;
    const cardBody = card.querySelector('.model-card-body');
    const cardHeader = card.querySelector('.model-card-header');

    if (removable && !disabled) {
        const removeButton = card.querySelector('.remove-button');
        const removeHandler = typeof onRemove === 'string' ? handleSchemaEvent(onRemove) : onRemove;
        if (typeof removeHandler === 'function') {
            removeButton.addEventListener('click', function (e) {
                e.stopPropagation();
                removeHandler();
            });
        }
    }

    if (collapsible) {
        const collapseButton = card.querySelector('.collapse-button');

        cardHeader.addEventListener('click', () => {
            cardBody.classList.toggle('collapsed');
            collapseButton.textContent = cardBody.classList.contains('collapsed') ? '►' : '▼';
        });

        collapseButton.addEventListener('click', (e) => {
            e.stopPropagation();
            cardBody.classList.toggle('collapsed');
            collapseButton.textContent = cardBody.classList.contains('collapsed') ? '►' : '▼';
        });
    }

    if (content) {
        if (Array.isArray(content)) {
            content.forEach(item => renderUIComponent(item, cardBody));
        } else {
            renderUIComponent(content, cardBody);
        }
    }

    container.appendChild(card);
    return card;
}

function renderComboboxOptions(dropdown, optionsToShow, allOptions, input, path, onChange) {
    dropdown.innerHTML = optionsToShow.map(option =>
        `<div class="combobox-option" data-value="${option.value}">${option.label}</div>`
    ).join('');

    dropdown.querySelectorAll('.combobox-option').forEach(opt => {
        opt.addEventListener('click', () => {
            const selectedValue = opt.dataset.value;
            const selectedOption = allOptions.find(o => o.value === selectedValue);
            input.value = selectedOption.label;
            dropdown.style.display = 'none';
            addPatch(path, selectedValue);

            if (onChange) {
                const changeHandler = typeof onChange === 'string' ? handleSchemaEvent(onChange) : onChange;
                if (typeof changeHandler === 'function') {
                    changeHandler(selectedValue);
                }
            }
        });

        opt.addEventListener('mouseenter', () => {
            opt.classList.add('combobox-option-hover');
        });
        opt.addEventListener('mouseleave', () => {
            opt.classList.remove('combobox-option-hover');
        });
    });
}

function renderFormGroup(schema, container) {
    const { id, label, inputType, value, options, disabled, onChange, tooltip, path } = schema;

    let html;
    if (inputType === 'select') {
        html = `
        <div class="form-group">
            <label for="${id}">
            ${label}
            ${tooltip ? `
                <span class="info-tooltip">ℹ️
                <span class="tooltip-text">${tooltip}</span>
                </span>
            ` : ''}
            </label>
            <div class="combobox-wrapper" style="position: relative;">
                <input type="text" 
                       id="${id}" 
                       class="form-control" 
                       value="${value ? (options.find(opt => opt.value === value)?.label || value) : ''}" 
                       ${disabled ? 'disabled' : ''} 
                       data-path='${JSON.stringify(path)}'
                       autocomplete="off">
                <div class="combobox-dropdown form-control" style="position: absolute; top: 100%; left: 0; right: 0; border-top: none; max-height: 200px; overflow-y: auto; z-index: 1000; display: none; padding: 0;">
                </div>
            </div>
        </div>
        `;
    } else {
        html = `
        <div class="form-group">
            <label for="${id}">
            ${label}
            ${tooltip ? `
                <span class="info-tooltip">ℹ️
                <span class="tooltip-text">${tooltip}</span>
                </span>
            ` : ''}
            </label>
            <input type="${inputType}" id="${id}" class="form-control" value="${value || ''}" ${disabled ? 'disabled' : ''} data-path='${JSON.stringify(path)}'>
        </div>
        `;
    }

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const element = tempDiv.firstElementChild;
    const input = element.querySelector('input') || element.querySelector('select');

    if (!disabled && path) {
        if (inputType === 'select') {
            const dropdown = element.querySelector('.combobox-dropdown');

            input.addEventListener('input', function () {
                const searchText = this.value.toLowerCase();
                const filteredOptions = options.filter(option =>
                    option.label.toLowerCase().includes(searchText)
                );
                renderComboboxOptions(dropdown, filteredOptions, options, input, path, onChange);
                dropdown.style.display = filteredOptions.length > 0 ? 'block' : 'none';
            });

            input.addEventListener('focus', function () {
                renderComboboxOptions(dropdown, options, options, input, path, onChange);
                dropdown.style.display = 'block';
            });

            input.addEventListener('blur', function () {
                setTimeout(() => {
                    dropdown.style.display = 'none';

                    let finalValue = this.value;
                    const matchedOption = options.find(opt =>
                        opt.label === finalValue || opt.value === finalValue
                    );
                    finalValue = matchedOption ? matchedOption.value : finalValue;

                    addPatch(path, finalValue);

                    if (onChange) {
                        const changeHandler = typeof onChange === 'string' ? handleSchemaEvent(onChange) : onChange;
                        if (typeof changeHandler === 'function') {
                            changeHandler(finalValue);
                        }
                    }
                }, 150);
            });

        } else {
            input.addEventListener('change', function () {
                let newValue = this.value;
                if (inputType === 'number') {
                    newValue = parseFloat(newValue);
                } else if (inputType === 'checkbox') {
                    newValue = this.checked;
                }
                addPatch(path, newValue);

                if (onChange) {
                    const changeHandler = typeof onChange === 'string' ? handleSchemaEvent(onChange) : onChange;
                    if (typeof changeHandler === 'function') {
                        changeHandler(newValue);
                    }
                }
            });
        }
    }

    container.appendChild(element);
    return element;
}

function renderFormRow(schema, container) {
    const { id, content, disabled } = schema;

    const html = `<div id="${id || ''}" class="form-row ${disabled ? 'disabled-row' : ''}" ${disabled ? 'data-disabled="true"' : ''}></div>`;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const row = tempDiv.firstElementChild;

    if (content) {
        if (Array.isArray(content)) {
            content.forEach(item => renderUIComponent(item, row));
        } else {
            renderUIComponent(content, row);
        }
    }

    container.appendChild(row);
    return row;
}

function renderButton(schema, container) {
    const { id, text, className, icon, onClick, disabled } = schema;

    const html = `
        <button id="${id || ''}" class="${className || 'add-button'}" ${disabled ? 'disabled' : ''}>
        ${icon ? `<span>${icon}</span>` : ''}
        ${text}
        </button>
    `;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const button = tempDiv.firstElementChild;

    if (onClick && !disabled) {
        const clickHandler = typeof onClick === 'string' ? handleSchemaEvent(onClick) : onClick;
        if (typeof clickHandler === 'function') {
            button.addEventListener('click', clickHandler);
        }
    }

    container.appendChild(button);
    return button;
}

function renderCheckbox(schema, container) {
    const { id, label, checked, onChange, disabled, path } = schema;

    const html = `
    <div class="form-group ${disabled ? 'disabled-form-group' : ''}" style="display: flex; align-items: center;">
    <label for="${id}" style="margin-right: 12px; margin-bottom: 0;">${label}</label>
    <input type="checkbox" id="${id}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''} style="width: 20px; height: 20px;" data-path='${JSON.stringify(path)}'>
    </div>
`;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const element = tempDiv.firstElementChild;
    const checkbox = element.querySelector('input');

    if (!disabled && path) {
        checkbox.addEventListener('change', function (e) {
            addPatch(path, this.checked);

            if (onChange) {
                const changeHandler = typeof onChange === 'string' ? handleSchemaEvent(onChange) : onChange;
                if (typeof changeHandler === 'function') {
                    changeHandler(this.checked);
                }
            }
        });
    }

    container.appendChild(element);
    return element;
}

function renderRangeSlider(schema, container) {
    const { id, label, min, max, step, value, tooltip, onChange, disabled, path } = schema;

    const html = `
            <div class="form-group ${disabled ? 'disabled-form-group' : ''}">
            <label for="${id}">
                ${label}
                ${tooltip ? `
                <span class="info-tooltip">ℹ️
                    <span class="tooltip-text">${tooltip}</span>
                </span>
                ` : ''}
            </label>
            <div style="display: flex; align-items: center;">
                <input type="range" id="${id}" class="form-control" 
                    min="${min}" max="${max}" step="${step}" value="${value}" ${disabled ? 'disabled' : ''} data-path='${JSON.stringify(path)}'>
                <span id="${id}-value" style="margin-left: 10px;">${value}</span>
            </div>
            </div>
        `;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const element = tempDiv.firstElementChild;
    const slider = element.querySelector('input');
    const valueDisplay = element.querySelector(`#${id}-value`);

    if (!disabled && path) {
        slider.addEventListener('input', function () {
            valueDisplay.textContent = this.value;
            const numValue = parseFloat(this.value);
            addPatch(path, numValue);

            if (onChange) {
                const changeHandler = typeof onChange === 'string' ? handleSchemaEvent(onChange) : onChange;
                if (typeof changeHandler === 'function') {
                    changeHandler(numValue);
                }
            }
        });
    }

    container.appendChild(element);
    return element;
}

function renderTable(schema, container) {
    const { id, columns, rows, disabled } = schema;

    const html = `
    <table id="${id || ''}" class="settings-table ${disabled ? 'disabled-table' : ''}" 
        style="width: 100%; border-collapse: collapse; margin: 10px 0;" ${disabled ? 'data-disabled="true"' : ''}>
    <thead>
        <tr>
        ${columns.map(col => `<th style="text-align: left; padding: 8px; border-bottom: 1px solid var(--border-color);">${col}</th>`).join('')}
        </tr>
    </thead>
    <tbody></tbody>
    </table>
`;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const table = tempDiv.firstElementChild;
    const tbody = table.querySelector('tbody');

    rows.forEach(row => {
        const tr = document.createElement('tr');

        row.cells.forEach(cell => {
            const td = document.createElement('td');
            td.style.padding = '8px';
            td.style.borderBottom = '1px solid var(--border-color)';

            if (typeof cell === 'object') {
                // Propagate disabled state to cell contents
                if (disabled && !cell.disabled) {
                    cell.disabled = true;
                }
                renderUIComponent(cell, td);
            } else {
                td.textContent = cell;
            }

            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });

    container.appendChild(table);
    return table;
}

function renderTabs(schema, container) {
    const { id, tabs, activeTab } = schema;

    const html = `
        <div id="${id || ''}" class="tabs-container">
        <div class="modal-tabs">
            ${tabs.map(tab => `
            <button class="tab-button ${tab.id === activeTab ? 'active' : ''}" data-tab="${tab.id}">
                ${tab.title}
            </button>
            `).join('')}
        </div>
        <div class="tabs-content"></div>
        </div>
    `;

    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    const tabsContainer = tempDiv.firstElementChild;
    const tabsContent = tabsContainer.querySelector('.tabs-content');

    tabs.forEach(tab => {
        const contentDiv = document.createElement('div');
        contentDiv.id = tab.id;
        contentDiv.className = `tab-content ${tab.id === activeTab ? 'active' : ''}`;
        tabsContent.appendChild(contentDiv);

        if (tab.content) {
            renderUIComponent(tab.content, contentDiv);
        }
    });

    const tabButtons = tabsContainer.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', function () {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            const tabId = this.getAttribute('data-tab');
            const tabContents = tabsContainer.querySelectorAll('.tab-content');
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');
        });
    });

    container.appendChild(tabsContainer);
    return tabsContainer;
}

function scrollToBottom(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        const modalBody = document.querySelector('.modal-body');
        if (modalBody) {
            modalBody.scrollTop = modalBody.scrollHeight;
        }
    }
}

function addNewAgentType(defaultModel) {
    fetchAgentTypes().then(agentTypes => {
        agentTypes.push("DEFAULT");

        const configuredAgentTypes = new Set();
        document.querySelectorAll('[id^="agent-model-"]').forEach(select => {
            const agent = select.id.replace('agent-model-', '');
            configuredAgentTypes.add(agent);
        });

        const availableTypes = agentTypes.filter(type => !configuredAgentTypes.has(type));

        if (availableTypes.length === 0) {
            showNotification('All available agent types are already configured', 'error');
            return;
        }

        createAgentTypeDialog(availableTypes, (selectedType) => {
            addAddPatch(['agentModelConfig', selectedType], defaultModel);

            fetch('/get_settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ patches: pendingPatches })
            })
                .then(response => response.json())
                .then(data => {
                    populateSettingsForm(data.schema);
                    setTimeout(() => scrollToBottom('agent-models'), 100);
                })
                .catch(error => {
                    console.error('Error updating settings:', error);
                });
        });
    });
}

function removeAgentType(agent) {
    if (confirm(`Are you sure you want to remove the "${agent}" agent configuration?`)) {
        addRemovePatch(['agentModelConfig', agent]);

        fetch('/get_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ patches: pendingPatches })
        })
            .then(response => response.json())
            .then(data => {
                populateSettingsForm(data.schema);
            })
            .catch(error => {
                console.error('Error updating settings:', error);
            });
    }
}

function addNewProvider() {
    const providerName = prompt('Enter provider name:');
    if (providerName) {
        const newProvider = {
            modelWrapper: 'AModelChatGPT',
            apikey: '',
            baseURL: 'https://api.openai.com/v1',
            modelList: {}
        };

        addAddPatch(['models', providerName], newProvider);

        fetch('/get_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ patches: pendingPatches })
        })
            .then(response => response.json())
            .then(data => {
                populateSettingsForm(data.schema);
            })
            .catch(error => {
                console.error('Error updating settings:', error);
            });
    }
}

function removeProvider(providerName) {
    if (confirm(`Are you sure you want to remove the provider "${providerName}"?`)) {
        addRemovePatch(['models', providerName]);

        fetch('/get_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ patches: pendingPatches })
        })
            .then(response => response.json())
            .then(data => {
                populateSettingsForm(data.schema);
            })
            .catch(error => {
                console.error('Error updating settings:', error);
            });
    }
}

function addNewModel(providerName) {
    const modelName = prompt('Enter model name:');
    if (modelName) {
        const newModel = {
            formatter: 'AFormatterGPT',
            contextWindow: 8192,
            systemAsUser: false,
            args: {}
        };

        addAddPatch(['models', providerName, 'modelList', modelName], newModel);

        fetch('/get_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ patches: pendingPatches })
        })
            .then(response => response.json())
            .then(data => {
                populateSettingsForm(data.schema);
            })
            .catch(error => {
                console.error('Error updating settings:', error);
            });
    }
}

function removeModel(providerName, modelName) {
    if (confirm(`Are you sure you want to remove the model "${modelName}"?`)) {
        addRemovePatch(['models', providerName, 'modelList', modelName]);

        fetch('/get_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ patches: pendingPatches })
        })
            .then(response => response.json())
            .then(data => {
                populateSettingsForm(data.schema);
            })
            .catch(error => {
                console.error('Error updating settings:', error);
            });
    }
}

function createAgentTypeDialog(agentTypes, onSelect) {
    const dialog = document.createElement('div');
    dialog.style.position = 'fixed';
    dialog.style.top = '50%';
    dialog.style.left = '50%';
    dialog.style.transform = 'translate(-50%, -50%)';
    dialog.style.backgroundColor = 'var(--bg-secondary)';
    dialog.style.padding = '20px';
    dialog.style.borderRadius = '8px';
    dialog.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
    dialog.style.zIndex = '3000';
    dialog.style.minWidth = '300px';

    const dialogTitle = document.createElement('h3');
    dialogTitle.textContent = 'Select Agent Type';
    dialogTitle.style.marginTop = '0';
    dialog.appendChild(dialogTitle);

    const select = document.createElement('select');
    select.className = 'form-control';
    select.style.marginBottom = '16px';

    agentTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        select.appendChild(option);
    });

    dialog.appendChild(select);

    const buttonContainer = document.createElement('div');
    buttonContainer.style.display = 'flex';
    buttonContainer.style.justifyContent = 'flex-end';
    buttonContainer.style.gap = '8px';

    const cancelButton = document.createElement('button');
    cancelButton.className = 'cancel-button';
    cancelButton.textContent = 'Cancel';
    cancelButton.addEventListener('click', () => {
        document.body.removeChild(dialog);
    });

    const addButton = document.createElement('button');
    addButton.className = 'save-button';
    addButton.textContent = 'Add';
    addButton.addEventListener('click', () => {
        const selectedType = select.value;
        onSelect(selectedType);
        document.body.removeChild(dialog);
    });

    buttonContainer.appendChild(cancelButton);
    buttonContainer.appendChild(addButton);
    dialog.appendChild(buttonContainer);

    document.body.appendChild(dialog);
}

function populateSettingsForm(schema) {
    document.getElementById('agent-models').innerHTML = '';
    document.getElementById('model-providers').innerHTML = '';
    document.getElementById('inference').innerHTML = '';

    if (schema && schema.tabs) {
        schema.tabs.forEach(tab => {
            renderUIComponent(tab.content, document.getElementById(tab.id));
        });
    }
}

function handleSchemaEvent(eventStr) {
    if (typeof eventStr === 'string') {
        const match = eventStr.match(/^(\w+)\((.*)\)$/);
        if (match) {
            const funcName = match[1];
            const paramsStr = match[2];

            const params = paramsStr ? paramsStr.split(',').map(param => {
                param = param.trim();
                if ((param.startsWith("'") && param.endsWith("'")) ||
                    (param.startsWith('"') && param.endsWith('"'))) {
                    return param.substring(1, param.length - 1);
                }
                else if (!isNaN(param)) {
                    return Number(param);
                }
                return param;
            }) : [];

            if (typeof window[funcName] === 'function') {
                return function () {
                    window[funcName].apply(null, params);
                };
            }
        }
    }
    return eventStr;
}

function fetchAgentTypes() {
    return fetch('/list_agent_type')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch agent types');
            }
            return response.json();
        });
}

function addResetButton() {
    const modalFooter = document.querySelector('.modal-footer');

    if (document.getElementById('reset-settings')) {
        return;
    }

    const resetButton = document.createElement('button');
    resetButton.id = 'reset-settings';
    resetButton.className = 'cancel-button';
    resetButton.textContent = 'Reset';
    resetButton.style.marginRight = 'auto';

    resetButton.addEventListener('click', function () {
        if (confirm('Are you sure you want to reset all settings to their current values? Any changes you made will be lost.')) {
            pendingPatches = [];
            fetch('/get_settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ patches: [] })
            })
                .then(response => response.json())
                .then(data => {
                    populateSettingsForm(data.schema);
                    showNotification('Settings have been reset');
                })
                .catch(error => {
                    console.error('Error resetting settings:', error);
                });
        }
    });

    modalFooter.insertBefore(resetButton, modalFooter.firstChild);
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    notification.style.position = 'fixed';
    notification.style.bottom = '20px';
    notification.style.right = '20px';
    notification.style.padding = '12px 20px';
    notification.style.borderRadius = '6px';
    notification.style.zIndex = '3000';
    notification.style.fontSize = '14px';
    notification.style.fontWeight = '500';
    notification.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.1)';
    notification.style.transition = 'opacity 0.3s ease';

    if (type === 'success') {
        notification.style.backgroundColor = '#4caf50';
        notification.style.color = 'white';
    } else if (type === 'error') {
        notification.style.backgroundColor = '#f44336';
        notification.style.color = 'white';
    }

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}
