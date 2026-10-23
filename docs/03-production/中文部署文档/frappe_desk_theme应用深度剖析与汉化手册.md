# frappe_desk_theme 应用深度剖析与全量汉化手册

## 1. 应用概述与定位

`frappe_desk_theme` 是针对 Frappe Desk 后台界面开发的轻量级、无侵入式主题扩展应用。通过 CSS 自定义变量 (`CSS Custom Properties`) 与动态 JS 引擎，实现了对 Frappe 后台顶栏、侧边栏、表单输入框、按钮、数字卡片、表格以及登录页的全方位定制。

```text
┌─────────────────────────────────────────────────────────┐
│              frappe_desk_theme 主题引擎                 │
├─────────────────────────────────────────────────────────┤
│  1. 单例 DocType: Desk Theme (存储 30+ 颜色与开关配置)     │
│  2. 前端主题引擎: frappe_desk_theme.js (防闪烁/缓存优化) │
│  3. 样式定义层: frappe_desk_theme.css (CSS 变量映射)    │
│  4. 中国 CRM 预设库: 商务蓝 / 飞书白 / 中国红 / 翡翠绿 / 暗黑 │
│  5. 国际化层: translations/zh.csv (全量中英文映射)       │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 核心架构与原理剖析

### 2.1 数据模型 (DocType)
应用包含两个核心 DocType：
- **`Desk Theme` (Single DocType)**：核心主题配置表，包含登录页设置、导航栏样式、主/次按钮颜色、主体背景、表格与卡片样式、页脚版权等 70+ 个字段。
- **`Desk Theme Carousel Images` (Child DocType)**：登录页多图背景轮播列表。

### 2.2 前端主题引擎 (`public/js/frappe_desk_theme.js`)
- **防闪烁缓存机制 (Anti-Flicker)**：初始化时优先从浏览器 `localStorage` (`frappe_desk_theme_cache`) 读取主题，立刻应用 CSS 变量，解决页面加载时的样式闪烁问题。
- **异步数据同步**：在后台异步调用 `/api/method/frappe_desk_theme.api.get_custom_theme` 接口拉取最新配置，并更新本地缓存。
- **动态 CSS 变量注入**：将颜色配置动态挂载到 `:root` 节点的 CSS 变量上（如 `--navbar-bg`、`--sidebar-bg`、`--primary-btn-bg`）。

### 2.3 接口与渲染层 (`api.py` & `templates`)
- `get_custom_theme()`：允许匿名访问（`allow_guest=True`），在未登录状态下即可提供登录页的主题背景与轮播配置。
- `get_footer_html()`：结合 Jinja2 模板 `desk_footer.html` 动态渲染自定义页脚版权信息。

---

## 3. 中国 CRM 风格预设主题库

我们在 `Desk Theme` 表单中全新集成了 **中国主流 CRM & ERP 风格预设主题库**，支持一键切换：

| 预设方案名称 | 风格特征 | 预览色块 | 适用行业 |
| :--- | :--- | :--- | :--- |
| **经典商务蓝** *(纷享销客/销售易)* | `#0052D9` 科技蓝顶栏 + `#001529` 深青蓝侧栏 + 纯白卡片 | 顶栏[蓝] 侧栏[深青] | 科技、IT、互联网及通用 CRM 业务 |
| **极简飞书风** *(飞书/钉钉办公)* | `#FFFFFF` 纯白顶栏 + `#F5F6F7` 浅灰侧栏 + `#3370FF` 飞书蓝 | 顶栏[白] 侧栏[浅灰] | 现代办公、轻量协同与高频操作 |
| **尊贵中国红** *(国企/政企集团)* | `#B20813` 沉稳中国红 + `#1F1A1B` 灰黑侧栏 | 顶栏[红] 侧栏[灰黑] | 国企、政企单位及大型制造集团 |
| **翡翠智造绿** *(用友/鼎捷 ERP)* | `#00875A` 翡翠绿 + `#091E42` 藏青蓝侧栏 | 顶栏[绿] 侧栏[藏青] | 制造、供应链、电商及计划管理 |
| **高级暗黑夜色** *(护眼极客模式)* | `#141414` 深邃玄黑 + `#1677FF` 蓝光按键 | 顶栏[黑] 侧栏[暗灰] | 夜间运维、数据看板与高强度分析 |

---

## 4. 全量深度汉化对照表

我们建立了官方汉化文件 `frappe_desk_theme/translations/zh.csv`，涵盖所有标签与提示词：

### 4.1 选项卡与区域汉化
- `Login Page` -> `登录页配置`
- `Navbar` -> `顶部导航栏`
- `Buttons` -> `按钮样式`
- `Body` -> `主体与侧边栏`
- `Table` -> `表格与列表`
- `Widgets` -> `小组件与卡片`
- `Input` -> `输入框与表单`
- `Footer` -> `页脚设置`

### 4.2 常用字段汉化
- `Background Color` -> `背景颜色`
- `Text Color` -> `文字颜色`
- `Hover Background Color` -> `悬停背景颜色`
- `Hover Text Color` -> `悬停文字颜色`
- `Hide Help Button` -> `隐藏帮助按钮`
- `Hide App Switcher` -> `隐藏应用切换器`
- `Default App` -> `默认进入应用`
- `Sticky Footer` -> `固定置底页脚`
- `Copyright Text` -> `版权所有声明`

---

## 5. 打包与一键使用指南

### 5.1 Docker 构建配置 (`apps.json`)
确保 `frappe_docker/apps.json` 中配置了该主题仓库：

```json
[
  {
    "url": "https://codeup.aliyun.com/64c8b550dcc8d50d3cc7f5b4/jack571754/product_sales_planning.git",
    "branch": "main"
  },
  {
    "url": "https://github.com/jack571754/frappe_desk_theme.git",
    "branch": "main"
  }
]
```

### 5.2 界面启用与切换预设
1. 打开系统 `https://psp.xajuzi.com`；
2. 搜索框搜索 **`Desk Theme`** (后台主题设置)；
3. 点击顶部蓝色按钮 **`🎨 中国 CRM 预设主题库`**；
4. 点击选择对应预设方案（如 *经典商务蓝* 或 *极简飞书风*）；
5. 点击右上角 **Save** 保存，即可完成界面焕新！
