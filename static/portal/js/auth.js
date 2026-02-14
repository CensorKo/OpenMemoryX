/**
 * OpenMemoryX Portal - Auth Module
 * 处理用户认证和会话管理
 */

let currentUser = null;

// 检查是否已登录
async function checkAuth() {
    const token = TokenStore.get();
    
    if (!token) {
        showAuth();
        return false;
    }
    
    try {
        currentUser = await AuthAPI.getMe();
        updateUserUI();
        showApp();
        return true;
    } catch (error) {
        TokenStore.remove();
        showAuth();
        return false;
    }
}

// 显示认证页面
function showAuth() {
    document.getElementById('auth-container').classList.remove('hidden');
    document.getElementById('app-container').classList.add('hidden');
}

// 显示应用主界面
function showApp() {
    document.getElementById('auth-container').classList.add('hidden');
    document.getElementById('app-container').classList.remove('hidden');
    loadDashboardData();
}

// 切换到注册表单
function showRegister() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-form').classList.remove('hidden');
}

// 切换到登录表单
function showLogin() {
    document.getElementById('register-form').classList.add('hidden');
    document.getElementById('login-form').classList.remove('hidden');
}

// 更新用户界面
function updateUserUI() {
    if (currentUser) {
        document.getElementById('user-name').textContent = currentUser.username || currentUser.name || 'User';
        document.getElementById('user-email').textContent = currentUser.email || '';
        document.getElementById('settings-username').value = currentUser.username || '';
        document.getElementById('settings-email').value = currentUser.email || '';
    }
}

// 登录处理
document.getElementById('login-form-el')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const btn = document.getElementById('login-btn');
    const btnText = document.getElementById('login-btn-text');
    const btnLoader = document.getElementById('login-btn-loader');
    
    // 显示加载状态
    btn.disabled = true;
    btnText.classList.add('hidden');
    btnLoader.classList.remove('hidden');
    
    try {
        const response = await AuthAPI.login(email, password);
        
        if (response.token) {
            TokenStore.set(response.token);
            currentUser = response.user;
            updateUserUI();
            showToast('登录成功', 'success');
            showApp();
        } else {
            throw new Error('登录失败：未收到 token');
        }
    } catch (error) {
        showToast(error.message || '登录失败', 'error');
    } finally {
        btn.disabled = false;
        btnText.classList.remove('hidden');
        btnLoader.classList.add('hidden');
    }
});

// 注册处理
document.getElementById('register-form-el')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const btn = document.getElementById('register-btn');
    const btnText = document.getElementById('register-btn-text');
    const btnLoader = document.getElementById('register-btn-loader');
    
    // 显示加载状态
    btn.disabled = true;
    btnText.classList.add('hidden');
    btnLoader.classList.remove('hidden');
    
    try {
        const response = await AuthAPI.register(username, email, password);
        
        showToast('注册成功，请登录', 'success');
        showLogin();
        document.getElementById('login-email').value = email;
    } catch (error) {
        showToast(error.message || '注册失败', 'error');
    } finally {
        btn.disabled = false;
        btnText.classList.remove('hidden');
        btnLoader.classList.add('hidden');
    }
});

// 退出登录
function logout() {
    if (confirm('确定要退出登录吗？')) {
        TokenStore.remove();
        currentUser = null;
        showAuth();
        showToast('已退出登录', 'info');
    }
}

// 处理 URL hash，自动显示登录/注册
function handleUrlHash() {
    const hash = window.location.hash;
    if (hash === '#login' || hash === '#auth-container') {
        showAuth();
        showLogin();
    } else if (hash === '#register') {
        showAuth();
        showRegister();
    }
}

// 页面加载时检查 hash
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', handleUrlHash);
} else {
    handleUrlHash();
}
