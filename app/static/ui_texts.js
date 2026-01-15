/**
 * 知识库 RAG 助理 - 企业级 UI 文案集中管理
 * 所有用户可见文本统一在此配置
 */

const UI_TEXTS = {
    // ============ 品牌 & 标题 ============
    brand: {
        name: '知识库助手',
        version: 'v2.0',
        tagline: 'AI 知识工作台 · 智能检索',
        subtitle: 'Enterprise Knowledge Assistant',
        // 一句话定位（30秒电梯演讲）
        positioning: '一个基于私有文档的智能问答与分析工作台，支持证据引用与自动再检索。',
        // 能力标签
        capabilities: ['严格模式', '证据可追溯', '多轮检索'],
    },

    // ============ 状态指示器 ============
    status: {
        checking: '检查服务状态...',
        ready: '系统就绪',
        vectorstoreReady: '向量库就绪',
        vectorstoreEmpty: '知识库为空',
        vectorstoreInit: '向量库初始化中',
        langsmithEnabled: 'Tracing 已启用',
        agenticEnabled: '严格模式',
        connectionFailed: '连接失败',
        reconnecting: '重新连接中...',
        offline: '服务离线',
    },

    // ============ 知识库状态 ============
    knowledgeBase: {
        title: '知识库',
        empty: '暂无文档',
        emptyHint: '上传文档以构建知识库',
        fileCount: '{count} 个文档',
        chunkCount: '{count} 个文本块',
        lastUpdated: '最后更新：{time}',
        ingested: '已入库',
        pending: '待入库',
        failed: '入库失败',
        // 空知识库防护
        emptyWarning: '当前知识库为空，无法基于文档回答问题。请先上传并索引文档。',
        emptyCannotChat: '知识库为空',
    },
    
    // ============ 侧边栏 ============
    sidebar: {
        collapse: '收起侧边栏',
        expand: '展开侧边栏',
        collapseTooltip: '收起侧边栏，专注查看回答内容',
        expandTooltip: '展开侧边栏，管理知识库',
    },
    
    // ============ 文件操作 ============
    fileOps: {
        delete: '删除',
        deleteTooltip: '删除此文档',
        // 删除确认弹窗
        deleteConfirmTitle: '确认删除文档？',
        deleteConfirmMessage: '该操作将永久删除文档 "{filename}"，删除后不可恢复。删除完成后需要重新索引以更新知识库。',
        deleteConfirmAction: '确认删除',
        // 删除结果
        deleteSuccess: '文档 {filename} 已删除，请重新索引',
        deleteFailed: '删除失败：{reason}',
    },

    // ============ 文件上传 ============
    upload: {
        title: '添加文档',
        dropHint: '拖拽文件至此或点击选择',
        supportedFormats: '支持 .md、.txt 格式',
        buttonText: '上传并入库',
        uploading: '正在上传...',
        processing: '处理中...',
        success: '已成功添加 {count} 个文档',
        partialSuccess: '部分文件上传成功：{success}/{total}',
        failed: '上传失败：{reason}',
        duplicate: '文件已存在，将更新内容',
        invalidFormat: '不支持的文件格式',
        fileTooLarge: '文件大小超出限制 (最大 10MB)',
        selected: '已选择 {count} 个文件',
    },

    // ============ 入库操作 ============
    ingest: {
        buttonText: '重新索引',
        buttonTooltip: '重新构建整个知识库索引。当文档内容或索引配置发生变化时使用。',
        processing: '正在建立索引...',
        success: '索引完成：{chunks} 个文本块',
        successDetail: '知识库索引已更新（{docCount} 个文档，{chunkCount} 个文本块）',
        noFiles: '无可处理文件',
        failed: '索引失败：{reason}',
        progress: '处理进度：{current}/{total}',
        // 二次确认弹窗
        confirmTitle: '确认重新索引？',
        confirmMessage: '该操作将清空并重新构建当前知识库的向量索引。所有文档将按最新规则重新处理，可能需要一定时间。',
        confirmCancel: '取消',
        confirmAction: '确认重新索引',
        // 索引中状态
        indexingStatus: '正在重新构建知识库索引…',
    },

    // ============ 聊天交互 ============
    chat: {
        inputPlaceholder: '输入您的问题，我将基于知识库为您解答...',
        sendButton: '发送',
        stopButton: '停止',
        generating: '生成回答中...',
        thinking: '正在分析问题...',
        retrieving: '检索相关文档...',
        analyzing: '严格模式分析中...',
        stopped: '已停止生成',
        error: '回答生成失败',
        empty: '请输入问题',
        noKnowledge: '请先上传文档建立知识库',
        shortcuts: {
            send: 'Enter 发送',
            newline: 'Shift + Enter 换行',
        },
    },

    // ============ 回答选项 ============
    options: {
        saveToFile: '保存为文档',
        saveAsDocument: '保存为文档',
        saveFileName: '文件名（可选）',
        agenticMode: '严格模式',
        agenticHint: '当资料不足时会自动补充检索并校验回答，结果更可靠但可能稍慢',
        streamMode: '实时回答',
        streamHint: '回答会实时显示，无需等待完整结果',
    },

    // ============ 置信度 ============
    confidence: {
        high: {
            label: '高可信',
            description: '证据充分，回答可靠',
        },
        medium: {
            label: '中可信',
            description: '证据基本充分，请结合实际判断',
        },
        low: {
            label: '待补充',
            description: '证据不足，建议补充相关文档',
        },
    },

    // ============ 证据不足兜底 ============
    lowConfidence: {
        title: '证据不足提示',
        message: '当前知识库可能缺少相关文档，建议：',
        suggestions: [
            '检查问题是否清晰明确',
            '补充与问题相关的文档',
            '尝试换一种方式提问',
        ],
        disclaimer: '以上回答仅供参考，请以原始资料为准。',
    },

    // ============ 来源/证据面板 ============
    sources: {
        title: '参考来源',
        // 证据感强化文案（企业级专业感）
        disclaimer: '以下内容来自你的知识库，而非模型臆测',
        expandButton: '查看证据 ({count})',
        collapseButton: '收起证据',
        viewOriginal: '查看原文',
        similarity: '相关度',
        noSources: '未找到相关参考',
        chunkId: '片段',
        copySuccess: '来源已复制',
        // 证据数量提示
        evidenceCount: '证据：{count} 条',
    },

    // ============ 文档预览 ============
    preview: {
        title: '文档预览',
        loading: '加载文档内容...',
        failed: '加载失败',
        close: '关闭',
        highlight: '高亮匹配',
    },

    // ============ 空状态 ============
    empty: {
        welcome: {
            title: '欢迎使用知识库助理',
            description: '上传您的文档，我将帮您快速检索和分析信息',
        },
        noDocuments: {
            title: '知识库为空',
            description: '上传文档以开始使用智能问答功能',
            action: '上传文档',
        },
        noConversation: {
            title: '开始新的对话',
            description: '输入问题或选择下方示例开始',
        },
        noResults: {
            title: '未找到相关内容',
            description: '尝试调整问题或补充相关文档',
        },
    },

    // ============ 示例问题（演示级推荐用法） ============
    examples: {
        title: '推荐示例',
        subtitle: '点击快速体验核心能力',
        questions: [
            {
                label: '理解系统',
                text: '请介绍这个系统的主要功能，并说明每个功能的使用场景。',
                highlight: true,
            },
            {
                label: '严谨问答',
                text: '根据知识库内容，总结核心要点，并给出引用来源。',
                highlight: false,
            },
            {
                label: '严格模式',
                text: '如果资料不足，请自动补充检索并给出更严格的回答。',
                highlight: true,
                requiresAgentic: true,
            },
        ],
    },

    // ============ 推理轨迹 ============
    reasoning: {
        title: '推理过程',
        steps: {
            retrieve: '检索文档',
            draft: '生成草稿',
            critique: '证据核查',
            refine: '优化检索',
            finalize: '确认答案',
        },
        loops: '检索轮次：{count}',
    },

    // ============ Toast 通知 ============
    toast: {
        // 成功类
        success: {
            upload: '文档上传成功',
            ingest: '知识库索引完成',
            save: '已保存至 {path}',
            saveDocument: '已保存为文档：{filename}',
            copy: '已复制到剪贴板',
            feedback: '感谢您的反馈',
        },
        // 信息类
        info: {
            processing: '处理中，请稍候',
            stopped: '生成已停止',
            noChanges: '内容无变化，已跳过',
            reconnecting: '正在重新连接...',
        },
        // 警告类
        warning: {
            lowConfidence: '证据不足，请谨慎参考',
            partialResult: '部分内容可能不完整',
            slowResponse: '响应时间较长，请耐心等待',
            tokenLimit: '回答已达长度限制',
        },
        // 错误类
        error: {
            upload: '上传失败：{reason}',
            ingest: '索引失败：{reason}',
            chat: '请求失败：{reason}',
            network: '网络连接异常',
            server: '服务暂时不可用',
            timeout: '请求超时，请重试',
            auth: '身份验证失败',
            params: '参数错误：{detail}',
            unknown: '发生未知错误',
        },
    },

    // ============ 加载提示（轮播） ============
    loading: {
        messages: [
            '正在检索知识库...',
            '分析文档相关性...',
            '组织回答内容...',
            '验证信息准确性...',
            '优化回答表述...',
        ],
        interval: 2000, // 轮播间隔（毫秒）
    },

    // ============ 按钮文案 ============
    buttons: {
        confirm: '确认',
        cancel: '取消',
        close: '关闭',
        retry: '重试',
        refresh: '刷新',
        export: '导出',
        copy: '复制',
        expand: '展开',
        collapse: '收起',
        more: '更多',
        less: '收起',
    },

    // ============ 时间格式 ============
    time: {
        justNow: '刚刚',
        minutesAgo: '{n} 分钟前',
        hoursAgo: '{n} 小时前',
        daysAgo: '{n} 天前',
        today: '今天',
        yesterday: '昨天',
    },

    // ============ 数量格式 ============
    count: {
        items: '{n} 项',
        files: '{n} 个文件',
        chunks: '{n} 个片段',
        characters: '{n} 字符',
    },

    // ============ 严格模式专属 ============
    agentic: {
        badge: '严格',
        analyzing: '深度分析中...',
        reRetrieval: '正在进行补充检索...',
        critique: '正在验证回答准确性...',
        multiLoop: '已进行 {n} 轮检索验证',
        enhanced: '此回答已通过多轮验证',
        // 风险提示（专业感）
        modeWarning: '严格模式将在资料不足时自动补充检索并校验回答，结果更可靠但可能稍慢。',
        modeEnabled: '严格模式已启用',
        // 能力标签
        capabilityLabel: '回答模式：严格',
    },

    // ============ 帮助提示 ============
    help: {
        agenticMode: '严格模式会自动检查回答质量，在证据不足时进行多轮检索',
        confidence: '置信度反映回答与知识库内容的匹配程度',
        sources: '来源展示了回答所依据的原始文档片段',
    },
};

// 文案模板替换函数
function formatText(template, params = {}) {
    if (!template) return '';
    return template.replace(/\{(\w+)\}/g, (match, key) => {
        return params[key] !== undefined ? params[key] : match;
    });
}

// 获取随机加载提示
function getRandomLoadingMessage() {
    const messages = UI_TEXTS.loading.messages;
    return messages[Math.floor(Math.random() * messages.length)];
}

// 获取置信度配置
function getConfidenceConfig(level) {
    return UI_TEXTS.confidence[level] || UI_TEXTS.confidence.medium;
}

// 格式化时间
function formatRelativeTime(date) {
    const now = new Date();
    const diff = now - new Date(date);
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return UI_TEXTS.time.justNow;
    if (minutes < 60) return formatText(UI_TEXTS.time.minutesAgo, { n: minutes });
    if (hours < 24) return formatText(UI_TEXTS.time.hoursAgo, { n: hours });
    return formatText(UI_TEXTS.time.daysAgo, { n: days });
}

// 导出供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { UI_TEXTS, formatText, getRandomLoadingMessage, getConfidenceConfig, formatRelativeTime };
}

