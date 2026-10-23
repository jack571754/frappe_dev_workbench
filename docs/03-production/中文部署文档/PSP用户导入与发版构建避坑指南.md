# PSP 用户导入功能重构与镜像构建发版避坑指南

本手册记录了 **PSP 系统（Product Sales Planning）** 用户导入模块的重构优化细节、前端与后端交互机制、Docker 镜像构建缓存避坑指南以及完整的发版部署流程。

---

## 目录
- [一、 业务需求与坑点背景](#一-业务需求与坑点背景)
- [二、 用户导入模块重构方案](#二-用户导入模块重构方案)
  - [1. 后端接口设计 (`import_feishu_users.py`)](#1-后端接口设计-import_feishu_userspy)
  - [2. 前端弹窗重构 (`permission_config_list.js`)](#2-前端弹窗重构-permission_config_listjs)
- [三、 Docker 镜像构建缓存避坑指南](#三-docker-镜像构建缓存避坑指南)
  - [1. 痛点分析：为什么打出的镜像总是旧代码？](#1-痛点分析为什么打出的镜像总是旧代码)
  - [2. 解决方案：`CACHE_BUST` 动态时间戳](#2-解决方案cache_bust-动态时间戳)
- [四、 完整发版部署全流程 SOP](#四-完整发版部署全流程-sop)

---

## 一、 业务需求与坑点背景

在 Frappe Desk 中，通过 `Permission Config`（数据权限配置）列表页的「用户导入」按钮调起弹窗，用于添加飞书成员或批量导入账号。原实现存在以下痛点与坑点：

1. **控件缺失/未响应**：原弹窗使用 `{ fieldname: 'file', fieldtype: 'Attach' }` 控件。由于 `frappe.ui.Dialog` 缺乏关联的 Doc 模型实例，选择/上传文件后**无法触发 `df.onchange` 事件**，导致弹窗既无直观表单输入框，也无法自动完成文件解析与预览。
2. **缺乏单人录入方式**：原逻辑仅支持 Excel 批量导入，若管理员只需临时添加 1~2 名员工，仍必须下载/填写 Excel 文件，使用体验繁琐。
3. **镜像构建缓存机制**：在本地 WSL 中执行打包脚本 `update-frappe-only.sh` 时，Docker 默认会缓存 `bench init` 和 `git clone` 的构建层（`CACHED`），导致即使将最新代码推送到远程 Git 仓库，构建出来的 Docker 镜像仍然使用的是旧代码。

---

## 二、 用户导入模块重构方案

### 1. 后端接口设计 (`import_feishu_users.py`)

文件路径：[import_feishu_users.py](file:///d:/project/02-%E5%BC%80%E6%BA%90%E9%A1%B9%E7%9B%AE/frappe_docker/development/frappe-bench/apps/product_sales_planning/product_sales_planning/api/v1/import_feishu_users.py)

#### 新增单人录入 API (`add_single_feishu_user`)
- **权限校验**：仅限 `System Manager`（系统管理员）调用。
- **手机号归一化**：自动过滤空格、横线及 `+86` 前缀。
- **飞书 OpenID 自动匹配**：根据手机号调用飞书 `batch_get_id` 接口检索 `open_id`。如果成员不在企业飞书通讯录中，给出明确错误提示。
- **用户创建**：自动创建用户账号（Email 格式为 `{mobile}@juzi.com`），初始密码设为 `Jz123456`，默认赋予 `Planning Admin` 角色并绑定飞书社交登录。

```python
@frappe.whitelist()
@handle_exceptions
def add_single_feishu_user(name, mobile):
    """手动添加单个飞书用户：自动从飞书获取 openid 并创建账户。"""
    _require_system_manager()
    validate_required_params({"mobile": mobile}, ["mobile"])
    mobile = normalize_mobile(mobile)
    if not mobile or len(mobile) != 11 or not mobile.isdigit():
        frappe.throw(_("手机号格式无效（请输入 11 位有效手机号）"))

    if _user_exists(mobile):
        frappe.throw(_(f"手机号为 {mobile} 的用户已存在"))

    open_id_map = _resolve_open_ids([mobile])
    open_id = open_id_map.get(mobile)
    if not open_id:
        frappe.throw(_(f"未在飞书企业通讯录中查找到手机号为 {mobile} 的成员，请确认该成员已加入企业飞书"))

    email, action = create_or_update_user(open_id, mobile, name=name)
    frappe.db.commit()
    return success_response(
        message=f"用户 {name or mobile} ({email}) 创建成功",
        email=email,
        name=name or mobile,
        mobile=mobile,
        open_id=open_id,
        action=action,
    )
```

---

### 2. 前端弹窗重构 (`permission_config_list.js`)

文件路径：[permission_config_list.js](file:///d:/project/02-%E5%BC%80%E6%BA%90%E9%A1%B9%E7%9B%AE/frappe_docker/development/frappe-bench/apps/product_sales_planning/product_sales_planning/public/js/permission_config_list.js)

弹窗重构为**双 Tab 交互界面**：

```
+-------------------------------------------------------------+
| 飞书用户录入 / 批量导入                              [ X ]  |
+-------------------------------------------------------------+
| [ 手动录入用户 ]   [ Excel 批量导入 ]                        |
+-------------------------------------------------------------+
| (Tab 1: 手动录入用户)                                        |
| 姓名 *:   [ 请输入成员姓名 (如：张三)                      ] |
| 手机号 *: [ 请输入 11 位手机号 (如：13800138000)            ] |
|                                       [ 确认添加用户 ]      |
|                                                             |
| (Tab 2: Excel 批量导入)                                     |
| [ 下载导入模板 (.xlsx) ]   [ 选择 Excel 文件并解析 ]        |
| 上传状态: 未选择文件 / 正在上传并解析... / 已上传: xxx.xlsx |
| 预览数据校验表格与结果提示                                    |
+-------------------------------------------------------------+
```

---

## 三、 Docker 镜像构建缓存避坑指南

### 1. 痛点分析：为什么打出的镜像总是旧代码？

在执行构建脚本 [update-frappe-only.sh](file:///d:/project/02-%E5%BC%80%E6%BA%90%E9%A1%B9%E7%9B%AE/frappe_docker/scripts/update-frappe-only.sh) 时，控制台如果输出：

```text
=> CACHED [builder 2/2] RUN --mount=type=secret,id=apps_json...
```

说明 Docker 引擎判断 `Containerfile` 和本地复制的文件没有变动，因此跳过了 `bench init` / `git clone` 步骤，直接复用了上一次的镜像缓存。导致**远程 Git 仓库虽然已经推送了最新代码，但打出来的 Docker 镜像包含的依然是旧代码**。

### 2. 解决方案：`CACHE_BUST` 动态时间戳

在 [update-frappe-only.sh](file:///d:/project/02-%E5%BC%80%E6%BA%90%E9%A1%B9%E7%9B%AE/frappe_docker/scripts/update-frappe-only.sh) 中动态生成当前 Unix 时间戳，并向 `docker build` 传入 `--build-arg=CACHE_BUST="${CACHE_BUST}"` 参数：

```bash
echo "[2/4] 构建镜像..."
CACHE_BUST="$(date +%s)"

docker build \
  --network=host \
  --secret=id=apps_json,src=apps.json \
  --build-arg=CACHE_BUST="${CACHE_BUST}" \
  --tag="${REGISTRY}/frappev16:${TMP_TAG}" \
  --file=images/layered/Containerfile .
```

- **机制原理**：容器构建文件 `Containerfile` 中含有 `ARG CACHE_BUST=""` 和 `: "${CACHE_BUST}"` 语句。一旦传入的时间戳发生变化，Docker 会判定该层缓存失效，强制重新拉取 Git 远程仓库的最新代码。

---

## 四、 完整发版部署全流程 SOP

### 第一步：提交代码到 Git 远程仓库
在应用目录 `product_sales_planning` 中提交并推送修改：
```bash
cd d:\project\02-开源项目\frappe_docker\development\frappe-bench\apps\product_sales_planning
git add product_sales_planning/api/v1/import_feishu_users.py product_sales_planning/public/js/permission_config_list.js
git commit -m "feat(user-import): add manual user entry form and fix dialog file upload"
git push upstream main
```

### 第二步：在 WSL 环境中打包 Docker 镜像
打开 WSL Ubuntu-24.04 终端，执行打包脚本：
```bash
wsl -d Ubuntu-24.04
bash /mnt/d/project/02-开源项目/frappe_docker/scripts/update-frappe-only.sh
```

确认日志中 `[3/4] 验证镜像` 能够正常输出 `product_sales_planning 0.0.1` 且无报错。

### 第三步：打正式 Tag 并推送到阿里云镜像仓库
```bash
# 定义仓库变量与新版本 Tag（如 v1.1.1）
REG=crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723/frappev16
FINAL_TAG=v1.1.1

# 打 Tag 并推送
docker tag $REG:tmp-frappe-update $REG:${FINAL_TAG}
docker login --username=15309154328 $REG
docker push $REG:${FINAL_TAG}
```

### 第四步：登录生产服务器执行热更新与迁移
```bash
ssh root@172.16.200.44
/root/gitops/deploy-update.sh v1.1.1
```

部署脚本会自动拉取最新镜像、重启容器并运行 `bench migrate` 完成全量发布！
