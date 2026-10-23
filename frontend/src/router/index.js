import { createRouter, createWebHistory } from 'vue-router'

import DashboardLayout from '@/components/DashboardLayout.vue'
import DailyActivityPage from '@/pages/DailyActivityPage.vue'
import AbsenceActivityPage from '@/pages/AbsenceActivityPage.vue'
import ProjectTrendPage from '@/pages/ProjectTrendPage.vue'
import ReportArchivePage from '@/pages/ReportArchivePage.vue'
import ProjectSettingsPage from '@/pages/ProjectSettingsPage.vue'
import MemberSettingsPage from '@/pages/MemberSettingsPage.vue'
import RepositoryConfigPage from '@/pages/RepositoryConfigPage.vue'
import AbsenceExemptionPage from '@/pages/AbsenceExemptionPage.vue'
import UnauthorizedPage from '@/pages/UnauthorizedPage.vue'

const routes = [
  {
    path: '/',
    redirect: '/dashboard/daily-activity',
  },
  {
    path: '/dashboard',
    component: DashboardLayout,
    redirect: '/dashboard/daily-activity',
    children: [
      {
        path: 'code-review',
        name: 'CodeReview',
        component: () => import('@/pages/CodeReviewPage.vue'),
        meta: { title: '代码审查 - 研发工作台' },
      },
      {
        path: 'code-review/:id',
        name: 'CodeReviewDetail',
        component: () => import('@/pages/CodeReviewDetailPage.vue'),
        meta: { title: '审查详情 - 研发工作台' },
      },
      {
        path: 'daily-activity',
        name: 'DailyActivity',
        component: DailyActivityPage,
        meta: { title: '成员工作量 - 研发工作台' },
      },
      {
        path: 'absence-activity',
        name: 'AbsenceActivity',
        component: AbsenceActivityPage,
        meta: { title: '缺勤跟进 - 研发工作台' },
      },
      {
        path: 'project-trend',
        name: 'ProjectTrend',
        component: ProjectTrendPage,
        meta: { title: '项目活跃度 - 研发工作台' },
      },
      {
        path: 'report-archive',
        name: 'ReportArchive',
        component: ReportArchivePage,
        meta: { title: '日报归档 - 研发工作台' },
      },
    ],
  },
  {
    path: '/projects',
    name: 'Projects',
    component: ProjectSettingsPage,
    meta: { title: '项目配置 - 研发工作台' },
  },
  {
    path: '/members',
    name: 'Members',
    component: MemberSettingsPage,
    meta: { title: '成员配置 - 研发工作台' },
  },
  {
    path: '/repositories',
    name: 'Repositories',
    component: RepositoryConfigPage,
    meta: { title: '仓库配置 - 研发工作台' },
  },
  {
    path: '/exemptions',
    name: 'Exemptions',
    component: AbsenceExemptionPage,
    meta: { title: '请假豁免 - 研发工作台' },
  },
  {
    path: '/unauthorized',
    name: 'Unauthorized',
    component: UnauthorizedPage,
    meta: { title: '无权限访问 - 研发工作台' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard/daily-activity',
  },
]

const router = createRouter({
  history: createWebHistory('/dev-workbench'),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.path !== from.path) return { top: 0 }
    return false
  },
})

// Navigation Guard: Manager Permission Middleware
router.beforeEach((to, from, next) => {
  if (to.meta?.title) {
    document.title = to.meta.title
  }

  const boot = typeof window !== 'undefined' ? window.boot : null
  const isManager = boot?.is_manager === true || boot?.user === 'Administrator' || (boot?.roles && boot.roles.includes('Dev Workbench Manager'))

  if (!isManager && to.path !== '/unauthorized') {
    next('/unauthorized')
  } else if (isManager && to.path === '/unauthorized') {
    next('/dashboard/daily-activity')
  } else {
    next()
  }
})

export default router
