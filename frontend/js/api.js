// API基础配置
const API_BASE_URL = 'http://localhost:8000';
const API_ENDPOINTS = {
    POSTS: '/api/posts',
    POST: (id) => `/api/posts/${id}`
};

// 显示/隐藏加载指示器
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// 统一的错误处理
function handleApiError(error) {
    console.error('API Error:', error);
    let message = '网络错误，请稍后重试';

    if (error.response) {
        message = error.response.data?.detail || `服务器错误: ${error.response.status}`;
    } else if (error.request) {
        message = '无法连接到服务器，请检查网络连接';
    }

    alert(message);
    throw error;
}

// 博客API
const BlogAPI = {
    // 获取所有文章
    async getAllPosts() {
        try {
            showLoading();
            const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.POSTS}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            return data;
        } catch (error) {
            handleApiError(error);
        } finally {
            hideLoading();
        }
    },

    // 获取单篇文章
    async getPost(id) {
        try {
            showLoading();
            const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.POST(id)}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            return data;
        } catch (error) {
            handleApiError(error);
        } finally {
            hideLoading();
        }
    },

    // 创建文章
    async createPost(postData) {
        try {
            showLoading();
            const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.POSTS}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(postData)
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            return data;
        } catch (error) {
            handleApiError(error);
        } finally {
            hideLoading();
        }
    },

    // 更新文章
    async updatePost(id, postData) {
        try {
            showLoading();
            const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.POST(id)}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(postData)
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            return data;
        } catch (error) {
            handleApiError(error);
        } finally {
            hideLoading();
        }
    },

    // 删除文章
    async deletePost(id) {
        try {
            showLoading();
            const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.POST(id)}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            return data;
        } catch (error) {
            handleApiError(error);
        } finally {
            hideLoading();
        }
    }
};
