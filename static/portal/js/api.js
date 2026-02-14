/**
 * OpenMemoryX Portal - API Module
 * 处理所有与后端的 API 通信
 */

const API_BASE_URL = 'http://192.168.31.65:8080/api';

// 存储 token
const TokenStore = {
    get() {
        return localStorage.getItem('omx_token');
    },
    set(token) {
        localStorage.setItem('omx_token', token);
    },
    remove() {
        localStorage.removeItem('omx_token');
    }
};

// 通用请求函数
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const token = TokenStore.get();
    
    const defaultHeaders = {
        'Content-Type': 'application/json',
    };
    
    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers,
        },
    };
    
    // 转换 body 为 JSON
    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }
    
    try {
        const response = await fetch(url, config);
        
        // 处理 401 未授权
        if (response.status === 401) {
            TokenStore.remove();
            showLogin();
            throw new Error('会话已过期，请重新登录');
        }
        
        // 解析响应
        let data;
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            data = await response.text();
        }
        
        if (!response.ok) {
            throw new Error(data.message || data.error || `请求失败: ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// 认证 API
const AuthAPI = {
    async register(username, email, password) {
        return apiRequest('/auth/register', {
            method: 'POST',
            body: { username, email, password },
        });
    },
    
    async login(email, password) {
        return apiRequest('/auth/login', {
            method: 'POST',
            body: { email, password },
        });
    },
    
    async getMe() {
        return apiRequest('/auth/me');
    },
};

// 记忆 API
const MemoriesAPI = {
    async list(params = {}) {
        const queryParams = new URLSearchParams(params).toString();
        const endpoint = queryParams ? `/v1/memories?${queryParams}` : '/v1/memories';
        return apiRequest(endpoint);
    },
    
    async create(data) {
        return apiRequest('/v1/memories', {
            method: 'POST',
            body: data,
        });
    },
    
    async search(query, filters = {}) {
        return apiRequest('/v1/memories/search', {
            method: 'POST',
            body: { query, ...filters },
        });
    },
    
    async get(id) {
        // 如果后端不支持单个获取，从列表中查找
        const list = await this.list({ limit: 1000 });
        return list.items?.find(m => m.id === id);
    },
};

// API Keys API
const KeysAPI = {
    async list() {
        return apiRequest('/keys');
    },
    
    async create(name) {
        return apiRequest('/keys', {
            method: 'POST',
            body: { name },
        });
    },
    
    async delete(id) {
        return apiRequest(`/keys/${id}`, {
            method: 'DELETE',
        });
    },
};

// 任务 API
const TasksAPI = {
    async getStatus(taskId) {
        return apiRequest(`/v1/tasks/${taskId}`);
    },
};
