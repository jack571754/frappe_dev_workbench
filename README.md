# Dev Workbench (研发工作台)

> 面向研发团队的全链路效能度量与自动化协同平台，基于 **Frappe Framework** 与 **Vue 3 SPA** 构建。

---

## 📌 功能概览与核心特性

- **代码活动自动采集**：无缝对接阿里云云效 (Codeup API)，自动化增量抓取 Git 提交、核算增减行数与修改文件数；
- **智能身份闭环体系**：支持一人多 Git 邮箱/用户名别名绑定，支持未归属提交隔离与一键认领；
- **大模型 AI 摘要提炼**：接入主流 LLM 大模型（DeepSeek / Qwen / OpenAI），自动过滤 Merge 杂音，提炼每日真实业务功能产出；
- **智能考勤与豁免判定**：工作日下班后自动排查无产出异常，支持考勤豁免实时流转与请假对齐；
- **飞书富文本互动卡片**：工作日定时自动推送精美飞书卡片至主管与研发大群，支持在线重推与历史回溯；
- **决策级看板 (Vue 3 SPA)**：通过 Frappe Apps/Workspace 入口独立访问，支持 12 周活跃度趋势折线图、多维度横向项目对比与个人聚焦。

---

## 📖 详细设计与流程拆解文档

系统完整的设计架构、数据模型与六大核心业务流程已归档至专门文档：

👉 **[完整功能架构与流程拆解文档 (dev_workbench_architecture_and_flow.md)](./docs/dev_workbench_architecture_and_flow.md)**

- [1. 系统定位与核心价值](./docs/dev_workbench_architecture_and_flow.md#1-系统定位与核心价值)
- [2. 总体系统架构与技术栈](./docs/dev_workbench_architecture_and_flow.md#2-总体系统架构与技术栈)
- [3. 核心数据模型 (DocTypes) 设计](./docs/dev_workbench_architecture_and_flow.md#3-核心数据模型-doctypes-设计)
- [4. 六大核心业务流程拆解 (Mermaid 流程图)](./docs/dev_workbench_architecture_and_flow.md#4-六大核心业务流程拆解)
- [5. API 接口清单与路由映射规范](./docs/dev_workbench_architecture_and_flow.md#5-api-接口清单与路由映射规范)
- [6. 定时任务 (Scheduler Events) 调度清单](./docs/dev_workbench_architecture_and_flow.md#6-定时任务-scheduler-events-调度清单)
- [7. 研发看板 (Vue SPA) 页面功能矩阵](./docs/dev_workbench_architecture_and_flow.md#7-研发看板-vue-spa-页面功能矩阵)

---

## 🚀 安装与部署

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app dev_workbench
bench --site development.localhost migrate
```

### 前端 SPA 构建

```bash
cd apps/dev_workbench/frontend
npm ci
npm run build
```

SPA 固定托管于 `/dev-workbench`，业务操作通过 Frappe 标准
`/api/method/dev_workbench.api.v1.*` 接口访问，普通 DocType 列表使用 Frappe Resource API。

---

## 🛠 代码规范与贡献

本项目采用 `pre-commit` 统一管理代码格式化和检查：

```bash
cd apps/dev_workbench
pre-commit install
pre-commit run --all-files
```

---

## 📄 开源许可证

MIT License
