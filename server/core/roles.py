# -*- coding: utf-8 -*-
"""
roles.py — Project-Agent 系统角色注册表
依据 PRD §3.2 技术角色全景图与 §3.3 角色-阶段参与矩阵实现。
共 27 个角色：R00 主 Agent（LPDT）+ R01~R26 共 26 个 Sub-Agent。
每个角色包含：编号、名称、英文缩写、技术领域分组、核心职责、主要产出物、
以及该角色在 IPD 六阶段（concept/plan/development/verification/release/lifecycle）
的参与程度（core=核心参与 / part=部分参与·评审 / none=不参与）。
"""
IPD_PHASES = [
    "concept",
    "plan",
    "development",
    "verification",
    "release",
    "lifecycle",
]
IPD_PHASE_CN = {
    "concept": "概念阶段",
    "plan": "计划阶段",
    "development": "开发阶段",
    "verification": "验证阶段",
    "release": "发布阶段",
    "lifecycle": "生命周期",
}
# 参与度符号
PART_CORE = "core"   # ● 核心参与
PART_PART = "part"   # ◐ 部分参与/评审
PART_NONE = "none"   # ○ 不参与
ROLE_GROUPS = [
    ("project", "项目与系统层"),
    ("hardware", "硬件设计层"),
    ("software", "软件设计层"),
    ("verification", "验证与测试层"),
    ("manufacturing", "制造与质量层"),
    ("support", "技术支撑层"),
]
# 每个角色：code, name, abbr, group, responsibilities(list), deliverables(list), phase_matrix
ROLES = {
    "R00": dict(
        code="R00", name="项目管理 Agent", abbr="LPDT", group="project",
        responsibilities=[
            "项目整体规划、WBS 拆解、进度监控、风险管控、跨角色协调",
            "需求解析与角色激活（根据项目类型动态激活所需 Sub-Agent）",
            "任务分配与依赖管理（按拓扑序分配，管理关键路径）",
            "全局进度监控与风险识别升级",
            "评审决策支持（DCP/TR 评审点汇总材料）",
            "主仓库维护（submodule/产物汇总）",
        ],
        deliverables=["项目计划", "WBS", "进度报告", "风险登记册"],
        phase={p: PART_CORE for p in IPD_PHASES},
        is_main=True,
    ),
    "R01": dict(
        code="R01", name="系统工程师 Agent", abbr="SE", group="project",
        responsibilities=[
            "系统需求分析：将用户需求转化为系统级需求规格(SRS)",
            "系统架构设计：定义系统整体架构（硬件+软件+接口）",
            "需求分解：将系统需求分解到各子系统/模块并分配角色",
            "接口定义与 ICD 维护、需求追踪矩阵(RTM)维护",
            "系统集成协调与技术仲裁",
        ],
        deliverables=["系统需求规格(SRS)", "系统架构设计", "接口控制文档(ICD)", "需求追踪矩阵(RTM)"],
        phase={"concept": PART_CORE, "plan": PART_CORE, "development": PART_PART,
               "verification": PART_CORE, "release": PART_PART, "lifecycle": PART_PART},
    ),
    "R02": dict(
        code="R02", name="技术预研 Agent", abbr="TRL", group="project",
        responsibilities=[
            "新技术调研与关键技术可行性验证",
            "技术选型评估与建议",
            "高风险技术点提前攻关",
            "原型开发与技术情报输出",
        ],
        deliverables=["技术调研报告", "可行性验证报告", "原型代码/数据", "技术选型建议"],
        phase={"concept": PART_CORE, "plan": PART_PART, "development": PART_NONE,
               "verification": PART_NONE, "release": PART_NONE, "lifecycle": PART_NONE},
    ),
    "R03": dict(
        code="R03", name="硬件工程师 Agent", abbr="EE", group="hardware",
        responsibilities=[
            "硬件需求分析与电路原理图设计",
            "元器件选型（性能/成本/供货）",
            "硬件规格定义（时钟/电源/接口）",
            "硬件调试与硬件测试方案制定",
            "BOM 维护",
        ],
        deliverables=["原理图", "BOM 表", "硬件设计文档", "硬件规格说明", "硬件测试报告"],
        phase={"concept": PART_PART, "plan": PART_CORE, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_PART, "lifecycle": PART_PART},
    ),
    "R04": dict(
        code="R04", name="PCB 设计 Agent", abbr="PCB", group="hardware",
        responsibilities=[
            "PCB 布局规划与布线设计（考虑 SI/EMC/散热）",
            "信号完整性(SI)分析与电源完整性(PI)分析",
            "DFM 检查与生产文件输出（Gerber/钻孔/贴片）",
        ],
        deliverables=["PCB 工程文件", "Gerber 文件", "SI/PI 分析报告", "DFM 报告"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_PART, "lifecycle": PART_NONE},
    ),
    "R05": dict(
        code="R05", name="数字前端设计 Agent", abbr="RTL", group="hardware",
        responsibilities=[
            "RTL 编码（Verilog/SystemVerilog/Chisel 模块级设计）",
            "模块级功能仿真与 testbench 编写",
            "综合约束(SDC)与代码质量检查（Lint/CDC）",
            "低功耗设计（时钟门控/电源管理）",
            "可综合设计保证",
        ],
        deliverables=["RTL 代码", "仿真 testbench", "综合约束(SDC)", "Lint/CDC 报告", "覆盖率报告"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_NONE, "lifecycle": PART_PART},
    ),
    "R06": dict(
        code="R06", name="数字后端设计 Agent", abbr="PNR", group="hardware",
        responsibilities=[
            "布局规划(Floorplan)：面积/模块布局/电源规划",
            "布局布线(Place&Route)：时钟树综合与布线",
            "时序收敛(STA)与功耗优化",
            "物理验证（DRC/LVS/ANT）与 ECO 处理",
            "Sign-off（时序/功耗/物理验证）",
        ],
        deliverables=["网表", "DEF/GDSII", "时序报告", "功耗报告", "物理验证报告", "Sign-off 清单"],
        phase={"concept": PART_NONE, "plan": PART_NONE, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_NONE, "lifecycle": PART_NONE},
    ),
    "R07": dict(
        code="R07", name="模拟/混合信号设计 Agent", abbr="ANA", group="hardware",
        responsibilities=[
            "模拟电路设计（PLL/ADC/DAC/SerDes/PMU 等）",
            "SPICE 电路仿真与性能验证",
            "全定制模拟版图设计与寄生参数提取后仿真",
            "数模混合仿真",
        ],
        deliverables=["模拟电路原理图", "版图", "仿真报告", "设计文档"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_NONE, "lifecycle": PART_NONE},
    ),
    "R08": dict(
        code="R08", name="DFT/可测性设计 Agent", abbr="DFT", group="hardware",
        responsibilities=[
            "DFT 架构设计（扫描链/BIST/边界扫描）",
            "扫描链插入与 MBIST/LBIST 设计",
            "ATPG 向量生成与故障覆盖率分析",
            "测试成本优化（时间/数据量）",
        ],
        deliverables=["DFT 架构文档", "测试向量", "覆盖率报告", "DFT 实现代码"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_NONE, "lifecycle": PART_NONE},
    ),
    "R09": dict(
        code="R09", name="结构/机械设计 Agent", abbr="ME", group="hardware",
        responsibilities=[
            "产品结构设计（外壳/支架/散热器）与 3D 建模",
            "2D 工程图输出与散热设计（热仿真）",
            "模具设计协作与装配工艺（公差分析）",
        ],
        deliverables=["3D 模型", "2D 工程图", "结构 BOM", "热仿真报告", "装配指导书"],
        phase={"concept": PART_PART, "plan": PART_CORE, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_PART},
    ),
    "R10": dict(
        code="R10", name="软件架构师 Agent", abbr="SArch", group="software",
        responsibilities=[
            "软件架构设计（分层/模块化/设计模式）",
            "技术选型（语言/框架/中间件/库）",
            "模块划分与接口定义（API/IDL/消息协议）",
            "代码规范与构建系统制定",
            "非功能设计（性能/安全/可扩展性）",
        ],
        deliverables=["软件架构设计文档", "接口定义(API/IDL)", "技术选型报告", "代码规范"],
        phase={"concept": PART_PART, "plan": PART_CORE, "development": PART_CORE,
               "verification": PART_PART, "release": PART_NONE, "lifecycle": PART_PART},
    ),
    "R11": dict(
        code="R11", name="应用软件工程师 Agent", abbr="SWE", group="software",
        responsibilities=[
            "应用层开发（业务逻辑/UI/应用服务）",
            "RESTful/gRPC API 开发",
            "前端开发（如涉及 GUI）",
            "单元测试与代码重构、文档编写",
        ],
        deliverables=["应用代码", "单元测试", "API 文档", "构建脚本"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_CORE},
    ),
    "R12": dict(
        code="R12", name="嵌入式/固件工程师 Agent", abbr="FW", group="software",
        responsibilities=[
            "嵌入式软件开发（MCU/SoC 应用）",
            "固件开发与 Bootloader",
            "RTOS 应用/裸机开发与外设编程",
            "低功耗优化与 OTA 升级机制",
        ],
        deliverables=["固件代码", "Bootloader", "嵌入式软件文档", "刷机包/镜像"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_CORE},
    ),
    "R13": dict(
        code="R13", name="驱动工程师 Agent", abbr="DRV", group="software",
        responsibilities=[
            "设备驱动开发与 BSP 开发",
            "操作系统适配（Linux/Android/RTOS）",
            "外设驱动（SPI/I2C/UART/USB/PCIe 等）",
            "驱动调试与 IO 性能优化",
        ],
        deliverables=["驱动代码", "BSP", "驱动测试报告", "驱动 API 文档"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_CORE},
    ),
    "R14": dict(
        code="R14", name="算法工程师 Agent", abbr="ALG", group="software",
        responsibilities=[
            "核心算法设计与数学建模",
            "算法实现（C/C++/Python）与优化",
            "模型训练/调优与量化压缩（面向嵌入式）",
            "算法验证、基准测试与对比实验",
        ],
        deliverables=["算法代码", "模型文件", "算法验证报告", "性能基准数据"],
        phase={"concept": PART_PART, "plan": PART_CORE, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_PART, "lifecycle": PART_CORE},
    ),
    "R15": dict(
        code="R15", name="系统软件/OS 工程师 Agent", abbr="OS", group="software",
        responsibilities=[
            "操作系统定制（Linux 内核配置/裁剪）",
            "内核开发、文件系统与中间件",
            "构建系统（Yocto/Buildroot）配置",
            "启动流程优化",
        ],
        deliverables=["OS 镜像", "内核配置", "构建脚本", "系统软件文档"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_CORE},
    ),
    "R16": dict(
        code="R16", name="芯片验证 Agent", abbr="DV", group="verification",
        responsibilities=[
            "验证计划制定与 UVM 环境搭建",
            "功能验证（定向+随机测试）与覆盖率收敛",
            "SVA 断言检查与验证报告输出",
        ],
        deliverables=["验证环境代码", "测试用例", "覆盖率报告", "验证报告"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_NONE, "lifecycle": PART_PART},
    ),
    "R17": dict(
        code="R17", name="硬件测试 Agent", abbr="HWT", group="verification",
        responsibilities=[
            "硬件测试计划与测试用例制定",
            "硬件功能/性能/信号测试",
            "环境可靠性测试（高低温/湿度/振动）",
            "BUG 跟踪与记录",
        ],
        deliverables=["测试用例", "测试报告", "BUG 记录", "测试脚本"],
        phase={"concept": PART_NONE, "plan": PART_NONE, "development": PART_PART,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_PART},
    ),
    "R18": dict(
        code="R18", name="软件测试 Agent", abbr="QE", group="verification",
        responsibilities=[
            "软件测试计划与策略制定",
            "功能/集成/回归测试用例设计与执行",
            "自动化测试框架搭建与脚本开发",
            "BUG 管理（提交/跟踪/验证）",
        ],
        deliverables=["测试用例", "自动化脚本", "测试报告", "BUG 记录"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_CORE},
    ),
    "R19": dict(
        code="R19", name="系统集成测试 Agent", abbr="SIT", group="verification",
        responsibilities=[
            "系统级集成测试方案与端到端场景测试",
            "兼容性测试与性能压测",
            "长稳测试与系统级问题定位协调",
        ],
        deliverables=["集成测试计划", "测试用例", "SIT 报告", "问题跟踪"],
        phase={"concept": PART_NONE, "plan": PART_NONE, "development": PART_PART,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_PART},
    ),
    "R20": dict(
        code="R20", name="工艺工程师 Agent", abbr="PIE", group="manufacturing",
        responsibilities=[
            "工艺流程定义与工艺参数优化",
            "良率分析与工艺文档编写",
            "生产中的工艺问题定位与解决",
        ],
        deliverables=["工艺流程文档", "工艺参数表", "良率分析报告", "作业指导书"],
        phase={"concept": PART_NONE, "plan": PART_NONE, "development": PART_PART,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_PART},
    ),
    "R21": dict(
        code="R21", name="试产/量产导入 Agent", abbr="NPI", group="manufacturing",
        responsibilities=[
            "试产计划制定与排程",
            "试产执行与问题跟踪闭环",
            "量产导入管理与生产工艺固化",
        ],
        deliverables=["试产计划", "试产报告", "量产导入 checklist", "问题清单"],
        phase={"concept": PART_NONE, "plan": PART_NONE, "development": PART_NONE,
               "verification": PART_PART, "release": PART_CORE, "lifecycle": PART_NONE},
    ),
    "R22": dict(
        code="R22", name="DFM/可制造性设计 Agent", abbr="DFM", group="manufacturing",
        responsibilities=[
            "DFM 审查与工艺可行性评估",
            "设计改进建议与 DFM 规范制定",
            "从制造角度提出成本优化建议",
        ],
        deliverables=["DFM 审查报告", "设计改进建议", "DFM 规范"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_PART, "lifecycle": PART_NONE},
    ),
    "R23": dict(
        code="R23", name="产品质量保证 Agent", abbr="PQA", group="manufacturing",
        responsibilities=[
            "质量计划制定与流程审计",
            "质量指标监控（缺陷率/通过率/覆盖率）",
            "评审组织与质量问题跟踪",
            "质量度量报告输出",
        ],
        deliverables=["质量计划", "审计报告", "质量度量报告", "评审记录"],
        phase={p: PART_CORE for p in IPD_PHASES},
    ),
    "R24": dict(
        code="R24", name="可靠性工程师 Agent", abbr="REL", group="manufacturing",
        responsibilities=[
            "可靠性设计规范与设计指南",
            "可靠性试验（高低温/湿热/振动/冲击/寿命）",
            "失效分析与寿命评估",
            "可靠性增长（试验-分析-改进循环）",
        ],
        deliverables=["可靠性试验方案", "试验报告", "失效分析报告", "寿命评估报告"],
        phase={"concept": PART_NONE, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_PART},
    ),
    "R25": dict(
        code="R25", name="技术文档工程师 Agent", abbr="TW", group="support",
        responsibilities=[
            "技术文档编写（用户手册/数据手册/编程手册/应用笔记）",
            "API 文档与寄存器手册",
            "文档版本管理与文档质量检查",
            "多语言文档版本管理",
        ],
        deliverables=["技术文档集", "用户手册", "数据手册", "API 文档"],
        phase={"concept": PART_PART, "plan": PART_PART, "development": PART_CORE,
               "verification": PART_CORE, "release": PART_CORE, "lifecycle": PART_CORE},
    ),
    "R26": dict(
        code="R26", name="应用工程师 Agent", abbr="AE", group="support",
        responsibilities=[
            "参考设计开发（面向客户应用场景）",
            "应用笔记编写与 FAQ 维护",
            "技术支持案例库建设",
            "演示系统开发",
        ],
        deliverables=["参考设计", "应用笔记", "技术支持案例库", "FAQ"],
        phase={"concept": PART_NONE, "plan": PART_NONE, "development": PART_NONE,
               "verification": PART_PART, "release": PART_CORE, "lifecycle": PART_CORE},
    ),
}
# 依据 PRD §3.2 角色配置说明：按项目类型动态激活角色
PROJECT_TYPE_ROLES = {
    "software": ["R00", "R01", "R10", "R11", "R12", "R13", "R14", "R15", "R18", "R19", "R23", "R25"],
    "hardware": ["R00", "R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09",
                 "R16", "R17", "R20", "R21", "R22", "R23", "R24", "R25"],
    "chip": ["R00", "R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09",
             "R10", "R11", "R12", "R13", "R14", "R15", "R16", "R17", "R18", "R19",
             "R20", "R21", "R22", "R23", "R24", "R25"],
    "hybrid": list(ROLES.keys()),
    "custom": list(ROLES.keys()),
}
PROJECT_TYPE_CN = {
    "software": "纯软件项目",
    "hardware": "纯硬件/芯片项目",
    "chip": "芯片设计项目",
    "hybrid": "软硬件协同项目",
    "custom": "自定义项目",
}

def get_role(code):
    return ROLES.get(code)

def active_roles_for(project_type):
    """根据项目类型返回激活角色编号列表。"""
    return list(PROJECT_TYPE_ROLES.get(project_type, ["R00", "R01", "R11", "R18"]))

def role_abbr(code):
    r = ROLES.get(code)
    return r["abbr"] if r else code

def role_name(code):
    r = ROLES.get(code)
    return r["name"] if r else code

def all_roles_sorted():
    return [ROLES[c] for c in sorted(ROLES.keys())]
