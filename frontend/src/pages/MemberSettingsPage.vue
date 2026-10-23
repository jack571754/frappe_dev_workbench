<template>
  <div class="member-settings-page" id="member-settings-page">
    <!-- Page Header -->
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
      <div>
        <h2 style="font-size: 1.4rem; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 10px;">
          <span>成员与 Git 身份管理</span>
          <span style="font-size: 0.78rem; font-weight: 600; padding: 2px 10px; border-radius: 9999px; background: #e0e7ff; color: #4338ca;">
            搜索精准录入模式
          </span>
        </h2>
        <p style="font-size: 0.88rem; color: var(--text-secondary); margin-top: 4px;">
          维护团队研发成员，通过精准搜索快速添加；为每位成员绑定多个 Git 身份（邮箱/用户名），并将未匹配提交进行认领归属
        </p>
      </div>

      <div style="display: flex; gap: 10px; align-items: center;">
        <button
          id="btn-open-search-member-modal"
          type="button"
          class="btn-primary"
          style="display: flex; align-items: center; gap: 6px; padding: 8px 16px; font-weight: 600;"
          @click="openSearchAddModal"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            <line x1="11" y1="8" x2="11" y2="14"></line>
            <line x1="8" y1="11" x2="14" y2="11"></line>
          </svg>
          <span>🔍 搜索并添加成员</span>
        </button>

        <a href="/app/project-member" target="_blank" class="btn-secondary" style="display: flex; align-items: center; gap: 6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
          <span>在 Desk 中编辑</span>
        </a>
      </div>
    </div>

    <!-- Unclaimed Identities Alert Banner with Search-based Claiming -->
    <div
      v-if="unclaimedIdentities.length > 0"
      id="unclaimed-identities-banner"
      style="background: #fffbeb; border: 1px solid #fde68a; border-radius: var(--radius-md); padding: 16px 20px; margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px;"
    >
      <div style="display: flex; align-items: center; gap: 14px;">
        <div style="width: 40px; height: 40px; background: #fef3c7; color: #d97706; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        </div>
        <div>
          <div style="font-weight: 700; color: #92400e; font-size: 0.96rem;">
            发现 {{ unclaimedIdentities.length }} 个待认领 Git 身份
          </div>
          <div style="font-size: 0.85rem; color: #b45309; margin-top: 2px;">
            这些 Git 邮箱在 Codeup 提交过代码但尚未归属。现已支持搜索候选成员与智能匹配，快速一键归属。
          </div>
        </div>
      </div>
      <button
        id="btn-open-claim-modal"
        type="button"
        class="btn-primary"
        style="background: #d97706; padding: 7px 18px;"
        @click="openClaimModal"
      >
        立即搜索匹配认领
      </button>
    </div>

    <!-- Members Grid / Table Card -->
    <div style="background: #fff; border-radius: var(--radius-lg); border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm); overflow: hidden;">
      <div style="padding: 18px 24px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <h3 style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary);">
            成员列表 ({{ members.length }} 人)
          </h3>
          <span style="font-size: 0.78rem; color: var(--text-muted); background: #f1f5f9; padding: 2px 8px; border-radius: 12px;">
            启用: {{ activeMembersCount }} 人
          </span>
        </div>

        <div style="display: flex; align-items: center; gap: 10px;">
          <input
            id="input-filter-member-list"
            type="text"
            v-model="searchQuery"
            placeholder="搜索姓名、邮箱、部门或 Git 标识..."
            class="form-input-sm"
            style="min-width: 260px;"
          />
          <button
            type="button"
            class="btn-secondary"
            style="padding: 6px 12px; font-size: 0.82rem;"
            @click="fetchMembers"
            title="刷新成员列表"
          >
            🔄 刷新
          </button>
        </div>
      </div>

      <div v-if="filteredMembers.length === 0" style="padding: 48px; text-align: center; color: var(--text-muted);">
        <p style="font-size: 0.95rem; margin-bottom: 12px;">暂无符合条件的成员记录</p>
        <button type="button" class="btn-primary" style="font-size: 0.84rem; padding: 6px 16px;" @click="openSearchAddModal">
          🔍 立即搜索并添加成员
        </button>
      </div>

      <div v-else style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.875rem;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); font-size: 0.82rem; text-transform: uppercase;">
              <th style="padding: 12px 24px;">成员姓名</th>
              <th style="padding: 12px 16px;">所属部门</th>
              <th style="padding: 12px 16px;">飞书关联</th>
              <th style="padding: 12px 16px;">邮箱 / 手机</th>
              <th style="padding: 12px 16px;">身份角色</th>
              <th style="padding: 12px 16px;">关联 Git 身份</th>
              <th style="padding: 12px 24px; text-align: right;">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="m in filteredMembers"
              :key="m.name"
              style="border-bottom: 1px solid #f1f5f9; transition: background 0.15s;"
              :style="{ opacity: m.is_active ? 1 : 0.45 }"
              onmouseover="this.style.background='#f8fafc'"
              onmouseout="this.style.background='#ffffff'"
            >
              <td style="padding: 14px 24px; font-weight: 600; color: var(--text-primary);">
                <div style="display: flex; align-items: center; gap: 10px;">
                  <div class="avatar-circle" style="width: 30px; height: 30px; font-size: 0.82rem;">
                    {{ (m.member_name || 'U').slice(0, 1).toUpperCase() }}
                  </div>
                  <div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                      <span>{{ m.member_name }}</span>
                      <span v-if="!m.is_active" style="font-size: 0.7rem; padding: 1px 6px; border-radius: 4px; background: #fee2e2; color: #dc2626;">已停用</span>
                    </div>
                    <div style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">
                      {{ m.name }}
                    </div>
                  </div>
                </div>
              </td>
              <td style="padding: 14px 16px; color: var(--text-secondary);">
                <span>{{ m.department || '-' }}</span>
              </td>
              <td style="padding: 14px 16px; color: var(--text-secondary);">
                <span v-if="m.open_id || m.user_id" style="font-size: 0.75rem; font-family: var(--font-mono); background: #f0fdf4; color: #166534; padding: 2px 7px; border-radius: 4px; border: 1px solid #bbf7d0;">
                  已绑定
                </span>
                <span v-else style="color: var(--text-muted); font-size: 0.8rem;">未关联</span>
              </td>
              <td style="padding: 14px 16px; color: var(--text-secondary);">
                <div style="font-weight: 500;">{{ m.email || '-' }}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">{{ m.mobile || '' }}</div>
              </td>
              <td style="padding: 14px 16px;">
                <span
                  v-if="m.is_manager"
                  style="background: #eef2ff; color: #4f46e5; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 600;"
                >
                  管理者
                </span>
                <span
                  v-else
                  style="background: #f1f5f9; color: #64748b; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem;"
                >
                  普通成员
                </span>
              </td>
              <td style="padding: 14px 16px;">
                <div v-if="m.git_identities && m.git_identities.length" style="display: flex; flex-wrap: wrap; gap: 4px; max-width: 260px;">
                  <span
                    v-for="id in m.git_identities"
                    :key="id.identity"
                    style="background: #ecfdf5; color: #047857; font-size: 0.72rem; padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); border: 1px solid #a7f3d0;"
                  >
                    {{ id.identity }}
                  </span>
                </div>
                <span v-else style="color: var(--text-muted); font-size: 0.8rem;">未关联</span>
              </td>
              <td style="padding: 14px 24px; text-align: right;">
                <div style="display: flex; align-items: center; justify-content: flex-end; gap: 6px;">
                  <button
                    type="button"
                    class="btn-secondary"
                    style="padding: 4px 8px; font-size: 0.78rem;"
                    @click="openAddGitModal(m)"
                    title="为该成员绑定新的 Git 身份"
                  >
                    + Git 身份
                  </button>
                  <button
                    v-if="m.is_active"
                    type="button"
                    class="btn-secondary"
                    style="padding: 4px 8px; font-size: 0.78rem; color: #b91c1c;"
                    @click="removeMember(m)"
                    title="停用并移出团队，避免干扰统计"
                  >
                    移除
                  </button>
                  <a :href="`/app/project-member/${m.name}`" target="_blank" class="btn-secondary" style="padding: 4px 8px; font-size: 0.78rem;">
                    Desk
                  </a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Search & Add Member Modal Dialog -->
    <div
      v-if="showSearchModal"
      class="modal-backdrop"
      style="position: fixed; inset: 0; background: rgba(15, 23, 42, 0.55); backdrop-filter: blur(3px); display: flex; align-items: center; justify-content: center; z-index: 10000;"
      @click.self="showSearchModal = false"
    >
      <div
        class="modal-card"
        style="background: #ffffff; border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); width: 92%; max-width: 680px; max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; animation: modalIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);"
      >
        <!-- Modal Header -->
        <div style="padding: 18px 24px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h3 style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
              <span>🔍 搜索并添加团队成员</span>
            </h3>
            <p style="font-size: 0.82rem; color: var(--text-muted); margin-top: 2px;">
              按需搜索飞书/系统用户进行定向添加，杜绝全企业无关人员混入
            </p>
          </div>
          <button type="button" class="btn-secondary" style="padding: 4px 10px; font-size: 0.82rem;" @click="showSearchModal = false">
            ✕
          </button>
        </div>

        <!-- Mode Tabs -->
        <div style="padding: 10px 24px; background: #f8fafc; border-bottom: 1px solid var(--border-subtle); display: flex; gap: 8px;">
          <button
            type="button"
            :class="['mode-tab', addMemberMode === 'search' ? 'active' : '']"
            @click="addMemberMode = 'search'"
          >
            精准搜索添加
          </button>
          <button
            type="button"
            :class="['mode-tab', addMemberMode === 'manual' ? 'active' : '']"
            @click="addMemberMode = 'manual'"
          >
            手动精准录入
          </button>
          <button
            type="button"
            :class="['mode-tab', addMemberMode === 'batch' ? 'active' : '']"
            @click="addMemberMode = 'batch'"
          >
            名单批量导入
          </button>
        </div>

        <!-- Tab 1: Search & Add -->
        <div v-if="addMemberMode === 'search'" style="padding: 20px 24px; overflow-y: auto; flex: 1;">
          <div style="display: flex; gap: 10px; margin-bottom: 18px;">
            <input
              id="input-candidate-search"
              type="text"
              v-model="candidateSearchKey"
              placeholder="输入姓名、企业邮箱或手机号搜索..."
              class="form-input-sm"
              style="flex: 1; padding: 9px 14px; font-size: 0.9rem;"
              @keyup.enter="handleSearchCandidates"
            />
            <button
              type="button"
              class="btn-primary"
              :disabled="loadingCandidates"
              style="padding: 9px 20px;"
              @click="handleSearchCandidates"
            >
              {{ loadingCandidates ? '正在搜索...' : '搜索' }}
            </button>
          </div>

          <div v-if="candidatesList.length === 0" style="padding: 40px; text-align: center; color: var(--text-muted); background: #f8fafc; border-radius: 8px;">
            <div v-if="loadingCandidates">🔍 正在检索飞书及系统人员...</div>
            <div v-else-if="searchedOnce">未检索到匹配的人员，您可以切换至【手动精准录入】直接添加</div>
            <div v-else>请输入成员姓名、邮箱或手机号开始搜索</div>
          </div>

          <div v-else style="display: flex; flex-direction: column; gap: 10px;">
            <div
              v-for="c in candidatesList"
              :key="c.email"
              style="border: 1px solid var(--border-subtle); border-radius: 8px; padding: 14px 16px; background: #fff; display: flex; align-items: center; justify-content: space-between; gap: 12px;"
            >
              <div style="display: flex; align-items: center; gap: 12px;">
                <div class="avatar-circle" style="width: 36px; height: 36px; font-weight: 700;">
                  {{ (c.member_name || 'U').slice(0, 1).toUpperCase() }}
                </div>
                <div>
                  <div style="font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                    <span>{{ c.member_name }}</span>
                    <span v-if="c.source === 'feishu'" style="font-size: 0.72rem; padding: 1px 6px; border-radius: 4px; background: #e0f2fe; color: #0369a1;">飞书已认证</span>
                    <span v-if="c.is_existing" style="font-size: 0.72rem; padding: 1px 6px; border-radius: 4px; background: #f1f5f9; color: #64748b;">已在团队</span>
                  </div>
                  <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px;">
                    <span>{{ c.email }}</span>
                    <span v-if="c.mobile" style="margin-left: 10px;">{{ c.mobile }}</span>
                  </div>
                </div>
              </div>

              <div>
                <button
                  v-if="!c.is_existing"
                  type="button"
                  class="btn-primary"
                  style="padding: 6px 14px; font-size: 0.82rem;"
                  @click="addCandidateToTeam(c)"
                >
                  + 加入团队
                </button>
                <span v-else style="font-size: 0.8rem; color: #059669; font-weight: 600;">✓ 已是成员</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab 2: Manual Add -->
        <div v-else-if="addMemberMode === 'manual'" style="padding: 20px 24px; overflow-y: auto; flex: 1;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
            <div>
              <label style="display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px;">成员姓名 *</label>
              <input type="text" v-model="manualForm.name" placeholder="例如：张伟" class="form-input-sm" style="width: 100%;" />
            </div>
            <div>
              <label style="display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px;">电子邮箱 *</label>
              <input type="email" v-model="manualForm.email" placeholder="zhangwei@company.com" class="form-input-sm" style="width: 100%;" />
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
            <div>
              <label style="display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px;">手机号 (选填)</label>
              <input type="text" v-model="manualForm.mobile" placeholder="13800000000" class="form-input-sm" style="width: 100%;" />
            </div>
            <div>
              <label style="display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px;">所属部门 (选填)</label>
              <input type="text" v-model="manualForm.department" placeholder="研发部 / 前端组" class="form-input-sm" style="width: 100%;" />
            </div>
          </div>

          <div style="margin-bottom: 16px;">
            <label style="display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px;">初始 Git 身份标识 (选填)</label>
            <input type="text" v-model="manualForm.gitIdentity" placeholder="例如其 Codeup 提交使用的 Git 邮箱或用户名" class="form-input-sm" style="width: 100%;" />
            <span style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; display: block;">录入后将自动完成该 Git 身份绑定与提交回溯归属</span>
          </div>

          <div style="margin-bottom: 24px;">
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 0.88rem; font-weight: 600;">
              <input type="checkbox" v-model="manualForm.isManager" />
              <span>设为研发工作台管理者 (可查看全部成员日报与配置)</span>
            </label>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button type="button" class="btn-secondary" @click="showSearchModal = false">取消</button>
            <button
              type="button"
              class="btn-primary"
              :disabled="!manualForm.name || !manualForm.email"
              @click="submitManualAdd"
            >
              确认添加新成员
            </button>
          </div>
        </div>

        <!-- Tab 3: Batch Add -->
        <div v-else-if="addMemberMode === 'batch'" style="padding: 20px 24px; overflow-y: auto; flex: 1;">
          <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 10px;">
            每行输入一条成员记录，支持以下格式（自动识别）：<br>
            • <code>姓名 邮箱</code> (例如: <code>李强 liqiang@company.com</code>)<br>
            • 直接填写邮箱 (例如: <code>liqiang@company.com</code>)
          </p>
          <textarea
            v-model="batchRawText"
            rows="7"
            class="form-input-sm"
            style="width: 100%; font-family: var(--font-mono); font-size: 0.85rem; padding: 12px; margin-bottom: 16px;"
            placeholder="李强 liqiang@company.com&#10;王芳 wangfang@company.com"
          ></textarea>

          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button type="button" class="btn-secondary" @click="showSearchModal = false">取消</button>
            <button
              type="button"
              class="btn-primary"
              :disabled="!batchRawText.trim()"
              @click="submitBatchAdd"
            >
              批量导入这批成员
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Search-based Claim Git Identity Modal -->
    <div
      v-if="showClaimModal"
      class="modal-backdrop"
      style="position: fixed; inset: 0; background: rgba(15, 23, 42, 0.55); backdrop-filter: blur(3px); display: flex; align-items: center; justify-content: center; z-index: 10000;"
      @click.self="showClaimModal = false"
    >
      <div
        class="modal-card"
        style="background: #fff; width: 92%; max-width: 650px; border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-lg);"
      >
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
          <div>
            <h3 style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary);">
              🎯 待认领 Git 身份归属 (搜索匹配模式)
            </h3>
            <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">
              选择待认领 Git 邮箱，在团队成员中快速搜索并归属，支持智能前缀推荐
            </p>
          </div>
          <button type="button" class="btn-secondary" style="padding: 4px 10px; font-size: 0.82rem;" @click="showClaimModal = false">
            ✕
          </button>
        </div>

        <!-- 1. Select Unclaimed Identity -->
        <div style="margin-bottom: 18px;">
          <label style="display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px;">1. 选择待认领 Git 身份 ({{ unclaimedIdentities.length }} 个)</label>
          <select
            v-model="claimForm.identityName"
            class="form-input-sm"
            style="width: 100%; padding: 8px 12px; font-size: 0.9rem;"
            @change="autoSuggestMemberForClaim"
          >
            <option v-for="item in unclaimedIdentities" :key="item.name" :value="item.name">
              {{ item.identity }} ({{ item.identity_type }})
            </option>
          </select>
        </div>

        <!-- Smart Match Recommendation Banner -->
        <div
          v-if="smartRecommendedMember"
          style="background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 6px; padding: 10px 14px; margin-bottom: 18px; display: flex; align-items: center; justify-content: space-between;"
        >
          <div style="font-size: 0.84rem; color: #065f46;">
            💡 <strong>智能推荐匹配：</strong>
            {{ smartRecommendedMember.member_name }} ({{ smartRecommendedMember.email }})
          </div>
          <button
            type="button"
            class="btn-primary"
            style="padding: 4px 10px; font-size: 0.78rem; background: #059669;"
            @click="claimForm.memberId = smartRecommendedMember.name"
          >
            一键选定
          </button>
        </div>

        <!-- 2. Search & Select Member -->
        <div style="margin-bottom: 24px;">
          <label style="display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 6px;">2. 搜索并选定归属成员</label>
          <input
            type="text"
            v-model="claimMemberFilter"
            placeholder="输入姓名或邮箱快速搜索过滤成员..."
            class="form-input-sm"
            style="width: 100%; margin-bottom: 8px;"
          />
          <div style="max-height: 180px; overflow-y: auto; border: 1px solid var(--border-medium); border-radius: 6px; padding: 6px;">
            <div
              v-for="m in filteredClaimMembers"
              :key="m.name"
              style="padding: 8px 12px; border-radius: 4px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; transition: background 0.15s;"
              :style="{ background: claimForm.memberId === m.name ? '#eef2ff' : 'transparent' }"
              @click="claimForm.memberId = m.name"
            >
              <div style="display: flex; align-items: center; gap: 8px;">
                <input type="radio" :value="m.name" v-model="claimForm.memberId" />
                <span style="font-weight: 600;">{{ m.member_name }}</span>
                <span style="font-size: 0.78rem; color: var(--text-muted);">{{ m.email || m.name }}</span>
              </div>
              <span v-if="claimForm.memberId === m.name" style="font-size: 0.75rem; color: #4338ca; font-weight: 700;">✓ 已选中</span>
            </div>
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button type="button" class="btn-secondary" @click="showClaimModal = false">取消</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="!claimForm.identityName || !claimForm.memberId"
            @click="submitClaim"
          >
            确认认领归属
          </button>
        </div>
      </div>
    </div>

    <!-- Quick Add Git Identity to Member Modal -->
    <div
      v-if="quickAddGitTargetMember"
      class="modal-backdrop"
      style="position: fixed; inset: 0; background: rgba(15, 23, 42, 0.55); backdrop-filter: blur(3px); display: flex; align-items: center; justify-content: center; z-index: 10000;"
      @click.self="quickAddGitTargetMember = null"
    >
      <div class="modal-card" style="background: #fff; width: 440px; border-radius: var(--radius-lg); padding: 24px; box-shadow: var(--shadow-lg);">
        <h3 style="font-size: 1.1rem; font-weight: 700; margin-bottom: 6px;">
          为 {{ quickAddGitTargetMember.member_name }} 绑定 Git 身份
        </h3>
        <p style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 16px;">
          输入该成员在 Codeup 提交中使用的 Git 邮箱或用户名
        </p>

        <div style="margin-bottom: 20px;">
          <input
            type="text"
            v-model="newGitIdentityInput"
            placeholder="例如: developer@git.company.com"
            class="form-input-sm"
            style="width: 100%; font-family: var(--font-mono); font-size: 0.88rem;"
            @keyup.enter="submitAddGitIdentity"
          />
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 10px;">
          <button type="button" class="btn-secondary" @click="quickAddGitTargetMember = null">取消</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="!newGitIdentityInput.trim()"
            @click="submitAddGitIdentity"
          >
            确认绑定
          </button>
        </div>
      </div>
    </div>

    <!-- Toast Notification -->
    <div v-if="toastMsg" class="toast-bar" style="position: fixed; bottom: 28px; right: 28px; background: #0f172a; color: #fff; padding: 12px 20px; border-radius: 10px; font-size: 0.88rem; box-shadow: var(--shadow-lg); display: flex; align-items: center; gap: 10px; z-index: 99999;">
      <span>{{ toastMsg }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { request, api } from '@/utils/api'

const members = ref([])
const unclaimedIdentities = ref([])
const searchQuery = ref('')
const toastMsg = ref('')

// Search & Add Modal State
const showSearchModal = ref(false)
const addMemberMode = ref('search') // 'search' | 'manual' | 'batch'
const candidateSearchKey = ref('')
const candidatesList = ref([])
const loadingCandidates = ref(false)
const searchedOnce = ref(false)

const manualForm = ref({
  name: '',
  email: '',
  mobile: '',
  department: '',
  gitIdentity: '',
  isManager: false,
})

const batchRawText = ref('')

// Claim Modal State
const showClaimModal = ref(false)
const claimForm = ref({ identityName: '', memberId: '' })
const claimMemberFilter = ref('')

// Quick Add Git Identity
const quickAddGitTargetMember = ref(null)
const newGitIdentityInput = ref('')

const showToast = (msg) => {
  toastMsg.value = msg
  setTimeout(() => {
    toastMsg.value = ''
  }, 3500)
}

const activeMembersCount = computed(() => {
  return members.value.filter(m => m.is_active).length
})

const filteredMembers = computed(() => {
  if (!searchQuery.value) return members.value
  const q = searchQuery.value.toLowerCase().trim()
  return members.value.filter(m => {
    const nameMatch = (m.member_name || '').toLowerCase().includes(q)
    const emailMatch = (m.email || '').toLowerCase().includes(q)
    const deptMatch = (m.department || '').toLowerCase().includes(q)
    const mobileMatch = (m.mobile || '').includes(q)
    const gitMatch = (m.git_identities || []).some(id => (id.identity || '').toLowerCase().includes(q))
    return nameMatch || emailMatch || deptMatch || mobileMatch || gitMatch
  })
})

const filteredClaimMembers = computed(() => {
  if (!claimMemberFilter.value) return members.value.filter(m => m.is_active)
  const q = claimMemberFilter.value.toLowerCase().trim()
  return members.value.filter(m =>
    m.is_active &&
    ((m.member_name || '').toLowerCase().includes(q) || (m.email || '').toLowerCase().includes(q))
  )
})

// Smart Recommendation for Claim Modal
const smartRecommendedMember = computed(() => {
  if (!claimForm.value.identityName || unclaimedIdentities.value.length === 0) return null
  const selected = unclaimedIdentities.value.find(u => u.name === claimForm.value.identityName)
  if (!selected) return null

  const target = (selected.identity || '').toLowerCase()
  const prefix = target.split('@')[0]

  // Find exact email or prefix match
  const match = members.value.find(m => {
    if (!m.is_active) return false
    const mEmail = (m.email || '').toLowerCase()
    const mName = (m.member_name || '').toLowerCase()
    return mEmail === target || mEmail.startsWith(prefix) || mName.includes(prefix)
  })
  return match || null
})

const autoSuggestMemberForClaim = () => {
  if (smartRecommendedMember.value) {
    claimForm.value.memberId = smartRecommendedMember.value.name
  }
}

const fetchMembers = async () => {
  try {
    const res = await request('/api/resource/Project Member?fields=["name","member_name","email","mobile","user_id","open_id","is_manager","is_active","department"]&limit_page_length=200&order_by=creation desc')
    const data = await res.json()
    members.value = data.data || []

    // Fetch child tables for git identities
    for (let m of members.value) {
      try {
        const detailRes = await request(`/api/resource/Project Member/${encodeURIComponent(m.name)}`)
        const detail = await detailRes.json()
        m.git_identities = detail.data?.git_identities || []
      } catch (e) {}
    }
  } catch (err) {
    console.error('获取成员列表失败:', err)
  }
}

const fetchUnclaimed = async () => {
  try {
    const res = await request('/api/method/dev_workbench.api.v1.members.get_unclaimed_identities')
    const data = await res.json()
    unclaimedIdentities.value = data.message || []
    if (unclaimedIdentities.value.length > 0 && !claimForm.value.identityName) {
      claimForm.value.identityName = unclaimedIdentities.value[0].name
      autoSuggestMemberForClaim()
    }
  } catch (err) {
    console.error('获取待认领 Git 身份失败:', err)
  }
}

const openSearchAddModal = () => {
  candidateSearchKey.value = ''
  candidatesList.value = []
  searchedOnce.value = false
  addMemberMode.value = 'search'
  showSearchModal.value = true
  handleSearchCandidates()
}

const handleSearchCandidates = async () => {
  loadingCandidates.value = true
  searchedOnce.value = true
  try {
    const key = candidateSearchKey.value.trim()
    const url = `/api/method/dev_workbench.api.v1.members.search_member_candidates?query=${encodeURIComponent(key)}`
    const res = await request(url)
    const data = await res.json()
    candidatesList.value = data.message || []
  } catch (err) {
    console.error('搜索候选人失败:', err)
  } finally {
    loadingCandidates.value = false
  }
}

const addCandidateToTeam = async (candidate) => {
  try {
    const res = await api.post('/api/method/dev_workbench.api.v1.members.add_project_member', {
      member_name: candidate.member_name,
      email: candidate.email,
      mobile: candidate.mobile,
      department: candidate.department,
      open_id: candidate.open_id,
      user_id: candidate.user_id,
    })
    const data = await res.json()
    showToast(data.message?.message || `已成功将 ${candidate.member_name} 加入团队`)
    candidate.is_existing = true
    await fetchMembers()
    await fetchUnclaimed()
  } catch (e) {
    alert('添加失败: ' + (e.message || '网络异常'))
  }
}

const submitManualAdd = async () => {
  try {
    const res = await api.post('/api/method/dev_workbench.api.v1.members.add_project_member', {
      member_name: manualForm.value.name,
      email: manualForm.value.email,
      mobile: manualForm.value.mobile,
      department: manualForm.value.department,
      git_identity: manualForm.value.gitIdentity,
      is_manager: manualForm.value.isManager ? 1 : 0,
    })
    const data = await res.json()
    showToast(data.message?.message || '成员添加成功')
    showSearchModal.value = false
    manualForm.value = { name: '', email: '', mobile: '', department: '', gitIdentity: '', isManager: false }
    await fetchMembers()
    await fetchUnclaimed()
  } catch (e) {
    alert('添加失败: ' + (e.message || '请检查输入'))
  }
}

const submitBatchAdd = async () => {
  try {
    const res = await api.post('/api/method/dev_workbench.api.v1.members.batch_add_members', {
      raw_text: batchRawText.value,
    })
    const data = await res.json()
    showToast(data.message?.message || '批量导入完成')
    showSearchModal.value = false
    batchRawText.value = ''
    await fetchMembers()
    await fetchUnclaimed()
  } catch (e) {
    alert('批量导入失败: ' + (e.message || '网络异常'))
  }
}

const openClaimModal = () => {
  showClaimModal.value = true
  claimMemberFilter.value = ''
  if (unclaimedIdentities.value.length > 0) {
    claimForm.value.identityName = unclaimedIdentities.value[0].name
    autoSuggestMemberForClaim()
  }
}

const submitClaim = async () => {
  try {
    const res = await api.post('/api/method/dev_workbench.api.v1.members.claim_git_identity', {
      member_id: claimForm.value.memberId,
      identity_name: claimForm.value.identityName,
    })
    const data = await res.json()
    showToast(data.message?.message || '认领成功')
    showClaimModal.value = false
    await fetchMembers()
    await fetchUnclaimed()
  } catch (e) {
    alert('认领失败: ' + (e.message || '网络异常'))
  }
}

const openAddGitModal = (member) => {
  quickAddGitTargetMember.value = member
  newGitIdentityInput.value = ''
}

const submitAddGitIdentity = async () => {
  if (!quickAddGitTargetMember.value || !newGitIdentityInput.value.trim()) return
  try {
    const res = await api.post('/api/method/dev_workbench.api.v1.members.add_git_identity', {
      member_id: quickAddGitTargetMember.value.name,
      identity: newGitIdentityInput.value.trim(),
    })
    const data = await res.json()
    showToast(data.message?.message || 'Git 身份绑定成功')
    quickAddGitTargetMember.value = null
    await fetchMembers()
  } catch (e) {
    alert('绑定失败: ' + (e.message || '网络异常'))
  }
}

const removeMember = async (member) => {
  if (!confirm(`确定要将成员【${member.member_name}】移出团队吗？\n移出后将不再出现在每日活动统计与缺勤提醒中。`)) {
    return
  }
  try {
    const res = await api.post('/api/method/dev_workbench.api.v1.members.remove_project_member', {
      member_id: member.name,
    })
    const data = await res.json()
    showToast(data.message?.message || '已成功移出该成员')
    await fetchMembers()
  } catch (e) {
    alert('移出失败: ' + (e.message || '网络异常'))
  }
}

onMounted(async () => {
  await fetchMembers()
  await fetchUnclaimed()
})
</script>

<style scoped>
.form-input-sm {
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-medium);
  font-family: inherit;
  font-size: 0.88rem;
  color: var(--text-primary);
  outline: none;
  background: #fff;
}

.mode-tab {
  padding: 6px 14px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.84rem;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.mode-tab.active {
  background: #fff;
  color: var(--primary);
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.avatar-circle {
  border-radius: 50%;
  background: #e0e7ff;
  color: #4338ca;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
