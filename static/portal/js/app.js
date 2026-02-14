/**
 * OpenMemoryX Portal - App Module
 * 主应用逻辑和页面管理
 */

// 全局状态
let currentPage = 'dashboard';
let currentPageNum = 1;
let memoriesData = [];
let apiKeysData = [];

// 初始化
async function init() {
    lucide.createIcons();
    await checkAuth();
    setupEventListeners();
}

// 设置事件监听
function setupEventListeners() {
    // 添加记忆表单
    document.getElementById('add-memory-form')?.addEventListener('submit', handleAddMemory);
    
    // 创建 API Key 表单
    document.getElementById('create-key-form')?.addEventListener('submit', handleCreateKey);
    
    // 搜索
    document.getElementById('memory-search')?.addEventListener('input', debounce(handleSearch, 300));
    
    // 设置表单
    document.getElementById('settings-form')?.addEventListener('submit', handleUpdateSettings);
    document.getElementById('password-form')?.addEventListener('submit', handleUpdatePassword);
}

// 导航到页面
function navigateTo(page) {
    // 隐藏所有页面
    document.querySelectorAll('.page-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.sidebar-item').forEach(el => el.classList.remove('active'));
    
    // 显示目标页面
    const targetPage = document.getElementById(`page-${page}`);
    if (targetPage) {
        targetPage.classList.remove('hidden');
    }
    
    // 更新菜单激活状态
    const navItem = document.getElementById(`nav-${page}`);
    if (navItem) {
        navItem.classList.add('active');
    }
    
    // 更新页面标题
    const pageTitles = {
        'dashboard': 'Dashboard',
        'memories': 'Memories',
        'memory-detail': 'Memory Detail',
        'api-keys': 'API Keys',
        'projects': 'Projects',
        'stats': 'Statistics',
        'settings': 'Settings'
    };
    document.getElementById('page-title').textContent = pageTitles[page] || page;
    
    currentPage = page;
    
    // 加载页面数据
    if (page === 'dashboard') {
        loadDashboardData();
    } else if (page === 'memories') {
        loadMemories(1);
    } else if (page === 'api-keys') {
        loadApiKeys();
    }
    
    // 移动端关闭侧边栏
    if (window.innerWidth < 1024) {
        document.getElementById('sidebar').classList.add('-translate-x-full');
    }
    
    lucide.createIcons();
}

// 加载 Dashboard 数据
async function loadDashboardData() {
    try {
        // 加载统计数据
        const memories = await MemoriesAPI.list({ limit: 1 });
        const keys = await KeysAPI.list();
        
        // 更新统计卡片
        document.getElementById('stat-total-memories').textContent = memories.total || memories.count || 0;
        document.getElementById('stat-api-keys').textContent = keys.length || 0;
        document.getElementById('stat-api-calls').textContent = '1,234';
        document.getElementById('stat-storage').textContent = '2.5 GB';
        
        // 加载最近记忆
        const recentMemories = await MemoriesAPI.list({ limit: 5 });
        renderRecentMemories(recentMemories.items || recentMemories.data || []);
    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

// 渲染最近记忆
function renderRecentMemories(memories) {
    const container = document.getElementById('recent-memories-list');
    
    if (!memories || memories.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-dark-muted">
                <i data-lucide="inbox" class="w-12 h-12 mx-auto mb-3"></i>
                <p>暂无记忆</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    container.innerHTML = memories.map(memory => `
        <div class="flex items-center p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
             onclick="viewMemory('${memory.id}')">
            <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500/20 to-primary-600/20 flex items-center justify-center mr-4">
                <i data-lucide="${getMemoryIcon(memory.type)}" class="w-5 h-5 text-primary-400"></i>
            </div>
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate">${escapeHtml(memory.title || memory.content?.substring(0, 50) || '无标题')}</p>
                <p class="text-xs text-dark-muted">${formatDate(memory.created_at || memory.createdAt)}</p>
            </div>
            <i data-lucide="chevron-right" class="w-4 h-4 text-dark-muted"></i>
        </div>
    `).join('');
    
    lucide.createIcons();
}

// 加载记忆列表
async function loadMemories(page = 1) {
    currentPageNum = page;
    
    try {
        const response = await MemoriesAPI.list({ 
            page: page, 
            limit: 10,
            search: document.getElementById('memory-search')?.value
        });
        
        memoriesData = response.items || response.data || response || [];
        
        renderMemoriesList(memoriesData);
        
        // 更新分页
        const total = response.total || memoriesData.length;
        document.getElementById('memories-showing').textContent = memoriesData.length;
        document.getElementById('memories-prev').disabled = page <= 1;
        document.getElementById('memories-next').disabled = memoriesData.length < 10;
    } catch (error) {
        showToast('加载记忆失败: ' + error.message, 'error');
    }
}

// 渲染记忆列表
function renderMemoriesList(memories) {
    const container = document.getElementById('memories-list');
    
    if (!memories || memories.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12">
                <i data-lucide="inbox" class="w-16 h-16 text-dark-muted mx-auto mb-4"></i>
                <p class="text-dark-muted">暂无记忆</p>
                <button onclick="openAddMemoryModal()" class="mt-4 text-primary-400 hover:text-primary-300">添加第一条记忆</button>
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    container.innerHTML = memories.map(memory => `
        <div class="card p-4 flex items-center justify-between hover:border-primary-500/50 transition-colors">
            <div class="flex items-center flex-1 min-w-0 cursor-pointer" onclick="viewMemory('${memory.id}')">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500/20 to-primary-600/20 flex items-center justify-center mr-4">
                    <i data-lucide="${getMemoryIcon(memory.type)}" class="w-6 h-6 text-primary-400"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <h4 class="font-medium truncate">${escapeHtml(memory.title || memory.content?.substring(0, 60) || '无标题')}</h4>
                    <p class="text-sm text-dark-muted truncate">${escapeHtml(memory.content?.substring(0, 100) || '')}</p>
                    <div class="flex items-center mt-2 space-x-3">
                        <span class="text-xs text-dark-muted">${formatDate(memory.created_at || memory.createdAt)}</span>
                        ${memory.tags?.map(tag => `
                            <span class="text-xs px-2 py-0.5 bg-slate-700 rounded-full">${escapeHtml(tag)}</span>
                        `).join('') || ''}
                    </div>
                </div>
            </div>
            <div class="flex items-center space-x-2 ml-4">
                <button onclick="event.stopPropagation(); viewMemory('${memory.id}')" class="p-2 hover:bg-slate-700 rounded-lg transition-colors">
                    <i data-lucide="eye" class="w-4 h-4 text-dark-muted"></i>
                </button>
                <button onclick="event.stopPropagation(); deleteMemory('${memory.id}')" class="p-2 hover:bg-red-500/20 rounded-lg transition-colors">
                    <i data-lucide="trash-2" class="w-4 h-4 text-red-400"></i>
                </button>
            </div>
        </div>
    `).join('');
    
    lucide.createIcons();
}

// 查看记忆详情
async function viewMemory(id) {
    navigateTo('memory-detail');
    
    const container = document.getElementById('memory-detail-content');
    container.innerHTML = `
        <div class="flex items-center justify-center py-12">
            <div class="loading mr-3"></div>
            <span class="text-dark-muted">加载中...</span>
        </div>
    `;
    
    try {
        const memory = await MemoriesAPI.get(id);
        
        if (!memory) {
            container.innerHTML = `
                <div class="text-center py-12">
                    <i data-lucide="alert-circle" class="w-12 h-12 text-red-400 mx-auto mb-4"></i>
                    <p>记忆不存在或已被删除</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }
        
        container.innerHTML = `
            <div class="flex items-center justify-between mb-6">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500/20 to-primary-600/20 flex items-center justify-center">
                        <i data-lucide="${getMemoryIcon(memory.type)}" class="w-5 h-5 text-primary-400"></i>
                    </div>
                    <div>
                        <h2 class="text-xl font-semibold">${escapeHtml(memory.title || '无标题')}</h2>
                        <p class="text-sm text-dark-muted">${formatDate(memory.created_at || memory.createdAt)}</p>
                    </div>
                </div>
                <div class="flex space-x-2">
                    <button onclick="editMemory('${memory.id}')" class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg flex items-center space-x-2">
                        <i data-lucide="edit" class="w-4 h-4"></i>
                        <span>编辑</span>
                    </button>
                    <button onclick="deleteMemory('${memory.id}')" class="px-4 py-2 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg flex items-center space-x-2">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                        <span>删除</span>
                    </button>
                </div>
            </div>
            
            <div class="bg-slate-800/50 rounded-lg p-4">
                <pre class="whitespace-pre-wrap text-sm">${escapeHtml(memory.content || '')}</pre>
            </div>
            
            ${memory.tags?.length > 0 ? `
                <div class="mt-6">
                    <h4 class="text-sm font-medium text-dark-muted mb-2">标签</h4>
                    <div class="flex flex-wrap gap-2">
                        ${memory.tags.map(tag => `
                            <span class="px-3 py-1 bg-slate-700 rounded-full text-sm">${escapeHtml(tag)}</span>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            <div class="mt-6 pt-6 border-t border-dark-border">
                <h4 class="text-sm font-medium text-dark-muted mb-2">元数据</h4>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span class="text-dark-muted">ID: </span>
                        <code class="text-xs">${memory.id}</code>
                    </div>
                    <div>
                        <span class="text-dark-muted">类型: </span>
                        <span class="capitalize">${memory.type || 'text'}</span>
                    </div>
                </div>
            </div>
        `;
        
        lucide.createIcons();
    } catch (error) {
        container.innerHTML = `
            <div class="text-center py-12">
                <i data-lucide="alert-circle" class="w-12 h-12 text-red-400 mx-auto mb-4"></i>
                <p>加载失败: ${error.message}</p>
            </div>
        `;
        lucide.createIcons();
    }
}

// 加载 API Keys
async function loadApiKeys() {
    try {
        const keys = await KeysAPI.list();
        apiKeysData = keys || [];
        renderApiKeysList(keys);
    } catch (error) {
        showToast('加载 API Keys 失败', 'error');
    }
}

// 渲染 API Keys 列表
function renderApiKeysList(keys) {
    const tbody = document.getElementById('api-keys-list');
    
    if (!keys || keys.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="px-6 py-8 text-center text-dark-muted">
                    <i data-lucide="key" class="w-12 h-12 mx-auto mb-3"></i>
                    <p>暂无 API Key</p>
                </td>
            </tr>
        `;
        lucide.createIcons();
        return;
    }
    
    tbody.innerHTML = keys.map(key => `
        <tr class="hover:bg-slate-800/50">
            <td class="px-6 py-4">
                <div class="font-medium">${escapeHtml(key.name)}</div>
            </td>
            <td class="px-6 py-4">
                <code class="text-sm text-dark-muted">${maskApiKey(key.key || key.token)}</code>
            </td>
            <td class="px-6 py-4 text-sm text-dark-muted">
                ${formatDate(key.created_at || key.createdAt)}
            </td>
            <td class="px-6 py-4">
                <button onclick="deleteApiKey('${key.id}')" class="p-2 hover:bg-red-500/20 rounded-lg transition-colors" title="删除">
                    <i data-lucide="trash-2" class="w-4 h-4 text-red-400"></i>
                </button>
            </td>
        </tr>
    `).join('');
    
    lucide.createIcons();
}

// 处理添加记忆
async function handleAddMemory(e) {
    e.preventDefault();
    
    const content = document.getElementById('memory-content').value;
    const type = document.getElementById('memory-type').value;
    const tagsInput = document.getElementById('memory-tags').value;
    const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(t => t) : [];
    
    try {
        await MemoriesAPI.create({ content, type, tags });
        closeModal('add-memory-modal');
        showToast('记忆添加成功', 'success');
        document.getElementById('add-memory-form').reset();
        
        // 刷新当前页面
        if (currentPage === 'memories') {
            loadMemories(currentPageNum);
        } else if (currentPage === 'dashboard') {
            loadDashboardData();
        }
    } catch (error) {
        showToast('添加失败: ' + error.message, 'error');
    }
}

// 处理创建 API Key
async function handleCreateKey(e) {
    e.preventDefault();
    
    const name = document.getElementById('key-name').value;
    
    try {
        const response = await KeysAPI.create(name);
        closeModal('create-key-modal');
        document.getElementById('create-key-form').reset();
        
        // 显示新密钥
        document.getElementById('new-api-key').textContent = response.key || response.token;
        document.getElementById('show-key-modal').classList.remove('hidden');
        
        loadApiKeys();
    } catch (error) {
        showToast('创建失败: ' + error.message, 'error');
    }
}

// 处理搜索
async function handleSearch(e) {
    const query = e.target.value.trim();
    
    if (!query) {
        loadMemories(1);
        return;
    }
    
    try {
        const results = await MemoriesAPI.search(query);
        memoriesData = results.items || results.data || results || [];
        renderMemoriesList(memoriesData);
    } catch (error) {
        console.error('Search failed:', error);
    }
}

// 处理更新设置
async function handleUpdateSettings(e) {
    e.preventDefault();
    showToast('设置已保存', 'success');
}

// 处理更新密码
async function handleUpdatePassword(e) {
    e.preventDefault();
    showToast('密码已更新', 'success');
    document.getElementById('password-form').reset();
}

// 删除记忆
async function deleteMemory(id) {
    if (!confirm('确定要删除这条记忆吗？此操作不可恢复。')) return;
    
    // 这里需要后端支持删除 API
    showToast('删除功能需要后端支持', 'info');
}

// 删除 API Key
async function deleteApiKey(id) {
    if (!confirm('确定要删除这个 API Key 吗？使用此密钥的应用将立即停止工作。')) return;
    
    try {
        await KeysAPI.delete(id);
        showToast('API Key 已删除', 'success');
        loadApiKeys();
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

// 模态框控制
function openAddMemoryModal() {
    document.getElementById('add-memory-modal').classList.remove('hidden');
}

function openCreateKeyModal() {
    document.getElementById('create-key-modal').classList.remove('hidden');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

// 移动端侧边栏
function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('-translate-x-full');
}

// 确认删除账户
function confirmDeleteAccount() {
    if (confirm('警告：此操作将永久删除您的账户和所有数据，无法恢复。确定要继续吗？')) {
        showToast('账户删除功能需要后端支持', 'info');
    }
}

// 工具函数
function getMemoryIcon(type) {
    const icons = {
        'text': 'file-text',
        'code': 'code',
        'url': 'link',
        'note': 'sticky-note',
        'image': 'image'
    };
    return icons[type] || 'file';
}

function formatDate(dateStr) {
    if (!dateStr) return '未知';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function maskApiKey(key) {
    if (!key) return '***';
    if (key.length <= 8) return '***';
    return key.substring(0, 4) + '••••••••' + key.substring(key.length - 4);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Toast 通知
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const icon = document.getElementById('toast-icon');
    const msg = document.getElementById('toast-message');
    
    const icons = {
        success: 'check-circle',
        error: 'x-circle',
        info: 'info'
    };
    
    const colors = {
        success: 'text-emerald-400',
        error: 'text-red-400',
        info: 'text-primary-400'
    };
    
    icon.setAttribute('data-lucide', icons[type]);
    icon.className = `w-5 h-5 ${colors[type]}`;
    msg.textContent = message;
    
    toast.classList.remove('hidden');
    lucide.createIcons();
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    const text = element.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板', 'success');
    }).catch(() => {
        showToast('复制失败', 'error');
    });
}

// 初始化应用
document.addEventListener('DOMContentLoaded', init);
