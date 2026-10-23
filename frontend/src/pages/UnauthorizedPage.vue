<template>
  <div class="unauthorized-page" id="unauthorized-page" style="padding: 80px 20px; text-align: center;">
    <div class="empty-frame" style="max-width: 580px; margin: 0 auto; border-color: var(--danger);">
      <div class="empty-icon" style="background: var(--danger-light); color: var(--danger);">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
      </div>
      <h2 class="empty-title" style="color: var(--danger);">访问受限：需要管理者权限</h2>
      <p class="empty-desc">
        只有飞书通讯录中被标记为“管理者”的用户可以访问研发工作台。如果您确需使用该系统，请联系管理员为您开通管理者权限或指派相关角色。
      </p>
      <div style="display: flex; justify-content: center; gap: 14px;">
        <a href="/app" target="_top" class="btn-primary" id="btn-back-desk">返回 Frappe Desk</a>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>
