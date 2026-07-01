// UI组件库

// 显示通知
function showNotification(message, type = 'info') {
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };

    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background-color: ${colors[type]};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        z-index: 1002;
        animation: slideIn 0.3s ease-out;
        max-width: 400px;
    `;

    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 
                          type === 'error' ? 'fa-exclamation-circle' : 
                          type === 'warning' ? 'fa-exclamation-triangle' : 
                          'fa-info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    // 自动消失
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out forwards';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// 创建模态框
function createModal(options) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'flex';

    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">${options.title || ''}</h3>
                <button class="modal-close" onclick="this.closest('.modal').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                ${options.body || ''}
            </div>
            ${options.footer ? `
            <div class="modal-footer">
                ${options.footer}
            </div>
            ` : ''}
        </div>
    `;

    document.getElementById('modal-container').appendChild(modal);

    // 点击背景关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });

    return modal;
}

// 确认对话框
function showConfirmDialog(message, onConfirm, onCancel = null) {
    const modal = createModal({
        title: '确认操作',
        body: message,
        footer: `
            <button class="btn btn-secondary" onclick="this.closest('.modal').remove(); ${onCancel ? 'onCancel()' : ''}">
                取消
            </button>
            <button class="btn btn-danger" onclick="this.closest('.modal').remove(); onConfirm()">
                确认
            </button>
        `
    });

    return modal;
}

// 渲染文章卡片
function renderPostCard(post) {
    const contentPreview = post.content.length > 150
        ? post.content.substring(0, 150) + '...'
        : post.content;

    return `
        <div class="post-card">
            <div class="post-title">${post.title}</div>
            <div class="post-meta">
                <span><i class="fas fa-user"></i> ${post.author}</span>
                <span><i class="fas fa-calendar"></i> ${post.created_at}</span>
            </div>
            <div class="post-content-preview">${contentPreview}</div>
            <div class="post-actions">
                <button class="btn btn-primary" onclick="viewPost(${post.id})">
                    <i class="fas fa-eye"></i> 查看
                </button>
                <button class="btn btn-secondary" onclick="editPost(${post.id})">
                    <i class="fas fa-edit"></i> 编辑
                </button>
                <button class="btn btn-danger" onclick="deletePost(${post.id})">
                    <i class="fas fa-trash"></i> 删除
                </button>
            </div>
        </div>
    `;
}

// 渲染文章详情
function renderPostDetail(post) {
    const cleanContent = DOMPurify.sanitize(marked.parse(post.content));

    return `
        <div class="card">
            <div style="margin-bottom: 20px;">
                <button class="btn btn-secondary" onclick="showPage('home')">
                    <i class="fas fa-arrow-left"></i> 返回
                </button>
            </div>
            
            <h1 class="post-title" style="font-size: 2rem; margin-bottom: 20px;">
                ${post.title}
            </h1>
            
            <div class="post-meta" style="margin-bottom: 30px;">
                <span class="badge badge-primary">
                    <i class="fas fa-user"></i> ${post.author}
                </span>
                <span><i class="fas fa-calendar"></i> 创建: ${post.created_at}</span>
                ${post.updated_at !== post.created_at ? 
                    `<span><i class="fas fa-history"></i> 更新: ${post.updated_at}</span>` : ''}
            </div>
            
            <div class="post-content" style="font-size: 1.1rem; line-height: 1.8;">
                ${cleanContent}
            </div>
            
            <div class="post-actions" style="margin-top: 30px;">
                <button class="btn btn-secondary" onclick="editPost(${post.id})">
                    <i class="fas fa-edit"></i> 编辑文章
                </button>
                <button class="btn btn-danger" onclick="deletePost(${post.id})">
                    <i class="fas fa-trash"></i> 删除文章
                </button>
            </div>
        </div>
    `;
}

// 渲染文章表单
function renderPostForm(post = null) {
    const isEdit = !!post;

    return `
        <div class="card">
            <div style="margin-bottom: 20px;">
                <button class="btn btn-secondary" onclick="showPage('${isEdit ? `view/${post.id}` : 'home'}')">
                    <i class="fas fa-arrow-left"></i> 返回
                </button>
            </div>
            
            <h2 style="margin-bottom: 30px; color: var(--text-color);">
                ${isEdit ? '编辑文章' : '写新文章'}
            </h2>
            
            <form id="postForm" onsubmit="handleSubmitPost(event, ${isEdit ? post.id : 'null'})">
                <div class="form-group">
                    <label class="form-label">标题</label>
                    <input type="text" class="form-control" id="postTitle" 
                           value="${post ? post.title : ''}" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">作者</label>
                    <input type="text" class="form-control" id="postAuthor" 
                           value="${post ? post.author : '管理员'}" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">内容</label>
                    <textarea class="form-control" id="postContent" 
                              rows="10" required>${post ? post.content : ''}</textarea>
                </div>
                
                <div style="display: flex; gap: 10px; margin-top: 30px;">
                    <button type="button" class="btn btn-secondary" 
                            onclick="showPage('${isEdit ? `view/${post.id}` : 'home'}')">
                        取消
                    </button>
                    <button type="submit" class="btn btn-success">
                        <i class="fas fa-paper-plane"></i> 
                        ${isEdit ? '更新文章' : '发布文章'}
                    </button>
                </div>
            </form>
        </div>
    `;
}

// 渲染文章管理表格
function renderPostTable(posts) {
    if (posts.length === 0) {
        return `
            <div class="card" style="text-align: center; padding: 40px;">
                <i class="fas fa-inbox" style="font-size: 3rem; color: var(--secondary-color); margin-bottom: 20px;"></i>
                <h3 style="color: var(--text-color); margin-bottom: 10px;">暂无文章</h3>
                <p style="color: var(--secondary-color);">点击"写文章"按钮开始创作</p>
            </div>
        `;
    }

    const rows = posts.map(post => `
        <tr>
            <td>${post.id}</td>
            <td>${post.title}</td>
            <td>${post.author}</td>
            <td>${post.created_at}</td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="viewPost(${post.id})">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-secondary btn-sm" onclick="editPost(${post.id})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-danger btn-sm" onclick="deletePost(${post.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');

    return `
        <div class="card">
            <h2 style="margin-bottom: 20px; color: var(--text-color);">文章管理</h2>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: var(--light-color);">
                            <th style="padding: 12px; text-align: left;">ID</th>
                            <th style="padding: 12px; text-align: left;">标题</th>
                            <th style="padding: 12px; text-align: left;">作者</th>
                            <th style="padding: 12px; text-align: left;">创建时间</th>
                            <th style="padding: 12px; text-align: left;">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}
