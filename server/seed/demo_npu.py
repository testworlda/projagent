# -*- coding: utf-8 -*-
"""
demo_npu.py — 演示项目种子数据（NPU 芯片，软硬件协同）
按照 PRD §8.2 的示例构建一个支持 8 路摄像头输入、算力 2TOPS、功耗≤2W
的 NPU 芯片项目。系统处于「开发阶段」（concept/plan 已完成，development 进行中），
包含完整的需求层级、任务、通信记录与 Commit 历史，用于直接展示看板/追溯链/
通信拓扑/提交图等全部视图。
数据全部依据 PRD 的数据结构与 Commit 规范构造，可复现。
"""
from ..core import roles as roles_mod
from ..core import models
from ..core.ids import make_change_id
from ..core.commit import format_commit

def seed(system):
    """在 system 上初始化演示项目。"""
    system.create_project(
        "NPU-2TOPS 边缘视觉芯片", "hybrid",
        description="支持 8 路摄像头输入，算力 2TOPS，功耗≤2W 的边缘 AI 视觉 SoC",
    )
    project = system.project
    project["current_phase"] = "development"
    project["status"] = "active"
    system.store.save_project(project)
    ids = system.ids
    req_mgr = system.requirements
    bus = system.bus
    store = system.store
    rt = system.runtime

    # ------------------------------------------------------------------ #
    # 0. 初始提交（主仓库基线）
    # ------------------------------------------------------------------ #
    def main_commit(ctype, scope, subject, body="", phase="concept", reqs=None, tasks=None, comms=None, parent=None, branch="main"):
        rec = rt.commit("main", ctype, scope, subject, body=body,
                        requirement_ids=reqs or [], task_ids=tasks or [],
                        comm_ids=comms or [], parent_commit=parent, phase=phase, branch=branch)
        system.main_commit = rec["hash"]
        return rec

    c0 = main_commit("plan", "project", "初始化项目主仓库与角色注册",
                     body="创建 .project-agent 元数据、docs、deliverables 目录结构，注册激活角色。",
                     phase="concept")

    # ------------------------------------------------------------------ #
    # 1. 概念阶段：项目级需求与系统架构
    # ------------------------------------------------------------------ #
    r_req = req_mgr.create(
        ids.next_req(), "8 路摄像头 NPU 边缘视觉芯片",
        "设计一款支持 8 路摄像头输入、AI 算力 2TOPS、典型功耗≤2W 的边缘视觉 SoC，"
        "面向智能安防与工业视觉场景，需支持 H.264 编码与主流 CNN 模型推理。",
        "user", "用户原始需求", parent_commit=c0["short"], priority="critical",
        phase="concept", assigned_role="R00",
        acceptance_criteria=[
            "8 路 MIPI-CSI 输入同时工作",
            "INT8 算力≥2TOPS",
            "整机典型功耗≤2W",
            "通过 SIT 系统集成测试",
        ],
    )
    # 主 Agent 完成概念阶段 WBS 拆解
    c1 = main_commit("plan", "wbs", "概念阶段 WBS 拆解完成",
                     body="完成概念阶段 6 个工作包拆解，识别关键技术风险：多路 MIPI 输入带宽、NPU 功耗收敛。",
                     phase="concept", reqs=[r_req["id"]], parent=c0["short"])
    system.requirements.update_status(r_req["id"], "in_progress", commit=c1["short"])
    # SE Agent 产出 SRS 与系统架构
    se = system.get_agent_by_role("R01")
    se["status"] = "working"
    store.save_agents(system.agents)
    c2 = rt.commit(se["id"], "docs", "srs", "系统需求规格 SRS v0.9",
                   body="完成系统需求规格初稿：功能需求 24 项、性能需求 12 项、接口需求 8 项。\n自检：需求可追踪性检查通过。",
                   requirement_ids=[r_req["id"]], parent_commit=c1["short"], phase="concept",
                   files=[{"path": "docs/srs_v0.9.md", "change_type": "add"}])
    c3 = rt.commit(se["id"], "docs", "arch", "系统架构设计 v0.8",
                   body="定义 SoC 整体架构：8x MIPI-CSI → ISP → NPU → 编码器 → DDR。\n接口控制文档 ICD 初版。",
                   requirement_ids=[r_req["id"]], parent_commit=c2["short"], phase="concept",
                   files=[{"path": "docs/architecture_v0.8.md", "change_type": "add"}])
    # TRL 技术预研报告
    trl = system.get_agent_by_role("R02")
    trl["status"] = "working"
    store.save_agents(system.agents)
    c4 = rt.commit(trl["id"], "docs", "trl", "技术预研：NPU 内核选型评估",
                   body="对比 3 家 NPU IP 方案，推荐自研 2TOPS INT8 内核，功耗余量 18%。\n原型验证通过。",
                   requirement_ids=[r_req["id"]], parent_commit=c1["short"], phase="concept",
                   files=[{"path": "docs/trl_npu_survey.md", "change_type": "add"}])
    # PQA 质量计划
    pqa = system.get_agent_by_role("R23")
    c5 = rt.commit(pqa["id"], "docs", "qa", "项目质量计划 v0.1",
                   body="定义质量目标：缺陷密度<0.5/KLOC，TR4 前功能覆盖率≥85%。",
                   requirement_ids=[r_req["id"]], parent_commit=c1["short"], phase="concept",
                   files=[{"path": "docs/quality_plan.md", "change_type": "add"}])
    # CDCP 评审通过（评审点）
    c6 = main_commit("review", "dcp", "CDCP 概念决策评审通过",
                     body="概念阶段评审通过：技术可行性验证完成，系统概念明确，批准进入计划阶段。",
                     phase="concept", reqs=[r_req["id"]], parent=c1["short"])

    # ------------------------------------------------------------------ #
    # 2. 计划阶段：详细技术方案与计划
    # ------------------------------------------------------------------ #
    project["current_phase"] = "plan"
    store.save_project(project)
    p1 = req_mgr.create(
        ids.next_req(), "系统详细技术方案与计划",
        "制定系统详细技术方案：硬件架构、软件架构、验证策略、资源估算、风险评估。",
        "main_agent", "主 Agent 计划阶段 WBS 拆解", parent_commit=c6["short"],
        priority="high", phase="plan", assigned_role="R01",
        acceptance_criteria=["PDCP 评审通过", "资源估算误差<15%", "风险清单≥8 项"],
    )
    c7 = main_commit("plan", "wbs", "计划阶段 WBS 拆解完成",
                     body="完成计划阶段 10 个工作包：硬件方案/软件方案/验证方案/资源估算/风险评估。",
                     phase="plan", reqs=[p1["id"]], parent=c6["short"])
    # SE 详细方案
    c8 = rt.commit(se["id"], "docs", "plan", "系统技术方案 v1.0",
                   body="完成系统级技术方案：模块划分 16 个、接口定义 32 项、资源估算完成。",
                   requirement_ids=[p1["id"]], parent_commit=c7["short"], phase="plan",
                   files=[{"path": "docs/system_plan_v1.0.md", "change_type": "add"}])
    # 软件架构师技术选型
    sarch = system.get_agent_by_role("R10")
    sarch["status"] = "working"
    store.save_agents(system.agents)
    c9 = rt.commit(sarch["id"], "docs", "swarch", "软件架构与 RTOS 选型",
                   body="选择 Zephyr RTOS + 自研 HAL 层，软件模块划分 9 个，API 规范 v0.5。",
                   requirement_ids=[p1["id"]], parent_commit=c7["short"], phase="plan",
                   files=[{"path": "docs/sw_architecture.md", "change_type": "add"}])
    # EE 硬件规格
    ee = system.get_agent_by_role("R03")
    ee["status"] = "working"
    store.save_agents(system.agents)
    c10 = rt.commit(ee["id"], "docs", "hw", "硬件规格定义 v0.9",
                    body="定义电源树（12 路 LDO/DC-DC）、时钟方案（27MHz 晶振 + 2 路 PLL）、DDR 配置。",
                    requirement_ids=[p1["id"]], parent_commit=c7["short"], phase="plan",
                    files=[{"path": "docs/hw_spec_v0.9.md", "change_type": "add"}])
    # PDCP 评审
    c11 = main_commit("review", "dcp", "PDCP 计划决策评审通过",
                      body="计划阶段评审通过：技术方案与资源估算确认，批准进入开发阶段。",
                      phase="plan", reqs=[p1["id"]], parent=c7["short"])
    system.requirements.update_status(p1["id"], "completed", commit=c11["short"])

    # ------------------------------------------------------------------ #
    # 3. 开发阶段：详细设计与实现（进行中）
    # ------------------------------------------------------------------ #
    project["current_phase"] = "development"
    store.save_project(project)
    # --- 3.1 AXI4-Lite 从机接口（对应 PRD 示例 REQ-0023） ---
    rtl = system.get_agent_by_role("R05")
    rtl["status"] = "working"
    store.save_agents(system.agents)
    r_axi = req_mgr.create(
        ids.next_req(), "AXI4-Lite 从机接口设计",
        "实现符合 AXI4-Lite 协议的从机接口模块，支持寄存器读写，工作频率 100MHz，需支持异步时钟域跨越。",
        "main_agent", "主 Agent 开发阶段 WBS 拆解", parent_commit=c11["short"],
        priority="high", phase="development", assigned_role="R05",
        acceptance_criteria=[
            "AXI4-Lite 协议一致性检查通过",
            "模块级功能覆盖率≥90%",
            "时序收敛（100MHz 下 WNS≥0）",
            "通过 DV Agent 的功能验证",
        ],
    )
    # SE→EE 对等通信：请求时钟域规格（对应 PRD §6.1 示例）
    comm_axi = rt.peer_request(se["id"], ee["id"], "request", "AXI4-Lite 接口时钟域需求",
        "我在实现 AXI4-Lite 从机接口时，需要确认以下硬件相关需求：\n"
        "1. 接口工作时钟频率预期是多少？\n"
        "2. 是否需要支持异步时钟域跨越？\n"
        "3. 复位策略是同步复位还是异步复位？",
        requirement_ids=[r_axi["id"]], priority="high")
    # EE 响应并闭环
    rt.respond_comm(comm_axi["id"], ee["id"])
    ee_resp = rt.commit(ee["id"], "docs", "hw_spec", "AXI 接口硬件规格确认",
                        body="已确认：接口时钟 100MHz，需支持异步时钟域（与核心 500MHz 跨域），异步复位同步释放。",
                        requirement_ids=[r_axi["id"]], comm_ids=[comm_axi["id"]],
                        parent_commit=c10["short"], phase="development",
                        files=[{"path": "docs/hw_spec_axi.md", "change_type": "add"}])
    # 主 Agent 分配 AXI4-Lite 任务给 RTL
    t_axi = models.new_task(
        ids.next_task(), "AXI4-Lite 从机接口 RTL 实现",
        "实现 AXI4-Lite 从机接口 RTL：5 通道信号处理、地址解码与寄存器映射、错误响应机制。",
        r_axi["id"], rtl["id"], "development",
        priority="high", status="in_progress",
        acceptance_criteria=["协议一致性检查通过", "模块功能覆盖率≥90%", "WNS≥0@100MHz"],
    )
    system.add_task(t_axi)
    rt.main_assign_task(rtl["id"], t_axi)
    # RTL 执行子任务
    rt.execute_task(rtl["id"], t_axi["id"], [
        {"ctype": "feat", "scope": "rtl", "subject": "实现 AXI4-Lite 5 通道从机接口",
         "body": "完成 AW/AR/R/W/B 通道逻辑与地址解码，寄存器映射 16 个。\n自检：lint 通过。",
         "files": [{"path": "rtl/axi4_lite_slave.v", "change_type": "add"}]},
        {"ctype": "feat", "scope": "rtl", "subject": "异步时钟域跨越同步逻辑",
         "body": "实现两级同步器与握手逻辑，完成 CDC 检查。\n自检：CDC 无违例。",
         "files": [{"path": "rtl/axi_cdc.v", "change_type": "add"}]},
        {"ctype": "test", "scope": "rtl", "subject": "AXI4-Lite 模块级功能仿真",
         "body": "编写 testbench，覆盖读写/错误/跨域场景，功能覆盖率 92%。\n自检：全部用例通过。",
         "files": [{"path": "tb/tb_axi4_lite.sv", "change_type": "add"}]},
    ], parent_commit=c11["short"])
    system.requirements.update_status(r_axi["id"], "completed")
    # RTL 向 DV 请求验证（对等协作）
    dv = system.get_agent_by_role("R16")
    dv["status"] = "working"
    store.save_agents(system.agents)
    comm_dv = rt.peer_request(rtl["id"], dv["id"], "request", "AXI4-Lite 功能验证请求",
        "AXI4-Lite 从机接口已完成 RTL 实现并自检通过，请开展独立功能验证，"
        "重点覆盖异步时钟域跨越与错误响应场景。",
        requirement_ids=[r_axi["id"]], task_ids=[t_axi["id"]], priority="high")
    rt.respond_comm(comm_dv["id"], dv["id"])
    dv_comm = rt.commit(dv["id"], "test", "dv", "AXI4-Lite UVM 验证环境搭建",
                        body="搭建 UVM 验证环境：driver/monitor/scoreboard，编写定向测试 12 条。",
                        requirement_ids=[r_axi["id"]], comm_ids=[comm_dv["id"]],
                        parent_commit=None, phase="development",
                        files=[{"path": "dv/axi_env.sv", "change_type": "add"}])
    # --- 3.2 NPU 内核（进行中） ---
    r_npu = req_mgr.create(
        ids.next_req(), "NPU 推理内核设计",
        "设计 2TOPS INT8 NPU 推理内核：MAC 阵列、激活、量化、DMA 调度，支持主流 CNN。",
        "main_agent", "主 Agent 开发阶段 WBS 拆解", parent_commit=c11["short"],
        priority="critical", phase="development", assigned_role="R05",
        acceptance_criteria=["算力≥2TOPS INT8", "功耗≤1.2W（内核）", "支持 Conv/FC/Pool/激活", "DV 验证通过"],
    )
    t_npu = models.new_task(
        ids.next_task(), "NPU MAC 阵列设计",
        "设计 128x64 的 INT8 MAC 阵列与脉动数据流，支持 Winograd 卷积。",
        r_npu["id"], rtl["id"], "development",
        priority="critical", status="in_progress",
        acceptance_criteria=["单周期 8192 MAC", "时钟 500MHz", "综合面积≤1.2mm²"],
    )
    system.add_task(t_npu)
    rt.main_assign_task(rtl["id"], t_npu)
    rt.execute_task(rtl["id"], t_npu["id"], [
        {"ctype": "feat", "scope": "rtl", "subject": "NPU MAC 阵列 RTL 设计",
         "body": "完成 128x64 脉动阵列 RTL 与权重缓冲，支持 Winograd。\n自检：仿真通过。",
         "files": [{"path": "rtl/npu_mac_array.v", "change_type": "add"}]},
        {"ctype": "test", "scope": "rtl", "subject": "NPU 内核模块级仿真",
         "body": "验证卷积正确性（对比参考模型），性能 2.1TOPS。\n自检：通过。",
         "files": [{"path": "tb/tb_npu_mac.sv", "change_type": "add"}]},
    ], parent_commit=c11["short"])
    # ALG 算法与量化
    alg = system.get_agent_by_role("R14")
    alg["status"] = "working"
    store.save_agents(system.agents)
    t_quant = models.new_task(
        ids.next_task(), "模型量化工具链开发",
        "开发 INT8 量化工具链：PTQ/QAT 支持、校准数据集、精度评估。",
        r_npu["id"], alg["id"], "development",
        priority="high", status="in_progress",
        acceptance_criteria=["量化后精度损失<1%", "支持 ResNet/MobileNet/YOLO"],
    )
    system.add_task(t_quant)
    rt.main_assign_task(alg["id"], t_quant)
    rt.execute_task(alg["id"], t_quant["id"], [
        {"ctype": "feat", "scope": "alg", "subject": "INT8 PTQ 量化器实现",
         "body": "实现校准数据采集与对称量化，精度损失 0.7%。\n自检：达标。",
         "files": [{"path": "alg/ptq_quantizer.py", "change_type": "add"}]},
        {"ctype": "test", "scope": "alg", "subject": "模型精度回归验证",
         "body": "ResNet50/MobileNetV2/YOLOv5s 精度回归全部通过。",
         "files": [{"path": "alg/tests/test_quant.py", "change_type": "add"}]},
    ], parent_commit=c11["short"])
    # ALG 向 RTL 发起对等通信：算子映射咨询
    comm_alg = rt.peer_request(alg["id"], rtl["id"], "inquiry", "NPU 算子映射接口咨询",
        "量化后的算子需要映射到 NPU 指令集，请确认 MAC 阵列的指令编码与 DMA 调度接口。",
        requirement_ids=[r_npu["id"]], task_ids=[t_npu["id"]], priority="medium")
    rt.respond_comm(comm_alg["id"], rtl["id"])
    # --- 3.3 驱动与固件（进行中） ---
    drv = system.get_agent_by_role("R13")
    drv["status"] = "working"
    store.save_agents(system.agents)
    r_drv = req_mgr.create(
        ids.next_req(), "外设驱动与 BSP 开发",
        "开发 MIPI-CSI、I2C、UART 驱动及 Linux BSP，支持 8 路摄像头接入。",
        "main_agent", "主 Agent 开发阶段 WBS 拆解", parent_commit=c11["short"],
        priority="high", phase="development", assigned_role="R13",
        acceptance_criteria=["8 路 MIPI-CSI 同时采集", "驱动通过 QE 测试", "BSP 可启动"],
    )
    t_drv = models.new_task(
        ids.next_task(), "MIPI-CSI 驱动开发",
        "开发 8 路 MIPI-CSI 接收驱动与 V4L2 适配层。",
        r_drv["id"], drv["id"], "development",
        priority="high", status="in_progress",
        acceptance_criteria=["8 路同时采集 1080p@30", "带宽无丢帧"],
    )
    system.add_task(t_drv)
    rt.main_assign_task(drv["id"], t_drv)
    rt.execute_task(drv["id"], t_drv["id"], [
        {"ctype": "feat", "scope": "drv", "subject": "MIPI-CSI 接收驱动实现",
         "body": "实现 D-PHY 接收与 V4L2 适配，8 路通道独立缓冲。\n自检：编译通过。",
         "files": [{"path": "drv/mipi_csi.c", "change_type": "add"}]},
    ], parent_commit=c11["short"])
    # FW 固件（进行中，有一个阻塞任务）
    fw = system.get_agent_by_role("R12")
    fw["status"] = "working"
    store.save_agents(system.agents)
    t_fw = models.new_task(
        ids.next_task(), "Bootloader 开发",
        "实现二级 Bootloader：DDR 初始化、镜像校验、跳转加载。",
        r_drv["id"], fw["id"], "development",
        priority="high", status="blocked",
        acceptance_criteria=["DDR 自检通过", "镜像校验失败可回滚"],
    )
    system.add_task(t_fw)
    # 该任务阻塞：FW 向主 Agent 升级（escalation）
    comm_esc = rt.peer_request(fw["id"], "main", "escalation", "Bootloader DDR 初始化阻塞",
        "DDR 初始化时序参数需等待 EE 确认最终硬件配置，当前任务阻塞，请协调。",
        requirement_ids=[r_drv["id"]], task_ids=[t_fw["id"]], priority="critical")
    # 主 Agent 响应并闭环升级
    rt.respond_comm(comm_esc["id"], "main")
    main_esc = rt.commit("main", "review", "escalation", "协调 DDR 时序参数",
                         body="已向 EE 下发 DDR 时序确认请求，并更新项目风险登记册。",
                         requirement_ids=[r_drv["id"]], comm_ids=[comm_esc["id"]],
                         parent_commit=c11["short"], phase="development", branch="main")
    bus.close(comm_esc["id"], "项目管理 Agent", "accepted",
              notes="已协调 EE 提供 DDR 时序参数，风险登记跟踪中", commit=main_esc["hash"])
    # --- 3.4 软件应用层（SWE 任务进行中） ---
    swe = system.get_agent_by_role("R11")
    swe["status"] = "working"
    store.save_agents(system.agents)
    r_swe = req_mgr.create(
        ids.next_req(), "边缘视觉应用框架开发",
        "开发应用层视觉管线框架：摄像头采集→AI 推理→事件上报的完整链路示例应用。",
        "main_agent", "主 Agent 开发阶段 WBS 拆解", parent_commit=c11["short"],
        priority="medium", phase="development", assigned_role="R11",
        acceptance_criteria=["示例应用跑通", "事件上报延迟<100ms", "通过 QE 测试"],
    )
    t_swe = models.new_task(
        ids.next_task(), "视觉管线框架实现",
        "实现 V4L2→NPU 推理→事件上报的流水线框架与示例应用。",
        r_swe["id"], swe["id"], "development",
        priority="medium", status="in_progress",
        acceptance_criteria=["流水线端到端跑通", "框架接口文档"],
    )
    system.add_task(t_swe)
    rt.main_assign_task(swe["id"], t_swe)
    rt.execute_task(swe["id"], t_swe["id"], [
        {"ctype": "feat", "scope": "swe", "subject": "视觉管线流水线框架",
         "body": "实现采集/推理/上报三级流水线与缓冲池管理。\n自检：单元测试通过。",
         "files": [{"path": "swe/pipeline.py", "change_type": "add"}]},
    ], parent_commit=c11["short"])
    # --- 3.5 部分待分配/待开始任务 ---
    t_pending = models.new_task(
        ids.next_task(), "PCB 布局规划（初版）",
        "完成核心板 PCB 布局规划：DDR 等长布线、电源层分割、散热过孔阵列。",
        p1["id"], system.get_agent_by_role("R04")["id"], "development",
        priority="medium", status="pending",
        acceptance_criteria=["布局 DRC 通过", "SI 预评估通过"],
    )
    system.add_task(t_pending)
    t_verif = models.new_task(
        ids.next_task(), "系统集成测试计划（SIT）",
        "制定系统级集成测试方案：端到端场景、兼容性、性能压测。",
        r_req["id"], system.get_agent_by_role("R19")["id"], "verification",
        priority="medium", status="pending",
        acceptance_criteria=["SIT 测试用例≥30 条", "覆盖 8 路输入场景"],
    )
    system.add_task(t_verif)
    # 用户直接交互示例（§6.5）
    user_comm = rt.user_message(swe["id"], "请把事件上报改为 WebSocket 推送，并补充断线重连逻辑。")

    # ------------------------------------------------------------------ #
    # 4. 风险登记与 WBS
    # ------------------------------------------------------------------ #
    from ..core.wbs import WbsBuilder
    wb = WbsBuilder(store, system.roles)
    wbs_packages = [
        # concept
        {"phase": "concept", "title": "系统需求分析", "description": "收集并确认用户需求，输出 SRS",
         "role": "R01", "deps": [], "acceptance": "SRS 评审通过", "deliverable": "SRS v1.0", "risk": ""},
        {"phase": "concept", "title": "技术可行性验证", "description": "NPU 内核与多路 MIPI 关键技术预研",
         "role": "R02", "deps": [], "acceptance": "可行性报告通过", "deliverable": "预研报告", "risk": "NPU 功耗收敛"},
        {"phase": "concept", "title": "系统概念设计", "description": "定义 SoC 概念架构与接口框架",
         "role": "R01", "deps": ["WBS-CON-01"], "acceptance": "CDCP 通过", "deliverable": "概念架构文档", "risk": ""},
        # plan
        {"phase": "plan", "title": "硬件详细方案", "description": "电源/时钟/DDR 规格定义",
         "role": "R03", "deps": ["WBS-CON-03"], "acceptance": "规格评审通过", "deliverable": "硬件规格 v1.0", "risk": "DDR 信号完整性"},
        {"phase": "plan", "title": "软件架构与选型", "description": "RTOS 选型与模块划分",
         "role": "R10", "deps": ["WBS-CON-03"], "acceptance": "架构评审通过", "deliverable": "软件架构文档", "risk": ""},
        {"phase": "plan", "title": "验证策略制定", "description": "UVM 环境与测试策略规划",
         "role": "R16", "deps": ["WBS-CON-03"], "acceptance": "验证计划通过", "deliverable": "验证计划", "risk": ""},
        # development
        {"phase": "development", "title": "AXI4-Lite 从机接口", "description": "RTL 实现与验证",
         "role": "R05", "deps": ["WBS-PLN-01"], "acceptance": "DV 验证通过", "deliverable": "RTL + 验证报告", "risk": ""},
        {"phase": "development", "title": "NPU 内核设计", "description": "MAC 阵列与指令集",
         "role": "R05", "deps": ["WBS-PLN-01"], "acceptance": "算力/功耗达标", "deliverable": "NPU RTL", "risk": "功耗超标"},
        {"phase": "development", "title": "驱动与 BSP", "description": "MIPI/I2C/UART 驱动与 BSP",
         "role": "R13", "deps": ["WBS-PLN-01"], "acceptance": "8 路采集通过", "deliverable": "驱动 + BSP", "risk": "多路带宽"},
        # verification
        {"phase": "verification", "title": "SIT 系统集成测试", "description": "端到端场景与性能压测",
         "role": "R19", "deps": ["WBS-DEV-01", "WBS-DEV-02"], "acceptance": "SIT 全部通过", "deliverable": "SIT 报告", "risk": ""},
        {"phase": "verification", "title": "可靠性试验", "description": "高低温/振动/寿命试验",
         "role": "R24", "deps": ["WBS-DEV-03"], "acceptance": "试验通过", "deliverable": "可靠性报告", "risk": "散热"},
        # release
        {"phase": "release", "title": "量产导入", "description": "试产与工艺固化",
         "role": "R21", "deps": ["WBS-VER-01"], "acceptance": "试产良率达标", "deliverable": "量产 checklist", "risk": ""},
        {"phase": "lifecycle", "title": "技术文档定稿", "description": "用户手册/数据手册",
         "role": "R25", "deps": ["WBS-VER-01"], "acceptance": "文档评审通过", "deliverable": "文档集", "risk": ""},
    ]
    wbs = wb.build(project, wbs_packages)
    # 通信归档
    store.save_communication_archive(bus.all())
    # 清理已闭环的待办动作，仅保留真正待处理的（如用户消息）
    system.runtime.pending = [p for p in system.runtime.pending
                              if not (p["action"] == "respond_comm"
                                      and bus.get(p["comm_id"])
                                      and bus.get(p["comm_id"])["status"] == "closed")]
    # 生成阶段 tag（§5.5）
    project["tags"] = ["phase/concept-complete", "phase/plan-complete", "dcp/cdcp-passed", "dcp/pdcp-passed",
                       "milestone/axi-lite-freeze", "agent/rtl/snapshot-20260904"]
    system.store.save_project(project)
    # 同步主仓库提交记录到主 Agent 的 latest_commit
    system.main_commit = rt._agent("main")["latest_commit"] if rt._agent("main") else system.main_commit
    return system
