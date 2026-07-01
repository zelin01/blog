// 应用主逻辑
let currentPage = 'home';

// 初始化应用
async function initApp() {
    // 设置主题
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // 加载首页
    await showPage('home');
}

// 切换主题
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // 更新按钮图标
    const themeButton = document.querySelector('.btn-toggle-theme i');
    themeButton.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

// 显示页面
async function showPage(page) {
    currentPage = page;
    const mainContent = document.getElementById('main-content');

    try {
        if (page === 'home') {
            await loadHomePage();
        } else if (page === 'manage') {
            await loadManagePage();
        } else if (page === 'create') {
            loadCreatePage();
        } else if (page.startsWith('view/')) {
            const postId = parseInt(page.split('/')[1]);
            await loadPostPage(postId);
        } else if (page.startsWith('edit/')) {
            const postId = parseInt(page.split('/')[1]);
            await loadEditPage(postId);
        }
    } catch (error) {
        console.error('Error loading page:', error);
        mainContent.innerHTML = `
            <div class="card" style="text-align: center; padding: 40px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: var(--danger-color); margin-bottom: 20px;"></i>
                <h3 style="color: var(--text-color); margin-bottom: 10px;">加载失败</h3>
                <p style="color: var(--secondary-color);">${error.message}</p>
                <button class="btn btn-primary" onclick="showPage('home')" style="margin-top: 20px;">
                    返回首页
                </button>
            </div>
        `;
    }
}

// 加载首页
async function loadHomePage() {
    const mainContent = document.getElementById('main-content');

    mainContent.innerHTML = `
        <div style="margin-bottom: 30px;">
            <h1 style="color: var(--text-color); margin-bottom: 10px;">📚 最新文章</h1>
            <p style="color: var(--secondary-color);">欢迎阅读我们的博客文章</p>
        </div>
        <div id="posts-container" style="min-height: 200px;">
            <div style="text-align: center; padding: 40px;">
                <div class="spinner" style="margin: 0 auto;"></div>
                <p style="margin-top: 20px; color: var(--secondary-color);">加载中...</p>
            </div>
        </div>
    `;

    try {
        const posts = await BlogAPI.getAllPosts();

        if (posts.length === 0) {
            document.getElementById('posts-container').innerHTML = `
                <div class="card" style="text-align: center; padding: 40px;">
                    <i class="fas fa-feather-alt" style="font-size: 3rem; color: var(--secondary-color); margin-bottom: 20px;"></i>
                    <h3 style="color: var(--text-color); margin-bottom: 10px;">暂无文章</h3>
                    <p style="color: var(--secondary-color); margin-bottom: 20px;">点击"写文章"按钮开始创作</p>
                    <button class="btn btn-success" onclick="showPage('create')">
                        <i class="fas fa-plus"></i> 写文章
                    </button>
                </div>
            `;
        } else {
            const postsHTML = posts
                .slice() // 创建副本避免修改原数组
                .reverse() // 最新的在前
                .map(post => renderPostCard(post))
                .join('');

            document.getElementById('posts-container').innerHTML = `
                <div class="post-list">
                    ${postsHTML}
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('posts-container').innerHTML = `
            <div class="card" style="text-align: center; padding: 40px; color: var(--danger-color);">
                <i class="fas fa-exclamation-circle" style="font-size: 3rem; margin-bottom: 20px;"></i>
                <p>加载文章失败，请刷新页面重试</p>
            </div>
        `;
    }
}

// 加载文章详情页
async function loadPostPage(postId) {
    const mainContent = document.getElementById('main-content');

    mainContent.innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <div class="spinner" style="margin: 0 auto;"></div>
            <p style="margin-top: 20px; color: var(--secondary-color);">加载中...</p>
        </div>
    `;

    try {
        const post = await BlogAPI.getPost(postId);
        mainContent.innerHTML = renderPostDetail(post);
    } catch (error) {
        mainContent.innerHTML = `
            <div class="card" style="text-align: center; padding: 40px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: var(--danger-color); margin-bottom: 20px;"></i>
                <h3 style="color: var(--text-color); margin-bottom: 10px;">文章不存在</h3>
                <p style="color: var(--secondary-color);">该文章可能已被删除</p>
                <button class="btn btn-primary" onclick="showPage('home')" style="margin-top: 20px;">
                    返回首页
                </button>
            </div>
        `;
    }
}

// 加载创建文章页
function loadCreatePage() {
    const mainContent = document.getElementById('main-content');
    mainContent.innerHTML = renderPostForm();
}

// 加载编辑文章页
async function loadEditPage(postId) {
    const mainContent = document.getElementById('main-content');

    mainContent.innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <div class="spinner" style="margin: 0 auto;"></div>
            <p style="margin-top: 20px; color: var(--secondary-color);">加载中...</p>
        </div>
    `;

    try {
        const post = await BlogAPI.getPost(postId);
        mainContent.innerHTML = renderPostForm(post);
    } catch (error) {
        mainContent.innerHTML = `
            <div class="card" style="text-align: center; padding: 40px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: var(--danger-color); margin-bottom: 20px;"></i>
                <h3 style="color: var(--text-color); margin-bottom: 10px;">文章不存在</h3>
                <p style="color: var(--secondary-color);">无法编辑不存在的文章</p>
                <button class="btn btn-primary" onclick="showPage('home')" style="margin-top: 20px;">
                    返回首页
                </button>
            </div>
        `;
    }
}

// 加载管理页面
async function loadManagePage() {
    const mainContent = document.getElementById('main-content');

    mainContent.innerHTML = `
        <div style="margin-bottom: 30px;">
            <h1 style="color: var(--text-color); margin-bottom: 10px;">📋 文章管理</h1>
            <p style="color: var(--secondary-color);">管理所有博客文章</p>
        </div>
        <div id="manage-container" style="min-height: 200px;">
            <div style="text-align: center; padding: 40px;">
                <div class="spinner" style="margin: 0 auto;"></div>
                <p style="margin-top: 20px; color: var(--secondary-color);">加载中...</p>
            </div>
        </div>
    `;

    try {
        const posts = await BlogAPI.getAllPosts();
        document.getElementById('manage-container').innerHTML = renderPostTable(posts);
    } catch (error) {
        document.getElementById('manage-container').innerHTML = `
            <div class="card" style="text-align: center; padding: 40px; color: var(--danger-color);">
                <i class="fas fa-exclamation-circle" style="font-size: 3rem; margin-bottom: 20px;"></i>
                <p>加载失败，请刷新页面重试</p>
            </div>
        `;
    }
}

// 查看文章
function viewPost(postId) {
    showPage(`view/${postId}`);
}

// 编辑文章
function editPost(postId) {
    showPage(`edit/${postId}`);
}

// 删除文章
async function deletePost(postId) {
    showConfirmDialog(
        '确定要删除这篇文章吗？删除后无法恢复。',
        async () => {
            try {
                await BlogAPI.deletePost(postId);
                showNotification('文章删除成功', 'success');

                // 根据当前页面刷新内容
                if (currentPage === 'manage') {
                    await loadManagePage();
                } else if (currentPage === 'home') {
                    await loadHomePage();
                } else {
                    showPage('home');
                }
            } catch (error) {
                showNotification('删除失败: ' + error.message, 'error');
            }
        }
    );
}

// 处理文章提交
async function handleSubmitPost(event, postId = null) {
    event.preventDefault();

    const title = document.getElementById('postTitle').value.trim();
    const author = document.getElementById('postAuthor').value.trim();
    const content = document.getElementById('postContent').value.trim();

    if (!title || !author || !content) {
        showNotification('请填写所有必填字段', 'warning');
        return;
    }

    const postData = {
        title,
        author,
        content
    };

    try {
        if (postId) {
            // 更新文章
            await BlogAPI.updatePost(postId, postData);
            showNotification('文章更新成功', 'success');
            showPage(`view/${postId}`);
        } else {
            // 创建新文章
            const newPost = await BlogAPI.createPost(postData);
            showNotification('文章发布成功', 'success');
            showPage(`view/${newPost.id}`);
        }
    } catch (error) {
        showNotification('操作失败: ' + error.message, 'error');
    }
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .btn-sm {
        padding: 4px 8px;
        font-size: 0.8rem;
    }
`;
document.head.appendChild(style);
