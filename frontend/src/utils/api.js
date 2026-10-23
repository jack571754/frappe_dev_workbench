/**
 * 研发工作台统一 API 通信客户端
 * 遵循 Frappe / Frappe UI 认证与 CSRF 规范：
 * 1. 自动提取并注入 X-Frappe-CSRF-Token 请求头
 * 2. 自动携带 credentials: 'same-origin' 保障 Session Cookie 传输
 * 3. 统一拦截 401/403 异常，友好跳转或提示
 */

export function getCsrfToken() {
  if (typeof window === 'undefined') return ''
  return (
    window.csrf_token ||
    window.boot?.csrf_token ||
    (window.frappe && window.frappe.csrf_token) ||
    getCookie('csrf_token') ||
    ''
  )
}

function getCookie(name) {
  if (typeof document === 'undefined') return ''
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return ''
}

function getErrorMessage(payload, fallback) {
  if (payload?.message) return payload.message

  if (payload?._server_messages) {
    try {
      const messages = JSON.parse(payload._server_messages)
      const lastMessage = JSON.parse(messages.at(-1))
      if (lastMessage?.message) return lastMessage.message
    } catch {
      // Continue with the exception or HTTP status fallback.
    }
  }

  return payload?.exception || fallback
}

export async function request(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {}),
  }

  // 针对非 GET/HEAD 请求注入 Content-Type 与 CSRF Token
  if (method !== 'GET' && method !== 'HEAD') {
    if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }
    const csrf = getCsrfToken()
    if (csrf) {
      headers['X-Frappe-CSRF-Token'] = csrf
    }
  }

  const fetchOptions = {
    credentials: 'same-origin',
    ...options,
    method,
    headers,
  }

  try {
    const res = await fetch(url, fetchOptions)

    // 拦截 401 登录失效
    if (res.status === 401) {
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        const redirectPath = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.href = `/login?redirect-to=${redirectPath}`
      }
    }

    if (!res.ok) {
      let message = `Request failed (${res.status})`
      try {
        const payload = await res.clone().json()
        message = getErrorMessage(payload, message)
      } catch {
        // Keep the HTTP status fallback for non-JSON responses.
      }
      throw new Error(message)
    }

    return res
  } catch (error) {
    console.error(`[API Error] Request failed for ${url}:`, error)
    throw error
  }
}

export const api = {
  get: (url, options = {}) => request(url, { ...options, method: 'GET' }),
  post: (url, body, options = {}) =>
    request(url, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body || {}),
    }),
  put: (url, body, options = {}) =>
    request(url, {
      ...options,
      method: 'PUT',
      body: body instanceof FormData ? body : JSON.stringify(body || {}),
    }),
  delete: (url, options = {}) => request(url, { ...options, method: 'DELETE' }),
}

export default api
