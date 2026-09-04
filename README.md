# Project-Agent 多智能体项目管理系统

按 [`task/Project-Agent系统PRD.md`](task/Project-Agent系统PRD.md) 实现的多智能体 IPD 项目管理系统。
以 **Git 为单一事实源**，用 **27 个技术角色 Agent** 驱动 **IPD 六阶段**（概念 → 计划 → 开发 → 验证 → 发布 → 生命周期）项目从需求到交付的完整生命周期，并提供三栏式深色 Web GUI 与 9 类可视化看板。

- 纯 **Python 3.12 标准库** 后端（`http.server`，零第三方依赖）
- 纯 **HTML/CSS/JS + 手写 SVG** 前端（无 CDN、无外部库，可离线运行）
- 种子数据：NPU-2TOPS 边缘视觉芯片项目（hybrid 类型，当前 development 阶段）

---

## 快速开始

```bash
# 首次运行（自动初始化 NPU 演示项目数据到 ./data/）
python3 -m server.main --port 8787

# 浏览器访问
#   GUI:  http://localhost:8787/
#   API:  http://localhost:8787/api/overview

# 重置演示数据后重启
python3 -m server.main --port 8787 --reset
```

或使用一键脚本：

```bash
./run.sh            # 启动（端口 8787）
./run.sh --reset    # 重置数据后启动
```

> 要求：Python 3.9+（开发与验证环境为 3.12）。无需 pip install 任何包。

---

## 功能总览

### IPD 六阶段与评审点
| 阶段 | 评审点 | 说明 |
|---|---|---|
| 概念 Concept | **CDCP** 概念决策评审 | 需求澄清、可行性、项目章程 |
| 计划 Plan | **PDCP** 计划决策评审 | WBS、资源、计划基线 |
| 开发 Development | **TR4** 开发完成评审 | 实现完成、自测通过 |
| 验证 Verification | **TR5** 验证完成评审 | 集成验证、回归测试 |
| 发布 Release | **GA** 通用可用 | 交付、发布 |
| 生命周期 Lifecycle | — | 维护、升级、退市 |

### 27 个技术角色 Agent（R00–R26）
| 编号 | 角色 | 职责摘要 |
|---|---|---|
| R00 | LPDT 主 Agent | 项目管理总控、需求/任务/评审主调度 |
| R01 | PMO 过程 Agent | 流程合规、里程碑、评审组织 |
| R02 | 市场洞察 Agent | 需求来源、市场与竞品分析 |
| R03 | 产品定义 Agent | 产品包需求、MRD/PRD |
| R04 | 系统架构 Agent | 系统架构、接口定义、需求分解 |
| R05 | 项目管理 Agent | 计划、WBS、风险、成本 |
| R06 | 财务分析 Agent | 财务测算、NRE/BOM 成本 |
| R07 | 质量 Agent | 质量策划、QA 门禁 |
| R08 | 测试策略 Agent | 测试策略、用例规划 |
| R09 | 数字前端 RTL Agent | RTL 设计、CDC/Lint |
| R10 | 数字验证 Agent | UVM 验证、覆盖率 |
| R11 | 模拟设计 Agent | 模拟/混合信号电路 |
| R12 | 版图设计 Agent | Layout、DRC/LVS |
| R13 | 物理实现 Agent | 综合、PNR、时序收敛 |
| R14 | 封装设计 Agent | 封装、基板、热/应力 |
| R15 | 器件工艺 Agent | 工艺 PDK、器件特性 |
| R16 | 固件/BSP Agent | 固件、Bootloader、驱动 |
| R17 | 软件算法 Agent | 算法、SDK、应用软件 |
| R18 | 系统验证 Agent | 系统级验证、bench |
| R19 | 应用方案 Agent | 应用方案、参考设计 |
| R20 | 可制造性 DFM Agent | DFM/DFT/DFA |
| R21 | 供应链 Agent | 供应链、产能、风险料 |
| R22 | 认证合规 Agent | 安规、EMC、RoHS、合规认证 |
| R23 | 文档 Agent | 文档资产、变更记录 |
| R24 | 发布运维 Agent | 发布计划、版本、运维 |
| R25 | 客户支持 Agent | 客户反馈、售后、问题闭环 |
| R26 | 战略规划 Agent | 路标、战略对齐、组合 |

每种项目类型（`soc` / `hybrid` / `chiplet` / `ip` / `template` / `sw`）按参与矩阵自动激活对应角色集。

### Agent 通信协议
- 6 种通信类型：`request`（请求）/ `escalation`（升级）/ `notification`（通知）/ `report`（报告）/ `user_message`（用户消息）/ `review_response`（评审响应）
- 状态机：`pending → accepted / rejected / blocked → in_progress → completed → closed`
- 每条通信自动归档为 `data/communications/COMM-{n}.yaml`（§6.1 协议完整落地）

### Git 单一事实源（§5）
- 仓库拓扑：`project-main` + `{role_abbr}-{n}` 子仓库 + `docs/`、`deliverables/`、`submodules/` 目录
- Commit Message 规范：`type(scope): subject` + 结构化正文
  - `Refs: Requirement/Task/Communication/Parent-Commit/Agent/Phase` + `Change-Id`
  - type 枚举：`feat` `fix` `docs` `refactor` `test` `chore` `review` `comm` `plan`
- 内置 **Commit Message 校验器**（GUI 校验视图 + `/api/commit/check`）

### 可视化看板（9+1 视图）
总览（进度环/甘特图/风险/活动流）· 阶段看板（Kanban）· 角色视图 · 需求追溯链 · 通信拓扑图+时间线 · 提交 Git 图 · 评审时间线（CDCP/PDCP/TR4/TR5/GA）· 聊天 · 代码浏览 · Commit 校验

---

## 仓库结构

```
projagent/
├── task/
│   └── Project-Agent系统PRD.md   # 需求规格（PRD）
├── server/                       # 后端（Python 标准库）
│   ├── main.py                   # HTTP 入口（端口 8787，--reset 重建）
│   ├── api.py                    # REST API 路由
│   ├── core/
│   │   ├── roles.py              # 27 角色注册表 + IPD 参与矩阵 + 项目类型映射
│   │   ├── ids.py                # REQ/TASK/COMM/Change-Id 生成器
│   │   ├── models.py             # 核心数据模型
│   │   ├── comm.py               # CommunicationBus 状态机 + YAML 归档
│   │   ├── commit.py             # Commit Message 生成/解析/校验（§5.4）
│   │   ├── requirements.py       # 需求管理 + 追溯链构建（§7/§9.3.4）
│   │   ├── store.py              # JSON 持久化（§5.1 仓库拓扑模拟）
│   │   ├── wbs.py                # WBS + 关键路径（§4.1.2/§13.4）
│   │   ├── agent_engine.py       # Agent 运行时：主从分配/对等通信/escalation/单步推进
│   │   └── system.py             # ProjectSystem 主类 + overview 聚合
│   └── seed/
│       └── demo_npu.py           # NPU-2TOPS 演示种子数据（§8.2）
├── web/                          # 前端（纯 JS + 手写 SVG）
│   ├── index.html                # 三栏布局 + 顶部导航 + 底部状态栏
│   ├── css/app.css               # 深色主题（§10.3 规范）
│   └── js/
│       ├── api.js                # REST API 封装
│       ├── ui.js                 # UI 基础组件
│       ├── charts.js             # SVG 图表（环形/甘特/拓扑/Git 图）
│       ├── views.js              # 10 个视图 + 详情面板
│       └── app.js                # 路由（含 #hash 直达）+ 全局搜索 + 运行演示 + 重置
├── run.sh                        # 一键启动脚本
└── data/                         # 运行时生成（JSON 数据 + 通信 YAML 归档），不纳入版本库
```

---

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/overview` | 总览聚合（进度/阶段/风险/活动流） |
| GET | `/api/project` | 项目元信息 + 评审点状态 |
| GET | `/api/roles` | 27 角色 + 阶段参与矩阵 |
| GET | `/api/requirements` | 需求列表 + 追溯链 |
| GET | `/api/tasks` | 任务列表（Kanban） |
| GET | `/api/communications` | 通信 + 拓扑边 |
| GET | `/api/commits` | 提交列表（Git 图） |
| GET | `/api/repos/tree` | 仓库拓扑树（代码浏览） |
| GET | `/api/repos/content` | 仓库文件内容 |
| GET | `/api/wbs` | WBS + 关键路径（甘特图） |
| POST | `/api/chat` | 向主 Agent 发消息（生成通信记录） |
| POST | `/api/simulate` | 单步推进一次 Agent 仿真 |
| POST | `/api/commit/check` | 校验 Commit Message |
| GET | `/api/search?q=` | 全局搜索 |

---

## PRD 覆盖对照

| PRD 章节 | 实现位置 |
|---|---|
| §3.2/§3.3 27 角色 + 参与矩阵 | `server/core/roles.py` |
| §4.1.2/§13.4 WBS + 关键路径 | `server/core/wbs.py` |
| §4.3 主从/对等/escalation 协作 | `server/core/agent_engine.py` |
| §5.1 仓库拓扑 / §5.4 Commit 规范 | `server/core/store.py` / `server/core/commit.py` |
| §6 Agent 通信协议 + 状态机 | `server/core/comm.py` |
| §7/§9.3.4 需求层级与追溯链 | `server/core/requirements.py` |
| §8.2 NPU 示例项目 | `server/seed/demo_npu.py` |
| §9 9 类可视化看板 | `web/js/views.js` + `web/js/charts.js` |
| §10.3 三栏 GUI 深色主题 | `web/index.html` + `web/css/app.css` |
| §11.2 数据模型 | `server/core/models.py` |
