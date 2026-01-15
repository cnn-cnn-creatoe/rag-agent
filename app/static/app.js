/**
 * 知识库助理 - 企业级前端逻辑
 * v2.0 - Agentic RAG + LangSmith + 企业级 UI
 */

// ============ 状态管理 ============
const state = {
    isLoading: false,
    isStreaming: false,
    selectedFiles: [],
    vectorstoreReady: false,
    documentCount: 0,  // 知识库文档数量
    abortController: null,
    currentStreamingElement: null,
    agenticEnabled: false,
    langsmithEnabled: false,
    hasMessages: false,
    loadingMessageIndex: 0,
    sidebarCollapsed: false,  // 侧边栏是否收起
    fileToDelete: null,  // 待删除的文件名
};

// ============ DOM 元素 ============
const elements = {
    // 状态指示
    statusPill: document.getElementById('status-pill'),
    statusText: document.getElementById('status-text'),
    chunkPill: document.getElementById('chunk-pill'),
    chunkCount: document.getElementById('chunk-count'),
    agenticPill: document.getElementById('agentic-pill'),
    langsmithPill: document.getElementById('langsmith-pill'),
    
    // 用户配置
    userId: document.getElementById('user-id'),
    threadId: document.getElementById('thread-id'),
    
    // 侧边栏
    sidebar: document.getElementById('sidebar'),
    sidebarToggle: document.getElementById('sidebar-toggle'),
    
    // 文件上传
    dropzone: document.getElementById('dropzone'),
    fileInput: document.getElementById('file-input'),
    selectedFiles: document.getElementById('selected-files'),
    selectedFilesList: document.getElementById('selected-files-list'),
    uploadBtn: document.getElementById('upload-btn'),
    
    // 文件列表
    fileList: document.getElementById('file-list'),
    fileCount: document.getElementById('file-count'),
    filesEmpty: document.getElementById('files-empty'),
    ingestBtn: document.getElementById('ingest-btn'),
    
    // 聊天
    chatMessages: document.getElementById('chat-messages'),
    welcomeState: document.getElementById('welcome-state'),
    messageInput: document.getElementById('message-input'),
    sendBtn: document.getElementById('send-btn'),
    stopBtn: document.getElementById('stop-btn'),
    saveToFile: document.getElementById('save-to-file'),
    fileName: document.getElementById('file-name'),
    useStream: document.getElementById('use-stream'),
    useAgentic: document.getElementById('use-agentic'),
    
    // 空知识库警告
    emptyKbWarning: document.getElementById('empty-kb-warning'),
    
    // 预览
    previewDrawer: document.getElementById('preview-drawer'),
    previewOverlay: document.getElementById('preview-overlay'),
    previewFilename: document.getElementById('preview-filename'),
    previewContent: document.getElementById('preview-content'),
    
    // 删除确认弹窗
    deleteModal: document.getElementById('delete-confirm-modal'),
    deleteModalMessage: document.getElementById('delete-confirm-message'),
};

// ============ 置信度配置 ============
const confidenceConfig = {
    high: { 
        label: UI_TEXTS.confidence.high.label, 
        class: 'confidence-high', 
        icon: '✓',
        description: UI_TEXTS.confidence.high.description
    },
    medium: { 
        label: UI_TEXTS.confidence.medium.label, 
        class: 'confidence-medium', 
        icon: '~',
        description: UI_TEXTS.confidence.medium.description
    },
    low: { 
        label: UI_TEXTS.confidence.low.label, 
        class: 'confidence-low', 
        icon: '!',
        description: UI_TEXTS.confidence.low.description
    },
};

// ============ Toast 通知 ============
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icons = {
        success: `<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
        error: `<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
        warning: `<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>`,
        info: `<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`
    };
    
    toast.innerHTML = `${icons[type] || icons.info}<span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastIn 0.25s ease reverse forwards';
        setTimeout(() => toast.remove(), 250);
    }, 4000);
}

// ============ API 调用 ============
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        state.vectorstoreReady = data.vectorstore_ready;
        state.documentCount = data.doc_count || 0;
        state.agenticEnabled = data.agentic_enabled;
        state.langsmithEnabled = data.langsmith_enabled;
        
        // 更新状态 Pill
        if (data.vectorstore_ready && data.doc_count > 0) {
            elements.statusPill.className = 'status-pill ready';
            elements.statusText.textContent = UI_TEXTS.status.vectorstoreReady;
        } else if (data.doc_count === 0) {
            elements.statusPill.className = 'status-pill pending';
            elements.statusText.textContent = UI_TEXTS.knowledgeBase.emptyCannotChat || UI_TEXTS.status.vectorstoreEmpty;
        } else {
            elements.statusPill.className = 'status-pill pending';
            elements.statusText.textContent = UI_TEXTS.status.vectorstoreEmpty;
        }
        
        // 文本块数量
        if (data.doc_count > 0) {
            elements.chunkPill.classList.remove('hidden');
            elements.chunkCount.textContent = data.doc_count;
        } else {
            elements.chunkPill.classList.add('hidden');
        }
        
        // Agentic 状态
        if (data.agentic_enabled) {
            elements.agenticPill.classList.remove('hidden');
            if (elements.useAgentic) {
                elements.useAgentic.checked = true;
            }
        }
        
        // LangSmith 状态
        if (data.langsmith_enabled) {
            elements.langsmithPill.classList.remove('hidden');
        }
        
        // 更新空知识库状态
        updateEmptyKbState();
        
    } catch (error) {
        console.error('Health check failed:', error);
        elements.statusPill.className = 'status-pill error';
        elements.statusText.textContent = UI_TEXTS.status.connectionFailed;
    }
}

/**
 * 更新空知识库状态防护
 */
function updateEmptyKbState() {
    const isEmpty = state.documentCount === 0;
    
    // 显示/隐藏空知识库警告
    if (elements.emptyKbWarning) {
        if (isEmpty) {
            elements.emptyKbWarning.classList.remove('hidden');
        } else {
            elements.emptyKbWarning.classList.add('hidden');
        }
    }
    
    // 禁用/启用输入框
    if (elements.messageInput) {
        elements.messageInput.disabled = isEmpty;
        if (isEmpty) {
            elements.messageInput.placeholder = UI_TEXTS.knowledgeBase.emptyWarning || '请先上传文档';
        } else {
            elements.messageInput.placeholder = UI_TEXTS.chat.inputPlaceholder;
        }
    }
    
    // 禁用/启用发送按钮
    if (elements.sendBtn) {
        elements.sendBtn.disabled = isEmpty;
    }
    
    // 禁用/启用严格模式
    if (elements.useAgentic) {
        elements.useAgentic.disabled = isEmpty;
        if (isEmpty) {
            elements.useAgentic.checked = false;
            showAgenticWarning(false);
        }
    }
    
    // 禁用/启用保存为文档
    if (elements.saveToFile) {
        elements.saveToFile.disabled = isEmpty;
        if (isEmpty) {
            elements.saveToFile.checked = false;
            if (elements.fileName) {
                elements.fileName.classList.add('hidden');
            }
        }
    }
}

async function loadFiles() {
    try {
        const response = await fetch('/files');
        const data = await response.json();
        
        elements.fileCount.textContent = formatText(UI_TEXTS.count.files, { n: data.count });
        
        if (data.files.length === 0) {
            elements.filesEmpty.classList.remove('hidden');
            elements.fileList.innerHTML = '';
            elements.fileList.appendChild(elements.filesEmpty);
            return;
        }
        
        elements.filesEmpty.classList.add('hidden');
        
        elements.fileList.innerHTML = data.files.map((file, index) => `
            <div class="file-item group" style="animation: slideIn 0.2s ease ${index * 0.03}s both">
                <div class="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 cursor-pointer" style="background: var(--bg-tertiary);" onclick="openPreview('${escapeHtml(file)}')">
                    <svg class="w-3.5 h-3.5" style="color: var(--text-muted);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                </div>
                <span class="text-xs truncate flex-1 cursor-pointer" style="color: var(--text-secondary);" onclick="openPreview('${escapeHtml(file)}')">${escapeHtml(file)}</span>
                <button class="delete-btn p-1 rounded hover:bg-black/20 transition-opacity" 
                        style="color: var(--text-muted);"
                        title="${UI_TEXTS.fileOps?.deleteTooltip || '删除此文档'}"
                        onclick="event.stopPropagation(); showDeleteConfirm('${escapeHtml(file)}')">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                </button>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load files:', error);
        showToast(UI_TEXTS.toast.error.network, 'error');
    }
}

async function uploadFiles() {
    if (state.selectedFiles.length === 0) {
        showToast(UI_TEXTS.upload.invalidFormat, 'warning');
        return;
    }
    
    setButtonLoading(elements.uploadBtn, true, UI_TEXTS.upload.uploading);
    disableControls(true);
    
    try {
        const formData = new FormData();
        state.selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        
        const response = await fetch('/upload?auto_ingest=true', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || UI_TEXTS.toast.error.upload);
        }
        
        const data = await response.json();
        showToast(formatText(UI_TEXTS.toast.success.upload, { count: state.selectedFiles.length }), 'success');
        
        state.selectedFiles = [];
        elements.selectedFiles.classList.add('hidden');
        elements.selectedFilesList.innerHTML = '';
        elements.fileInput.value = '';
        
        await Promise.all([checkHealth(), loadFiles()]);
        
    } catch (error) {
        console.error('Upload failed:', error);
        showToast(formatText(UI_TEXTS.toast.error.upload, { reason: error.message }), 'error');
    } finally {
        setButtonLoading(elements.uploadBtn, false, UI_TEXTS.upload.buttonText);
        disableControls(false);
    }
}

// ============ 侧边栏功能 ============
/**
 * 切换侧边栏展开/收起状态
 */
function toggleSidebar() {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    updateSidebarState();
    // 保存到 localStorage
    localStorage.setItem('sidebarCollapsed', state.sidebarCollapsed);
}

/**
 * 更新侧边栏 UI 状态
 */
function updateSidebarState() {
    const sidebar = elements.sidebar;
    const toggle = elements.sidebarToggle;
    
    if (!sidebar || !toggle) return;
    
    if (state.sidebarCollapsed) {
        sidebar.classList.add('sidebar-collapsed');
        toggle.classList.remove('expanded');
        toggle.classList.add('collapsed');
        toggle.title = UI_TEXTS.sidebar?.expandTooltip || '展开侧边栏';
    } else {
        sidebar.classList.remove('sidebar-collapsed');
        toggle.classList.remove('collapsed');
        toggle.classList.add('expanded');
        toggle.title = UI_TEXTS.sidebar?.collapseTooltip || '收起侧边栏';
    }
}

/**
 * 从 localStorage 恢复侧边栏状态
 */
function restoreSidebarState() {
    const saved = localStorage.getItem('sidebarCollapsed');
    if (saved !== null) {
        state.sidebarCollapsed = saved === 'true';
        updateSidebarState();
    }
}

// ============ 文件删除功能 ============
/**
 * 显示删除确认弹窗
 */
function showDeleteConfirm(filename) {
    state.fileToDelete = filename;
    
    const modal = elements.deleteModal;
    const message = elements.deleteModalMessage;
    
    if (modal) {
        // 更新弹窗消息
        if (message) {
            const msgTemplate = UI_TEXTS.fileOps?.deleteConfirmMessage || 
                '该操作将永久删除文档 "{filename}"，删除后不可恢复。删除完成后需要重新索引以更新知识库。';
            message.textContent = msgTemplate.replace('{filename}', filename);
        }
        modal.classList.remove('hidden');
    }
}

/**
 * 关闭删除确认弹窗
 */
function closeDeleteModal() {
    const modal = elements.deleteModal;
    if (modal) {
        modal.classList.add('hidden');
    }
    state.fileToDelete = null;
}

/**
 * 确认删除文件
 */
async function confirmDeleteFile() {
    const filename = state.fileToDelete;
    if (!filename) {
        closeDeleteModal();
        return;
    }
    
    closeDeleteModal();
    
    try {
        const response = await fetch(`/files/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '删除失败');
        }
        
        const data = await response.json();
        
        // 显示成功提示
        const successMsg = UI_TEXTS.fileOps?.deleteSuccess || '文档 {filename} 已删除，请重新索引';
        showToast(successMsg.replace('{filename}', filename), 'success');
        
        // 刷新文件列表
        await loadFiles();
        
        // 提示用户重新索引
        if (data.needs_reindex) {
            showToast('请点击"重新索引"按钮更新知识库', 'info');
        }
        
    } catch (error) {
        console.error('Delete file failed:', error);
        const errorMsg = UI_TEXTS.fileOps?.deleteFailed || '删除失败：{reason}';
        showToast(errorMsg.replace('{reason}', error.message), 'error');
    }
    
    state.fileToDelete = null;
}

// ============ 重新索引功能 ============
/**
 * 显示重新索引确认弹窗
 */
function showReindexConfirm() {
    const modal = document.getElementById('confirm-modal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

/**
 * 关闭确认弹窗
 */
function closeConfirmModal() {
    const modal = document.getElementById('confirm-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * 显示/隐藏索引状态栏
 */
function setIndexingStatus(show) {
    const statusBar = document.getElementById('indexing-status');
    if (statusBar) {
        if (show) {
            statusBar.classList.remove('hidden');
        } else {
            statusBar.classList.add('hidden');
        }
    }
}

/**
 * 确认重新索引
 */
async function confirmReindex() {
    closeConfirmModal();
    await ingestDocuments();
}

async function ingestDocuments() {
    setButtonLoading(elements.ingestBtn, true, UI_TEXTS.ingest.processing);
    setIndexingStatus(true);
    disableControls(true);
    
    try {
        const response = await fetch('/ingest', { method: 'POST' });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || UI_TEXTS.toast.error.ingest);
        }
        
        const data = await response.json();
        
        // 显示详细的索引完成信息
        const successMsg = formatText(UI_TEXTS.ingest.successDetail, {
            docCount: data.doc_count || data.processed || 0,
            chunkCount: data.chunk_count || data.added_chunks || 0
        });
        showToast(successMsg, 'success');
        
        await checkHealth();
        
    } catch (error) {
        console.error('Ingest failed:', error);
        showToast(formatText(UI_TEXTS.toast.error.ingest, { reason: error.message }), 'error');
    } finally {
        setButtonLoading(elements.ingestBtn, false, UI_TEXTS.ingest.buttonText);
        setIndexingStatus(false);
        disableControls(false);
    }
}

// ============ 聊天功能 ============
async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message) {
        showToast(UI_TEXTS.chat.empty, 'warning');
        return;
    }
    
    // 空知识库防护
    if (state.documentCount === 0) {
        showToast(UI_TEXTS.knowledgeBase?.emptyWarning || '当前知识库为空，请先上传并索引文档', 'warning');
        return;
    }
    
    if (!state.vectorstoreReady) {
        showToast(UI_TEXTS.chat.noKnowledge, 'warning');
        return;
    }
    
    // 隐藏欢迎状态
    if (!state.hasMessages) {
        elements.welcomeState.classList.add('hidden');
        state.hasMessages = true;
    }
    
    // 添加用户消息
    appendUserMessage(message);
    elements.messageInput.value = '';
    autoResizeTextarea();
    
    const useStream = elements.useStream.checked;
    const useAgentic = elements.useAgentic ? elements.useAgentic.checked : false;
    
    if (useAgentic) {
        await sendAgenticMessage(message);
    } else if (useStream) {
        await sendStreamMessage(message);
    } else {
        await sendNormalMessage(message);
    }
}

async function sendNormalMessage(message) {
    const loadingId = appendLoadingMessage();
    setButtonLoading(elements.sendBtn, true, '');
    disableControls(true);
    
    try {
        const requestBody = {
            user_id: elements.userId.value || 'user_001',
            thread_id: elements.threadId.value || 'thread_001',
            message: message,
            top_k: 5,
            save_to_file: elements.saveToFile.checked,
            save_as_document: elements.saveToFile.checked,
            file_name: elements.fileName.value || null
        };
        
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || UI_TEXTS.toast.error.chat);
        }
        
        const data = await response.json();
        
        document.getElementById(loadingId)?.remove();
        
        appendAssistantMessage(data);
        
        // 显示文档保存成功提示
        if (data.saved_document) {
            showToast(formatText(UI_TEXTS.toast.success.saveDocument, { filename: data.saved_document.filename }), 'success');
        } else if (data.saved_file) {
            showToast(formatText(UI_TEXTS.toast.success.save, { path: data.saved_file }), 'success');
        }
        
    } catch (error) {
        console.error('Send failed:', error);
        document.getElementById(loadingId)?.remove();
        appendErrorMessage(error.message);
        showToast(formatText(UI_TEXTS.toast.error.chat, { reason: error.message }), 'error');
    } finally {
        setButtonLoading(elements.sendBtn, false, UI_TEXTS.chat.sendButton);
        disableControls(false);
    }
}

async function sendAgenticMessage(message) {
    const loadingId = appendLoadingMessage(true);
    setButtonLoading(elements.sendBtn, true, '');
    disableControls(true);
    
    try {
        const requestBody = {
            user_id: elements.userId.value || 'user_001',
            thread_id: elements.threadId.value || 'thread_001',
            message: message,
            top_k: 5,
            save_to_file: elements.saveToFile.checked,
            save_as_document: elements.saveToFile.checked,
            file_name: elements.fileName.value || null,
            agentic_mode: true,
            max_loops: 2,
        };
        
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || UI_TEXTS.toast.error.chat);
        }
        
        const data = await response.json();
        
        document.getElementById(loadingId)?.remove();
        
        appendAgenticMessage(data);
        
        // 显示文档保存成功提示
        if (data.saved_document) {
            showToast(formatText(UI_TEXTS.toast.success.saveDocument, { filename: data.saved_document.filename }), 'success');
        } else if (data.saved_file) {
            showToast(formatText(UI_TEXTS.toast.success.save, { path: data.saved_file }), 'success');
        }
        
    } catch (error) {
        console.error('Agentic send failed:', error);
        document.getElementById(loadingId)?.remove();
        appendErrorMessage(error.message);
        showToast(formatText(UI_TEXTS.toast.error.chat, { reason: error.message }), 'error');
    } finally {
        setButtonLoading(elements.sendBtn, false, UI_TEXTS.chat.sendButton);
        disableControls(false);
    }
}

async function sendStreamMessage(message) {
    state.isStreaming = true;
    state.abortController = new AbortController();
    
    elements.sendBtn.classList.add('hidden');
    elements.stopBtn.classList.remove('hidden');
    disableControls(true);
    
    const msgId = 'msg-' + Date.now();
    const messageHtml = `
        <div id="${msgId}" class="message flex justify-start">
            <div class="message-assistant p-4 max-w-2xl">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-6 h-6 rounded-md flex items-center justify-center" style="background: var(--accent-subtle);">
                        <svg class="w-3.5 h-3.5" style="color: var(--accent-primary);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                        </svg>
                    </div>
                    <span class="text-xs font-medium" style="color: var(--accent-primary);">知识库助理</span>
                    <span id="${msgId}-confidence" class="confidence-tag hidden"></span>
                </div>
                <div id="${msgId}-content" class="prose text-sm streaming" style="color: var(--text-secondary);"></div>
                <div id="${msgId}-sources" class="hidden"></div>
            </div>
        </div>
    `;
    
    elements.chatMessages.insertAdjacentHTML('beforeend', messageHtml);
    smoothScrollToBottom();
    
    const contentElement = document.getElementById(`${msgId}-content`);
    state.currentStreamingElement = contentElement;
    
    let fullAnswer = '';
    let sources = [];
    let confidence = 'medium';
    
    try {
        const requestBody = {
            user_id: elements.userId.value || 'user_001',
            thread_id: elements.threadId.value || 'thread_001',
            message: message,
            top_k: 5,
            save_to_file: elements.saveToFile.checked,
            save_as_document: elements.saveToFile.checked,
        };
        
        const response = await fetch('/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
            signal: state.abortController.signal
        });
        
        if (!response.ok) {
            throw new Error(UI_TEXTS.toast.error.server);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data:')) {
                    try {
                        const data = JSON.parse(line.slice(5).trim());
                        
                        if (data.delta) {
                            fullAnswer += data.delta;
                            contentElement.innerHTML = formatMarkdown(fullAnswer);
                            smoothScrollToBottom();
                        }
                        
                        if (data.answer !== undefined) {
                            fullAnswer = data.answer;
                            sources = data.sources || [];
                            confidence = data.confidence || 'medium';
                            
                            // 处理文档保存结果
                            if (data.saved_document) {
                                showToast(formatText(UI_TEXTS.toast.success.saveDocument, { filename: data.saved_document.filename }), 'success');
                            }
                        }
                        
                        if (data.error) {
                            throw new Error(data.error);
                        }
                    } catch (e) {
                        if (e.message !== 'Unexpected end of JSON input') {
                            console.error('SSE parse error:', e);
                        }
                    }
                }
            }
        }
        
        contentElement.classList.remove('streaming');
        contentElement.innerHTML = formatMarkdown(fullAnswer);
        
        // 置信度标签
        const confidenceBadge = document.getElementById(`${msgId}-confidence`);
        if (confidenceBadge && confidence) {
            const config = confidenceConfig[confidence] || confidenceConfig.medium;
            confidenceBadge.className = `confidence-tag ${config.class}`;
            confidenceBadge.innerHTML = `<span>${config.icon}</span>${config.label}`;
            confidenceBadge.classList.remove('hidden');
        }
        
        // 来源
        if (sources.length > 0) {
            const sourcesContainer = document.getElementById(`${msgId}-sources`);
            sourcesContainer.innerHTML = buildSourcesHtml(sources, msgId);
            sourcesContainer.classList.remove('hidden');
        }
        
        // 低置信度提示
        if (confidence === 'low') {
            appendLowConfidenceHint(contentElement);
        }
        
    } catch (error) {
        if (error.name === 'AbortError') {
            contentElement.classList.remove('streaming');
            contentElement.innerHTML = formatMarkdown(fullAnswer + '\n\n*[已停止生成]*');
            showToast(UI_TEXTS.toast.info.stopped, 'info');
        } else {
            console.error('Stream failed:', error);
            contentElement.classList.remove('streaming');
            contentElement.innerHTML = `<span style="color: var(--color-error);">${UI_TEXTS.chat.error}: ${escapeHtml(error.message)}</span>`;
            showToast(formatText(UI_TEXTS.toast.error.chat, { reason: error.message }), 'error');
        }
    } finally {
        state.isStreaming = false;
        state.abortController = null;
        state.currentStreamingElement = null;
        
        elements.stopBtn.classList.add('hidden');
        elements.sendBtn.classList.remove('hidden');
        disableControls(false);
    }
}

function stopStreaming() {
    if (state.abortController) {
        state.abortController.abort();
    }
}

// ============ 文档预览 ============
async function openPreview(filename, highlightText = null) {
    try {
        const response = await fetch(`/doc?name=${encodeURIComponent(filename)}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || UI_TEXTS.preview.failed);
        }
        
        const data = await response.json();
        
        elements.previewFilename.textContent = data.name;
        
        let content = escapeHtml(data.content);
        
        if (highlightText) {
            const escapedHighlight = escapeHtml(highlightText);
            const regex = new RegExp(`(${escapeRegex(escapedHighlight.substring(0, 50))})`, 'gi');
            content = content.replace(regex, '<mark class="highlight">$1</mark>');
        }
        
        elements.previewContent.querySelector('pre').innerHTML = content;
        
        elements.previewDrawer.classList.add('open');
        elements.previewOverlay.classList.add('open');
        
    } catch (error) {
        console.error('Preview failed:', error);
        showToast(formatText(UI_TEXTS.toast.error.unknown, { reason: error.message }), 'error');
    }
}

function closePreview() {
    elements.previewDrawer.classList.remove('open');
    elements.previewOverlay.classList.remove('open');
}

// ============ UI 辅助函数 ============
function disableControls(disabled) {
    elements.uploadBtn.disabled = disabled;
    elements.ingestBtn.disabled = disabled;
    if (!state.isStreaming) {
        elements.sendBtn.disabled = disabled;
    }
}

function setButtonLoading(button, isLoading, text) {
    state.isLoading = isLoading;
    button.disabled = isLoading;
    
    const spinner = `
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
        `;
    
    if (isLoading) {
        if (button === elements.sendBtn) {
            button.innerHTML = spinner;
    } else {
            button.innerHTML = `${spinner}<span>${text}</span>`;
        }
    } else {
        if (button === elements.sendBtn) {
            button.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                </svg>
                ${text}
            `;
        } else if (button === elements.uploadBtn) {
            button.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
                </svg>
                ${text}
            `;
        } else if (button === elements.ingestBtn) {
            button.innerHTML = `
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                ${text}
            `;
        }
    }
}

function appendUserMessage(content) {
    const id = 'msg-' + Date.now();
    const messageHtml = `
        <div id="${id}" class="message flex justify-end">
            <div class="message-user p-3 max-w-xl">
                <p class="text-sm text-white">${escapeHtml(content)}</p>
            </div>
        </div>
    `;
    
    elements.chatMessages.insertAdjacentHTML('beforeend', messageHtml);
    smoothScrollToBottom();
}

function appendLoadingMessage(isAgentic = false) {
    const id = 'loading-' + Date.now();
    const bgColor = isAgentic ? 'rgba(168, 85, 247, 0.1)' : 'var(--accent-subtle)';
    const textColor = isAgentic ? 'var(--color-agentic)' : 'var(--accent-primary)';
    const loadingText = isAgentic ? UI_TEXTS.agentic.analyzing : getRandomLoadingMessage();
    
    // 启动加载文案轮播
    state.loadingMessageIndex = 0;
    
    const messageHtml = `
        <div id="${id}" class="message flex justify-start">
            <div class="message-assistant p-4">
                <div class="flex items-center gap-2 mb-3">
                    <div class="w-6 h-6 rounded-md flex items-center justify-center" style="background: ${bgColor};">
                        <svg class="w-3.5 h-3.5" style="color: ${textColor};" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                        </svg>
                </div>
                    <span class="text-xs font-medium" style="color: ${textColor};">知识库助理</span>
                    ${isAgentic ? `<span class="status-pill agentic text-xs"><span class="dot"></span>Agentic</span>` : ''}
                </div>
                <p id="${id}-text" class="text-xs mb-3" style="color: var(--text-muted);">${escapeHtml(loadingText)}</p>
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        </div>
    `;
    
    elements.chatMessages.insertAdjacentHTML('beforeend', messageHtml);
    smoothScrollToBottom();
    
    // 轮播加载文案
    const loadingInterval = setInterval(() => {
        const textElement = document.getElementById(`${id}-text`);
        if (!textElement) {
            clearInterval(loadingInterval);
            return;
        }
        state.loadingMessageIndex = (state.loadingMessageIndex + 1) % UI_TEXTS.loading.messages.length;
        textElement.textContent = UI_TEXTS.loading.messages[state.loadingMessageIndex];
    }, UI_TEXTS.loading.interval);
    
    // 清理函数
    const observer = new MutationObserver((mutations) => {
        if (!document.getElementById(id)) {
            clearInterval(loadingInterval);
            observer.disconnect();
        }
    });
    observer.observe(elements.chatMessages, { childList: true });
    
    return id;
}

function buildSourcesHtml(sources, msgId) {
    return `
        <div class="mt-4 pt-3 border-t" style="border-color: var(--border-subtle);">
            <div class="flex items-center justify-between mb-2">
                <button class="flex items-center gap-2 text-xs font-medium transition-colors" style="color: var(--accent-primary);" onclick="toggleSources('${msgId}')">
                    <svg class="w-3.5 h-3.5 transition-transform" id="${msgId}-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                    ${UI_TEXTS.sources.expandButton.replace('{count}', sources.length)}
                </button>
                <span class="text-xs" style="color: var(--text-disabled);">${UI_TEXTS.sources.evidenceCount.replace('{count}', sources.length)}</span>
                </div>
            <div class="overflow-hidden transition-all duration-300" id="${msgId}-sources-list" style="max-height: 0;">
                <!-- 证据来源声明 -->
                <div class="evidence-disclaimer mb-3">
                    <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <span>${UI_TEXTS.sources.disclaimer}</span>
                </div>
                <div class="space-y-2">
                        ${sources.map((s, i) => `
                        <div class="source-card">
                            <div class="flex items-center justify-between mb-2">
                                <div class="flex items-center gap-2">
                                    <svg class="w-3.5 h-3.5" style="color: var(--text-muted);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                                    </svg>
                                    <span class="text-xs font-medium" style="color: var(--text-primary);">${escapeHtml(s.source)}</span>
                                    <span class="text-xs font-mono" style="color: var(--text-disabled);">#${escapeHtml(s.chunk_id)}</span>
                                </div>
                                <div class="flex items-center gap-2">
                                    <span class="text-xs font-mono" style="color: var(--color-success);">${(s.score || 0).toFixed(2)}</span>
                                    <button onclick="openPreview('${escapeHtml(s.source)}', '${escapeHtml(s.snippet?.substring(0, 50) || '')}')" 
                                            class="text-xs hover:underline" style="color: var(--accent-primary);">
                                        ${UI_TEXTS.sources.viewOriginal}
                                    </button>
                                </div>
                                </div>
                            <p class="text-xs leading-relaxed" style="color: var(--text-muted);">${escapeHtml(s.snippet)}</p>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

function appendAssistantMessage(data) {
    const { answer, sources, confidence, saved_file, message_id } = data;
    const id = 'msg-' + Date.now();
    
    const config = confidenceConfig[confidence] || confidenceConfig.medium;
    const confidenceBadgeHtml = `<span class="confidence-tag ${config.class}"><span>${config.icon}</span>${config.label}</span>`;
    
    let sourcesHtml = sources && sources.length > 0 ? buildSourcesHtml(sources, id) : '';
    
    let savedFileHtml = '';
    if (saved_file) {
        savedFileHtml = `
            <div class="mt-3 flex items-center gap-2 p-2 rounded-md text-xs" style="background: rgba(34, 197, 94, 0.1); color: var(--color-success);">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                已保存至 <span class="font-mono">${escapeHtml(saved_file)}</span>
            </div>
        `;
    }
    
    let lowConfidenceHint = '';
    if (confidence === 'low') {
        lowConfidenceHint = buildLowConfidenceHtml();
    }
    
    const messageHtml = `
        <div id="${id}" class="message flex justify-start">
            <div class="message-assistant p-4 max-w-2xl">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-6 h-6 rounded-md flex items-center justify-center" style="background: var(--accent-subtle);">
                        <svg class="w-3.5 h-3.5" style="color: var(--accent-primary);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                        </svg>
                    </div>
                    <span class="text-xs font-medium" style="color: var(--accent-primary);">知识库助理</span>
                    ${confidenceBadgeHtml}
                </div>
                <div class="prose text-sm" style="color: var(--text-secondary);">
                    ${formatMarkdown(answer)}
                </div>
                ${lowConfidenceHint}
                ${savedFileHtml}
                ${sourcesHtml}
            </div>
        </div>
    `;
    
    elements.chatMessages.insertAdjacentHTML('beforeend', messageHtml);
    smoothScrollToBottom();
}

function appendAgenticMessage(data) {
    const { answer, sources, confidence, saved_file, reasoning_trace, loops_used } = data;
    const id = 'msg-' + Date.now();
    
    const config = confidenceConfig[confidence] || confidenceConfig.medium;
    const confidenceBadgeHtml = `<span class="confidence-tag ${config.class}"><span>${config.icon}</span>${config.label}</span>`;
    
    let sourcesHtml = sources && sources.length > 0 ? buildSourcesHtml(sources, id) : '';
    
    let savedFileHtml = '';
    if (saved_file) {
        savedFileHtml = `
            <div class="mt-3 flex items-center gap-2 p-2 rounded-md text-xs" style="background: rgba(34, 197, 94, 0.1); color: var(--color-success);">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                已保存至 <span class="font-mono">${escapeHtml(saved_file)}</span>
            </div>
        `;
    }
    
    // 推理轨迹
    let reasoningTraceHtml = '';
    if (reasoning_trace && reasoning_trace.length > 0) {
        const stepIcons = {
            retrieve: '🔍',
            draft: '✏️',
            critique: '🔎',
            refine: '🔄',
            finalize: '✓',
            error: '✕',
        };
        
        const stepsHtml = reasoning_trace.map(step => {
            const icon = stepIcons[step.step] || '•';
            let detail = '';
            if (step.query) detail = `：${step.query}`;
            if (step.decision) detail = `：${step.decision}`;
            
            return `
                <div class="reasoning-step">
                    <span class="icon">${icon}</span>
                    <span>${UI_TEXTS.reasoning.steps[step.step] || step.step}${detail}</span>
                </div>
            `;
        }).join('');
        
        reasoningTraceHtml = `
            <div class="reasoning-trace">
                <div class="flex items-center gap-2 text-xs font-medium mb-2" style="color: var(--color-agentic);">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                    </svg>
                    ${UI_TEXTS.reasoning.title} ${formatText(UI_TEXTS.reasoning.loops, { count: loops_used || 1 })}
                </div>
                ${stepsHtml}
            </div>
        `;
    }
    
    let lowConfidenceHint = '';
    if (confidence === 'low') {
        lowConfidenceHint = buildLowConfidenceHtml(true);
    }
    
    const messageHtml = `
        <div id="${id}" class="message flex justify-start">
            <div class="message-assistant p-4 max-w-2xl">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-6 h-6 rounded-md flex items-center justify-center" style="background: rgba(168, 85, 247, 0.1);">
                        <svg class="w-3.5 h-3.5" style="color: var(--color-agentic);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                        </svg>
                    </div>
                    <span class="text-xs font-medium" style="color: var(--color-agentic);">知识库助理</span>
                    <span class="status-pill agentic text-xs"><span class="dot"></span>Agentic</span>
                    ${confidenceBadgeHtml}
                </div>
                <div class="prose text-sm" style="color: var(--text-secondary);">
                    ${formatMarkdown(answer)}
                </div>
                ${lowConfidenceHint}
                ${savedFileHtml}
                ${reasoningTraceHtml}
                ${sourcesHtml}
            </div>
        </div>
    `;
    
    elements.chatMessages.insertAdjacentHTML('beforeend', messageHtml);
    smoothScrollToBottom();
}

function appendErrorMessage(error) {
    const id = 'msg-' + Date.now();
    const messageHtml = `
        <div id="${id}" class="message flex justify-start">
            <div class="message-assistant p-4 max-w-2xl" style="border-color: rgba(239, 68, 68, 0.2);">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-6 h-6 rounded-md flex items-center justify-center" style="background: rgba(239, 68, 68, 0.1);">
                        <svg class="w-3.5 h-3.5" style="color: var(--color-error);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                    <span class="text-xs font-medium" style="color: var(--color-error);">处理失败</span>
                </div>
                <p class="text-sm" style="color: var(--text-muted);">${escapeHtml(error)}</p>
            </div>
        </div>
    `;
    
    elements.chatMessages.insertAdjacentHTML('beforeend', messageHtml);
    smoothScrollToBottom();
}

function buildLowConfidenceHtml(isAgentic = false) {
    const suggestions = UI_TEXTS.lowConfidence.suggestions.map(s => `<li>${escapeHtml(s)}</li>`).join('');
    return `
        <div class="low-confidence-alert">
            <div class="flex items-start gap-2">
                <svg class="w-4 h-4 flex-shrink-0 mt-0.5" style="color: var(--color-error);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
                <div class="flex-1">
                    <p class="text-xs font-medium mb-1" style="color: var(--color-error);">${UI_TEXTS.lowConfidence.title}</p>
                    <p class="text-xs mb-2" style="color: var(--text-muted);">${UI_TEXTS.lowConfidence.message}</p>
                    <ul class="text-xs space-y-1" style="color: var(--text-muted); list-style: disc; padding-left: 1em;">
                        ${suggestions}
                    </ul>
                    ${isAgentic ? `<p class="text-xs mt-2" style="color: var(--text-disabled);">Agentic 模式已尝试多轮检索</p>` : ''}
                </div>
            </div>
        </div>
    `;
}

function appendLowConfidenceHint(container) {
    container.insertAdjacentHTML('afterend', buildLowConfidenceHtml());
}

function toggleSources(id) {
    const content = document.getElementById(`${id}-sources-list`);
    const arrow = document.getElementById(`${id}-arrow`);
    
    if (content.style.maxHeight === '0px' || !content.style.maxHeight) {
        content.style.maxHeight = content.scrollHeight + 'px';
        arrow.style.transform = 'rotate(90deg)';
    } else {
        content.style.maxHeight = '0';
        arrow.style.transform = 'rotate(0deg)';
    }
}

function smoothScrollToBottom() {
    const container = elements.chatMessages;
    container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth'
    });
}

function formatMarkdown(text) {
    if (!text) return '';
    
    let html = escapeHtml(text);
    
    // 代码块
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    
    // 行内代码
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // 标题
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    
    // 粗体
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // 斜体
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // 列表
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    
    // 数字列表
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    
    // 换行
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function autoResizeTextarea() {
    const textarea = elements.messageInput;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function updateSelectedFiles() {
    if (state.selectedFiles.length === 0) {
        elements.selectedFiles.classList.add('hidden');
        return;
    }
    
    elements.selectedFiles.classList.remove('hidden');
    elements.selectedFilesList.innerHTML = state.selectedFiles.map(file => `
        <div class="flex items-center gap-2">
            <svg class="w-3 h-3" style="color: var(--color-success);" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4"/>
            </svg>
            <span class="truncate">${escapeHtml(file.name)}</span>
        </div>
    `).join('');
}

/**
 * 使用推荐示例
 * @param {string} question - 示例问题
 * @param {boolean} requiresAgentic - 是否需要开启 Agentic 模式
 */
function useExample(question, requiresAgentic = false) {
    elements.messageInput.value = question;
    autoResizeTextarea();
    
    // 如果示例需要 Agentic 模式，自动开启
    if (requiresAgentic && elements.useAgentic) {
        elements.useAgentic.checked = true;
        showAgenticWarning(true);
        showToast(UI_TEXTS.agentic.modeEnabled, 'info');
    }
    
    elements.messageInput.focus();
}

/**
 * 显示/隐藏 Agentic 模式警告
 */
function showAgenticWarning(show) {
    const warning = document.getElementById('agentic-warning');
    if (warning) {
        if (show) {
            warning.classList.remove('hidden');
        } else {
            warning.classList.add('hidden');
        }
    }
}

// ============ 事件绑定 ============
function initEventListeners() {
    // 文件上传 - 点击
    elements.dropzone.addEventListener('click', () => {
        elements.fileInput.click();
    });
    
    // 文件上传 - 选择
    elements.fileInput.addEventListener('change', (e) => {
        state.selectedFiles = Array.from(e.target.files);
        updateSelectedFiles();
    });
    
    // 文件上传 - 拖拽
    elements.dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.dropzone.classList.add('dragover');
    });
    
    elements.dropzone.addEventListener('dragleave', () => {
        elements.dropzone.classList.remove('dragover');
    });
    
    elements.dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.dropzone.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files).filter(file => {
            const ext = file.name.split('.').pop().toLowerCase();
            return ['md', 'txt'].includes(ext);
        });
        
        if (files.length === 0) {
            showToast(UI_TEXTS.upload.invalidFormat, 'warning');
            return;
        }
        
        state.selectedFiles = files;
        updateSelectedFiles();
    });
    
    // 上传按钮
    elements.uploadBtn.addEventListener('click', uploadFiles);
    
    // 入库按钮 - 显示确认弹窗
    elements.ingestBtn.addEventListener('click', showReindexConfirm);
    
    // 发送消息
    elements.sendBtn.addEventListener('click', sendMessage);
    
    // 停止生成
    elements.stopBtn.addEventListener('click', stopStreaming);
    
    // 回车发送
    elements.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // 自动调整文本框高度
    elements.messageInput.addEventListener('input', autoResizeTextarea);
    
    // 保存为文档复选框
    elements.saveToFile.addEventListener('change', (e) => {
        elements.fileName.classList.toggle('hidden', !e.target.checked);
    });
    
    // Agentic 模式切换 - 显示风险提示
    if (elements.useAgentic) {
        elements.useAgentic.addEventListener('change', (e) => {
            showAgenticWarning(e.target.checked);
        });
    }
    
    // ESC 关闭预览
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closePreview();
        }
    });
}

// ============ 初始化 ============
async function init() {
    initEventListeners();
    
    // 恢复侧边栏状态
    restoreSidebarState();
    
    // 初始加载
    await Promise.all([checkHealth(), loadFiles()]);
    
    // 定时刷新状态
    setInterval(checkHealth, 30000);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);

// 暴露给 HTML 的函数
window.toggleSources = toggleSources;
window.openPreview = openPreview;
window.closePreview = closePreview;
window.useExample = useExample;
window.showAgenticWarning = showAgenticWarning;
window.closeConfirmModal = closeConfirmModal;
window.confirmReindex = confirmReindex;
// 侧边栏功能
window.toggleSidebar = toggleSidebar;
// 文件删除功能
window.showDeleteConfirm = showDeleteConfirm;
window.closeDeleteModal = closeDeleteModal;
window.confirmDeleteFile = confirmDeleteFile;
