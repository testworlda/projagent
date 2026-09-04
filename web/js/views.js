/* views.js — 各视图渲染与交互 */
const Views = {
  _cache: {},
  async _data(key, fetcher) {
    if (!this._cache[key]) this._cache[key] = fetcher();
    return this._cache[key];
  },
  invalidate() { this._cache = {}; },
  /* ============ 总览（§9.3.1） ============ */
  async dashboard() {
    const c = document.getElementById("viewContent");
    c.innerHTML = UI.loading();
    const ov = await API.overview();
    const wbs = await API.wbs();
    const commits = await API.commits();
    const comms = await API.communications();
    const p = ov.project;
    const phaseOrder = ["concept", "plan", "development", "verification", "release", "lifecycle"];
    const phaseColors = { concept: "#1677ff", plan: "#722ed1", development: "#13c2c2",
                          verification: "#faad14", release: "#52c41a", lifecycle: "#8b98b3" };
    // 阶段进度
    let phaseBlocks = "";
    let doneTotal = 0, totalAll = 0;
    phaseOrder.forEach(ph => {
      const s = ov.phases[ph] || { done: 0, total: 0, commits: 0 };
      const ratio = s.total ? s.done / s.total : (s.commits ? Math.min(1, 0.15 + s.commits * 0.05) : 0);
      doneTotal += s.done; totalAll += s.total;
      const cls = p.current_phase === ph ? "current" : (ratio >= 1 ? "done" : "");
      phaseBlocks += `<div class="phase-node ${cls}">
        <div class="pn-name">${UI.phaseCn(ph)}</div>
        <div class="pn-stat">${s.done}/${s.total} 任务 · ${s.commits} 提交</div>
      </div>`;
    });
    // 需求/任务统计
    const reqStatusHtml = Object.entries(ov.requirements)
      .filter(([k]) => ov.requirements[k] > 0)
      .map(([k, v]) => `<span class="badge ${UI.dot(k)}">${UI.statusCn(k)} ${v}</span>`).join(" ");
    const taskStatusHtml = Object.entries(ov.tasks)
      .filter(([k]) => ov.tasks[k] > 0)
      .map(([k, v]) => `<span class="badge ${UI.dot(k)}">${UI.statusCn(k)} ${v}</span>`).join(" ");
    // 近期活动（最近 12 条）
    const recent = [...commits].sort((a, b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 12);
    const recentHtml = recent.map(cm => {
      const m = UI.commitTypeMeta(cm.type);
      return `<div class="tl-item ${cm.type === "fix" ? "tl-red" : cm.type === "comm" ? "tl-orange" : cm.type === "review" ? "tl-purple" : ""}">
        <div class="tl-time">${UI.fmtTime(cm.timestamp)} · ${cm.repo}</div>
        <div><span style="color:${m.color}">${m.icon}</span>
          <b>${UI.esc(cm.subject)}</b>
          <span class="mono">${cm.short}</span>
          <span style="color:#8b98b3">by ${UI.esc(cm.author || "")}</span></div>
      </div>`;
    }).join("");
    // 活跃 Agent 表
    const agentRows = Object.values(ov.agents).map(a =>
      `<tr onclick="App.showAgentDetail('${a.role_code}')" style="cursor:pointer">
        <td>${UI.dotHtml(a.status)}<b>${UI.esc(a.role_name)}</b></td>
        <td class="mono">${a.repo}</td>
        <td>${UI.badge(a.status)}</td>
        <td class="mono">${a.latest_commit ? a.latest_commit.slice(0, 8) : "-"}</td>
        <td>${a.active_tasks}</td>
      </tr>`).join("");
    // 关键路径甘特
    const ganttHtml = Charts.gantt(wbs.length ? wbs : [{ id: "WBS-暂无", title: "无数据", phase: "concept", status: "pending" }]);
    // 风险清单
    const risks = wbs.filter(w => w.risk).map(w =>
      `<li>${UI.dotHtml("orange")} <b>${UI.esc(w.title)}</b> <span style="color:#faad14">${UI.esc(w.risk)}</span> <span class="mono">${w.id}</span></li>`).join("");
    c.innerHTML = `
      <div class="phase-timeline">${phaseBlocks}</div>
      <div class="grid grid-2">
        <div class="card">
          <div class="card-title">项目进度 <span class="hint">按 IPD 六阶段</span></div>
          <div style="display:flex;gap:20px;align-items:center;flex-wrap:wrap">
            ${Charts.ring(totalAll ? doneTotal / totalAll : 0, 120, 11, "#1677ff", "整体完成度")}
            <div>
              <div class="detail-block"><div class="db-label">需求</div><div>${reqStatusHtml || "-"}</div></div>
              <div class="detail-block"><div class="db-label">任务</div><div>${taskStatusHtml || "-"}</div></div>
              <div class="detail-block"><div class="db-label">统计</div>
                <div>需求 ${ov.counts.requirement} · 任务 ${ov.counts.task} · 通信 ${ov.counts.communication} · 提交 ${ov.counts.commit}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-title">活跃 Agent <span class="hint">${ov.counts.active_agents} 个角色</span></div>
          <div style="max-height:280px;overflow-y:auto">
            <table class="tbl">
              <thead><tr><th>角色</th><th>仓库</th><th>状态</th><th>最新提交</th><th>进行中任务</th></tr></thead>
              <tbody>${agentRows}</tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <div class="card-title">关键路径甘特图</div>
          <div style="overflow-x:auto">${ganttHtml}</div>
        </div>
        <div class="card">
          <div class="card-title">风险预警 <span class="hint">${risks ? "" : "无风险项"}</span></div>
          ${risks ? `<ul style="padding-left:18px;line-height:2">${risks}</ul>` : `<div class="empty">当前无活跃风险项</div>`}
          <div class="card-title" style="margin-top:14px">近期活动流 <span class="hint">最近 ${recent.length} 条</span></div>
          <div class="timeline">${recentHtml}</div>
        </div>
      </div>`;
  },
  /* ============ 阶段看板（§9.3.2） ============ */
  async phase() {
    const c = document.getElementById("viewContent");
    c.innerHTML = UI.loading();
    const ov = await API.overview();
    const tasks = await API.tasks();
    const p = ov.project;
    const phaseOrder = ["concept", "plan", "development", "verification", "release", "lifecycle"];
    let tl = "";
    phaseOrder.forEach(ph => {
      const s = ov.phases[ph];
      const ratio = s.total ? s.done / s.total : 0;
      tl += `<div class="phase-node ${p.current_phase === ph ? "current" : ratio >= 1 ? "done" : ""}">
        <div class="pn-name">${UI.phaseCn(ph)}</div>
        <div class="pn-stat">${s.done}/${s.total} 任务 · ${s.commits} 提交</div></div>`;
    });
    const cols = [
      ["pending", "待开始", "yellow"],
      ["in_progress", "进行中", "blue"],
      ["blocked", "已阻塞", "red"],
      ["completed", "已完成", "green"],
    ];
    const kanbanCols = cols.map(([st, label, color]) => {
      const items = tasks.filter(t => t.status === st);
      const cards = items.map(t => {
        const prio = "prio-" + (t.priority || "medium");
        const agent = App.agents.find(a => a.id === t.agent_id);
        const prog = st === "completed" ? 100 : st === "in_progress" ? 60 : st === "blocked" ? 30 : 0;
        return `<div class="task-card ${prio}" onclick="App.showTaskDetail('${t.id}')">
          <div class="tc-title">${UI.esc(t.title)}</div>
          <div class="tc-meta">
            <span class="mono">${t.id}</span>
            <span class="badge ${UI.dot(t.phase)}">${UI.phaseCn(t.phase)}</span>
            <span>${agent ? UI.esc(agent.role_name) : "-"}</span>
          </div>
          <div class="tc-meta"><span class="mono">${t.requirement_id}</span>
            <span class="badge ${t.priority === "critical" ? "red" : t.priority === "high" ? "yellow" : "gray"}">${UI.priorityCn(t.priority)}</span></div>
          <div class="progress-bar"><i style="width:${prog}%"></i></div>
        </div>`;
      }).join("");
      return `<div class="kanban-col">
        <div class="kanban-col-head">${UI.dotHtml(color)}${label} <span class="count">${items.length}</span></div>
        ${cards || `<div class="empty" style="padding:14px">暂无</div>`}
      </div>`;
    }).join("");
    c.innerHTML = `<div class="phase-timeline">${tl}</div>
      <div class="filters">
        <span style="color:#8b98b3">当前阶段: <b style="color:#1677ff">${UI.phaseFull(p.current_phase)}</b></span>
      </div>
      <div class="kanban">${kanbanCols}</div>`;
  },
  /* ============ 角色（§9.3.3） ============ */
  async role(selectedCode) {
    const c = document.getElementById("viewContent");
    c.innerHTML = UI.loading();
    const [rolesData, agents, tasks, commits] = await Promise.all([
      API.roles(), API.agents(), API.tasks(), API.commits()]);
    const groups = rolesData.groups;
    const groupOrder = [["project", "项目与系统层"], ["hardware", "硬件设计层"], ["software", "软件设计层"],
                        ["verification", "验证与测试层"], ["manufacturing", "制造与质量层"], ["support", "技术支撑层"]];
    let listHtml = "";
    groupOrder.forEach(([gkey, gname]) => {
      const items = rolesData.roles.filter(r => r.group === gkey);
      listHtml += `<div class="nav-title">${gname}</div>`;
      items.forEach(r => {
        const agent = agents.find(a => a.role_code === r.code);
        const status = agent ? agent.status : "inactive";
        const isSel = selectedCode === r.code;
        listHtml += `<div class="nav-item ${isSel ? "active" : ""}" onclick="App.showRole('${r.code}')"
          style="display:flex;justify-content:space-between">
          <span>${UI.dotHtml(status)} ${r.code} ${UI.esc(r.abbr)}</span>
          <span style="color:#5a6b86;font-size:11px">${UI.esc(r.name.replace(" Agent", ""))}</span>
        </div>`;
      });
    });
    c.innerHTML = `<div style="display:flex;gap:14px;height:calc(100vh - 220px)">
      <div style="width:230px;background:var(--bg-2);border:1px solid var(--border);border-radius:8px;padding:10px;overflow-y:auto">${listHtml}</div>
      <div style="flex:1;overflow-y:auto" id="roleDetail">${UI.loading()}</div>
    </div>`;
    if (selectedCode) this.roleDetail(selectedCode);
    else {
      const first = agents[0];
      if (first) this.roleDetail(first.role_code);
    }
  },
  async roleDetail(code) {
    const box = document.getElementById("roleDetail");
    if (!box) return;
    const [rolesData, agents, tasks, commits] = await Promise.all([
      API.roles(), API.agents(), API.tasks(), API.commits()]);
    const r = rolesData.roles.find(x => x.code === code);
    if (!r) { box.innerHTML = `<div class="empty">角色不存在</div>`; return; }
    const agent = agents.find(a => a.role_code === code);
    const myTasks = tasks.filter(t => t.agent_id === (agent ? agent.id : ""));
    const myCommits = commits.filter(c => c.agent_id === (agent ? agent.id : "agent-main"));
    const phaseRows = rolesData.ipd_phases.map(ph =>
      `<td>${r.phase[ph] === "core" ? '<span style="color:#52c41a">●</span>'
        : r.phase[ph] === "part" ? '<span style="color:#faad14">◐</span>' : '<span style="color:#3a4a66">○</span>'}</td>`).join("");
    const commitTimeline = myCommits.slice().reverse().slice(-8).map(cm =>
      `<div class="tl-item ${cm.type === "fix" ? "tl-red" : cm.type === "comm" ? "tl-orange" : ""}">
        <div class="tl-time">${UI.fmtTime(cm.timestamp)} · ${UI.commitTypeBadge(cm.type)}</div>
        <div><b>${UI.esc(cm.subject)}</b> <span class="mono">${cm.short}</span></div>
      </div>`).join("");
    const taskRows = myTasks.map(t =>
      `<tr onclick="App.showTaskDetail('${t.id}')" style="cursor:pointer">
        <td class="mono">${t.id}</td><td>${UI.esc(t.title)}</td>
        <td>${UI.phaseCn(t.phase)}</td><td>${UI.badge(t.status)}</td></tr>`).join("");
    box.innerHTML = `
      <div class="card">
        <div class="card-title"><span style="color:#1677ff">${r.code}</span> ${UI.esc(r.name)}
          <span class="badge ${agent ? UI.dot(agent.status) : "gray"}">${agent ? UI.statusCn(agent.status) : "未激活"}</span></div>
        <div class="detail-block"><div class="db-label">核心职责</div>
          <ul style="padding-left:18px;line-height:1.9">${r.responsibilities.map(x => `<li>${UI.esc(x)}</li>`).join("")}</ul></div>
        <div class="detail-block"><div class="db-label">主要产出物</div>
          <div>${r.deliverables.map(d => `<span class="badge blue">${UI.esc(d)}</span>`).join(" ")}</div></div>
        <div class="detail-block"><div class="db-label">IPD 阶段参与</div>
          <table class="tbl"><thead><tr><th></th>${rolesData.ipd_phases.map(ph => `<th>${UI.phaseCn(ph)}</th>`).join("")}</tr></thead>
          <tbody><tr><th>${r.abbr}</th>${phaseRows}</tr></tbody></table></div>
        ${agent ? `<div class="detail-block"><div class="db-label">Agent 实例</div>
          ${UI.kvTable({"实例 ID": `<span class="mono">${agent.id}</span>`,
                        "仓库": `<span class="mono">${agent.repo_path}</span>`,
                        "分支": `<span class="mono">${agent.current_branch}</span>`,
                        "最新提交": `<span class="mono">${agent.latest_commit ? agent.latest_commit.slice(0, 8) : "-"}</span>`})}</div>` : ""}
      </div>
      <div class="grid grid-2">
        <div class="card"><div class="card-title">任务列表 <span class="hint">${myTasks.length}</span></div>
          ${taskRows ? `<table class="tbl"><thead><tr><th>ID</th><th>标题</th><th>阶段</th><th>状态</th></tr></thead><tbody>${taskRows}</tbody></table>` : `<div class="empty">无任务</div>`}</div>
        <div class="card"><div class="card-title">提交时间线 <span class="hint">${myCommits.length} 条</span></div>
          ${commitTimeline ? `<div class="timeline">${commitTimeline}</div>` : `<div class="empty">无提交</div>`}</div>
      </div>`;
  },
  /* ============ 需求（§9.3.4） ============ */
  async requirement() {
    const c = document.getElementById("viewContent");
    c.innerHTML = UI.loading();
    const reqs = await API.requirements();
    const rows = reqs.slice().sort((a, b) => a.id.localeCompare(b.id)).map(r => `
      <tr onclick="App.showRequirementDetail('${r.id}')" style="cursor:pointer">
        <td class="mono">${r.id}</td>
        <td><b>${UI.esc(r.title)}</b></td>
        <td><span class="badge ${UI.dot(r.phase)}">${UI.phaseCn(r.phase)}</span></td>
        <td>${UI.badge(r.status)}</td>
        <td><span class="badge ${r.priority === "critical" ? "red" : r.priority === "high" ? "yellow" : "gray"}">${UI.priorityCn(r.priority)}</span></td>
        <td style="color:#8b98b3;font-size:11px">${UI.esc(r.source.type)} · ${UI.esc(r.source.origin)}</td>
      </tr>`).join("");
    c.innerHTML = `<div class="filters">
        <span style="color:#8b98b3">共 <b style="color:#1677ff">${reqs.length}</b> 条需求，点击行查看追溯链</span>
      </div>
      <div class="card"><table class="tbl">
        <thead><tr><th>ID</th><th>标题</th><th>阶段</th><th>状态</th><th>优先级</th><th>来源</th></tr></thead>
        <tbody>${rows}</tbody></table></div>`;
  },
  async requirementDetail(rid) {
    const chain = await API.trace(rid);
    if (!chain) { UI.showPanel(`<div class="empty">需求不存在</div>`); return; }
    const r = chain.requirement;
    // 追溯链节点（§9.3.4）
    const chainHtml = chain.nodes.map(n => {
      const colorMap = { requirement: "blue", dispatch: "purple", task: "cyan", commit: "green", finish: "orange" };
      const color = colorMap[n.type] || "gray";
      return `<div class="chain-node" onclick="App.traceNodeClick('${rid}','${n.key}','${n.type}')"
        title="${UI.esc(n.detail || "")}">
        <div class="cn-type" style="color:var(--${color})">${n.type === "requirement" ? "需求" : n.type === "dispatch" ? "分配" : n.type === "task" ? "任务" : n.type === "commit" ? "提交" : "完成"}</div>
        <div class="cn-label">${n.label}</div>
        <div style="font-size:10px;color:#5a6b86">${UI.esc((n.detail || "").slice(0, 16))}</div>
      </div>`;
    }).join("");
    const arrows = chain.nodes.map(() => `<div class="chain-arrow">→</div>`).join("");
    // 交错排列
    let chainRow = "";
    chain.nodes.forEach((n, i) => {
      chainRow += chainHtml.split("|")[i];
    });
    // 用 flex 渲染
    const chainCells = chain.nodes.map((n, i) => {
      const colorMap = { requirement: "blue", dispatch: "purple", task: "cyan", commit: "green", finish: "orange" };
      const color = colorMap[n.type] || "gray";
      const cell = `<div class="chain-node" onclick="App.traceNodeClick('${rid}','${n.key}','${n.type}')">
        <div class="cn-type" style="color:var(--${color})">${n.type === "requirement" ? "需求创建" : n.type === "dispatch" ? "需求分配" : n.type === "task" ? "任务" : n.type === "commit" ? "Commit" : "完成验证"}</div>
        <div class="cn-label" style="font-size:11px">${UI.esc((n.detail || "").slice(0, 14))}</div>
      </div>`;
      const arrow = i < chain.nodes.length - 1 ? `<div class="chain-arrow">→</div>` : "";
      return cell + arrow;
    }).join("");
    UI.showPanel(UI.panel(`${r.id} · ${r.title}`, [
      { label: "状态", html: `<span class="badge ${UI.dot(r.status)}">${UI.statusCn(r.status)}</span> <span class="badge ${UI.dot(r.phase)}">${UI.phaseFull(r.phase)}</span>` },
      { label: "描述", text: r.description },
      { label: "来源", text: `${r.source.type} · ${r.source.origin}${r.source.comm_id ? " · 通信 " + r.source.comm_id : ""}` },
      { label: "验收标准", html: `<ul style="padding-left:16px">${r.acceptance_criteria.map(x => `<li>${UI.esc(x)}</li>`).join("")}</ul>` },
      { label: "追溯链", html: `<div class="chain-wrap">${chainCells}</div>` },
    ]));
  },
  async traceNodeClick(rid, key, type) {
    const [reqs, tasks, comms, commits] = await Promise.all([
      API.requirements(), API.tasks(), API.communications(), API.commits()]);
    if (type === "requirement") return this.requirementDetail(rid);
    if (type === "task") {
      const t = tasks.find(x => "TASK:" + x.id === key);
      if (t) return this.showTaskDetail(t.id);
    }
    if (type === "commit") {
      const cm = commits.find(x => "COMMIT:" + x.short === key || x.hash === key);
      if (cm) return this.showCommitDetail(cm.hash);
    }
    if (type === "dispatch") {
      const r = reqs.find(x => x.id === rid);
      if (r && r.source.comm_id) {
        const cm = comms.find(x => x.id === r.source.comm_id);
        if (cm) return this.showCommDetail(cm.id);
      }
    }
  },
  /* ============ 通信（§9.3.5） ============ */
  async communication() {
    const c = document.getElementById("viewContent");
    c.innerHTML = UI.loading();
    const [agents, comms] = await Promise.all([API.agents(), API.communications()]);
    const sorted = comms.slice().sort((a, b) => a.id.localeCompare(b.id));
    const timelineRows = sorted.map(cm => {
      const color = UI.commTypeColor(cm.type);
      return `<div class="tl-item tl-${color === "blue" ? "" : color === "green" ? "green" : color === "red" ? "red" : color === "orange" ? "orange" : "purple"}">
        <div class="tl-time">${UI.fmtTime(cm.timestamp)} · <span class="badge ${UI.dot(cm.status)}">${UI.statusCn(cm.status)}</span></div>
        <div style="cursor:pointer" onclick="App.showCommDetail('${cm.id}')">
          <span class="badge" style="background:var(--${color})22;color:var(--${color})">${UI.commTypeCn(cm.type)}</span>
          <b>${UI.esc(cm.subject)}</b>
          <span style="color:#8b98b3;font-size:11px">${UI.esc(cm.from.role)} → ${UI.esc(cm.to.role)}</span>
          <span class="mono" style="color:#5a6b86">${cm.id}</span>
        </div>
      </div>`;
    }).join("");
    c.innerHTML = `<div class="filters">
        <select id="commTypeFilter" onchange="App.applyCommFilter()">
          <option value="">全部类型</option>
          <option value="request">request 请求</option><option value="response">response 响应</option>
          <option value="notification">notification 通知</option><option value="inquiry">inquiry 咨询</option>
          <option value="review">review 评审</option><option value="escalation">escalation 升级</option>
        </select>
        <select id="commStatusFilter" onchange="App.applyCommFilter()">
          <option value="">全部状态</option>
          <option value="pending">pending 待处理</option><option value="accepted">accepted 已接收</option>
          <option value="in_progress">in_progress 进行中</option><option value="completed">completed 已完成</option>
          <option value="blocked">blocked 阻塞</option><option value="closed">closed 已闭环</option>
        </select>
      </div>
      <div class="grid grid-2">
        <div class="card"><div class="card-title">Agent 交互拓扑 <span class="hint">边粗细=频次 · 边颜色=类型</span></div>
          <div class="legend">
            <span class="lg"><i style="width:14px;height:3px;background:#1677ff;display:inline-block"></i>request</span>
            <span class="lg"><i style="width:14px;height:3px;background:#52c41a;display:inline-block"></i>response</span>
            <span class="lg"><i style="width:14px;height:3px;background:#722ed1;display:inline-block"></i>review</span>
            <span class="lg"><i style="width:14px;height:3px;background:#ff4d4f;display:inline-block"></i>escalation</span>
          </div>
          <div class="topology-wrap" id="topologyBox">${Charts.topology(agents, comms)}</div>
        </div>
        <div class="card"><div class="card-title">通信时间线 <span class="hint">${comms.length} 条</span></div>
          <div class="timeline" id="commTimeline" style="max-height:460px;overflow-y:auto">${timelineRows}</div>
        </div>
      </div>`;
    // 拓扑节点点击 → 角色详情
    document.querySelectorAll("#topologyBox .topo-node").forEach(el => {
      el.style.cursor = "pointer";
      el.addEventListener("click", () => {
        const a = agents.find(x => x.id === el.dataset.id);
        if (a) App.showRole(a.role_code);
      });
    });
  },
  applyCommFilter() {
    const t = document.getElementById("commTypeFilter").value;
    const s = document.getElementById("commStatusFilter").value;
    document.querySelectorAll("#commTimeline .tl-item").forEach(el => {
      el.style.display = "";
      if (t && !el.dataset.type.includes(t)) el.style.display = "none";
      if (s && !el.dataset.status.includes(s)) el.style.display = "none";
    });
  },
  async showCommDetail(id) {
    const comms = await API.communications();
    const cm = comms.find(x => x.id === id);
    if (!cm) return;
    const refs = cm.references || {};
    UI.showPanel(UI.panel(`${cm.id} · ${cm.subject}`, [
      { label: "类型 / 状态 / 优先级",
        html: `${UI.badge(UI.commTypeColor(cm.type), UI.commTypeCn(cm.type))} ${UI.badge(cm.status)} <span class="badge ${cm.priority === "critical" ? "red" : "yellow"}">${UI.priorityCn(cm.priority)}</span>` },
      { label: "时间戳", text: UI.fmtTime(cm.timestamp) },
      { label: "发起方", html: UI.kvTable({
          "角色": UI.esc(cm.from.role), "类型": UI.esc(cm.from.agent_type),
          "仓库": `<span class="mono">${cm.from.repo}</span>`,
          "Commit": `<span class="mono">${(cm.from.commit || "").slice(0, 8) || "-"}</span>`,
          "分支": `<span class="mono">${cm.from.branch}</span>`}) },
      { label: "接收方", html: UI.kvTable({
          "角色": UI.esc(cm.to.role), "类型": UI.esc(cm.to.agent_type),
          "仓库": `<span class="mono">${cm.to.repo}</span>`,
          "Commit": `<span class="mono">${(cm.to.commit || "").slice(0, 8) || "-"}</span>`,
          "分支": `<span class="mono">${cm.to.branch}</span>`}) },
      { label: "通信内容", html: `<pre>${UI.esc(cm.description)}</pre>` },
      { label: "关联", html: `需求: ${refs.requirement_ids.map(x => `<span class="mono">${x}</span>`).join(" ") || "-"}<br>
        任务: ${refs.task_ids.map(x => `<span class="mono">${x}</span>`).join(" ") || "-"}<br>
        通信: ${refs.related_comm_ids.map(x => `<span class="mono">${x}</span>`).join(" ") || "-"}` },
      ...(cm.response ? [{ label: "响应", html: `<pre>${UI.esc(cm.response.summary)}</pre><div class="mono">${UI.fmtTime(cm.response.timestamp)} · commit ${(cm.response.commit || "").slice(0, 8)}</div>` }] : []),
      ...(cm.closure ? [{ label: "闭环确认", html: `确认人: ${UI.esc(cm.closure.confirmed_by)} · 结果: <b>${UI.esc(cm.closure.result)}</b><br>${UI.esc(cm.closure.notes || "")}` }] : []),
    ]));
  },
  /* ============ 提交（§9.3.6） ============ */
  async commit() {
    const c = document.getElementById("viewContent");
    c.innerHTML = UI.loading();
    const [commits, project] = await Promise.all([API.commits(), API.project()]);
    const tags = (project.tags || []).map(t => `<span class="badge purple">${UI.esc(t)}</span>`).join(" ");
    c.innerHTML = `<div class="filters">
        <select id="commitTypeFilter" onchange="App.applyCommitFilter()">
          <option value="">全部类型</option>
          ${Object.entries({ feat: "功能", fix: "修复", docs: "文档", refactor: "重构", test: "测试", chore: "配置", review: "评审", comm: "通信", plan: "计划" })
            .map(([k, v]) => `<option value="${k}">${k} ${v}</option>`).join("")}
        </select>
        <select id="commitRepoFilter" onchange="App.applyCommitFilter()">
          <option value="">全部仓库</option>
          ${[...new Set(commits.map(x => x.repo))].map(r => `<option value="${r}">${r}</option>`).join("")}
        </select>
        <span style="color:#8b98b3">共 ${commits.length} 条提交</span>
        <span style="margin-left:auto">Tags: ${tags || "-"}</span>
      </div>
      <div class="card" id="gitGraphBox"></div>`;
    this.renderGitGraph(commits);
  },
  renderGitGraph(commits) {
    const box = document.getElementById("gitGraphBox");
    if (!box) return;
    box.innerHTML = Charts.gitGraph(commits);
    box.querySelectorAll(".gg-row").forEach(row => {
      row.addEventListener("click", () => App.showCommitDetail(row.dataset.hash));
    });
  },
  applyCommitFilter() {
    const t = document.getElementById("commitTypeFilter").value;
    const r = document.getElementById("commitRepoFilter").value;
    document.querySelectorAll("#gitGraphBox .gg-row").forEach(row => {
      row.style.display = "";
      if (t && row.dataset.type !== t) row.style.display = "none";
      if (r && row.dataset.repo !== r) row.style.display = "none";
    });
  },
  async showCommitDetail(hash) {
    const commits = await API.commits();
    const cm = commits.find(x => x.hash === hash || x.short === hash);
    if (!cm) return;
    const m = UI.commitTypeMeta(cm.type);
    UI.showPanel(UI.panel(`提交 ${cm.short}`, [
      { label: "类型 / 阶段", html: `${UI.commitTypeBadge(cm.type)} <span class="badge ${UI.dot(cm.phase)}">${UI.phaseCn(cm.phase)}</span> <span class="badge">${cm.repo}</span>` },
      { label: "Commit Hash", html: `<pre>${cm.hash}\nChange-Id: ${cm.change_id || "-"}</pre>` },
      { label: "主题", html: `<div style="font-weight:600">${UI.esc(cm.subject)}</div>` },
      { label: "完整 Message", html: `<pre>${UI.esc(cm.body)}</pre>` },
      { label: "关联", html: `需求: ${cm.requirement_ids.map(x => `<span class="mono">${x}</span>`).join(" ") || "-"}<br>
        任务: ${cm.task_ids.map(x => `<span class="mono">${x}</span>`).join(" ") || "-"}<br>
        通信: ${cm.comm_ids.map(x => `<span class="mono">${x}</span>`).join(" ") || "-"}<br>
        上游提交: <span class="mono">${cm.parent_commit ? cm.parent_commit.slice(0, 8) : "-"}</span>` },
      { label: "文件变更", html: (cm.file_changes || []).map(f =>
          `<div class="mono" style="color:#52c41a">+ ${UI.esc(f.path)}</div>`).join("") || "-" },
      { label: "作者 / 时间", text: `${cm.author} · ${UI.fmtTime(cm.timestamp)}` },
    ]));
  },
  /* ============ 评审（§9.3.7） ============ */
  async review() {
    const c = document.getElementById("viewContent");
    c.innerHTML = UI.loading();
    const [project, wbs, tasks, commits] = await Promise.all([API.project(), API.wbs(), API.tasks(), API.commits()]);
    const tags = project.tags || [];
    const reviews = [
      { name: "CDCP", full: "概念决策评审点", phase: "concept", done: tags.includes("dcp/cdcp-passed") || tags.includes("phase/concept-complete"), desc: "验证技术可行性，明确系统概念，批准进入计划阶段" },
      { name: "PDCP", full: "计划决策评审点", phase: "plan", done: tags.includes("dcp/pdcp-passed") || tags.includes("phase/plan-complete"), desc: "确认详细技术方案与资源估算，批准进入开发阶段" },
      { name: "TR4", full: "开发完成评审", phase: "development", done: false, desc: "各模块开发完成，单元验证通过，进入系统集成" },
      { name: "TR5", full: "验证完成评审", phase: "verification", done: false, desc: "SIT 系统集成测试通过，可靠性验证完成" },
      { name: "GA", full: "通用可用发布", phase: "release", done: false, desc: "试产/量产准备就绪，产品正式发布" },
    ];
    const timeline = reviews.map((rv, i) => {
      const status = rv.done ? "已通过" : (i === 0 ? "进行中" : "未开始");
      const cls = rv.done ? "green" : i === 0 ? "blue" : "yellow";
      const related = wbs.filter(w => w.phase === rv.phase);
      return `<div class="tl-item tl-${cls}">
        <div class="tl-time">${rv.full} · <span class="badge ${UI.dot(cls)}">${status}</span></div>
        <div style="margin-top:4px"><b style="font-size:14px">${rv.name}</b> <span style="color:#8b98b3">${UI.esc(rv.desc)}</span></div>
        ${related.length ? `<div style="margin-top:6px;color:#8b98b3;font-size:11px">相关 WBS: ${related.map(w => `<span class="mono">${w.id}</span>`).join(" ")}</div>` : ""}
      </div>`;
    }).join("");
    // 评审材料统计
    const matStat = reviews.map(rv => {
      const relCommits = commits.filter(cm => cm.phase === rv.phase);
      const relTasks = tasks.filter(t => t.phase === rv.phase);
      return { ...rv, commits: relCommits.length, tasks: relTasks.length };
    });
    const matRows = matStat.map(rv => `<tr>
        <td><b>${rv.name}</b></td><td>${UI.phaseCn(rv.phase)}</td>
        <td>${rv.commits}</td><td>${rv.tasks}</td>
        <td>${rv.done ? UI.badge("completed", "已通过") : UI.badge("pending", "未开始")}</td></tr>`).join("");
    c.innerHTML = `<div class="grid grid-2">
      <div class="card"><div class="card-title">评审点时间线 <span class="hint">CDCP → PDCP → TR4 → TR5 → GA</span></div>
        <div class="timeline">${timeline}</div></div>
      <div class="card"><div class="card-title">评审材料统计</div>
        <table class="tbl"><thead><tr><th>评审点</th><th>阶段</th><th>提交数</th><th>任务数</th><th>状态</th></tr></thead>
        <tbody>${matRows}</tbody></table>
        <div class="card-title" style="margin-top:16px">评审 Checklist</div>
        <div class="detail-block" style="line-height:2">
          <div>${UI.dotHtml("green")} 需求可追溯性检查（每个需求关联发起方/接收方/处理提交）</div>
          <div>${UI.dotHtml("green")} Commit 规范检查（type/Refs/Change-Id 完整性）</div>
          <div>${UI.dotHtml("yellow")} 各角色交付物齐套性（SRS/架构/代码/测试/文档）</div>
          <div>${UI.dotHtml("yellow")} 通信闭环检查（request 均需 response + closure）</div>
        </div></div>
    </div>`;
  },
  /* ============ 聊天（§8.2/§8.3） ============ */
  async chat(agentId) {
    const c = document.getElementById("viewContent");
    c.innerHTML = UI.loading();
    const agents = await API.agents();
    const sessions = [ { id: "main", name: "主 Agent（LPDT）", sub: "项目级对话" },
                       ...agents.filter(a => a.role_code !== "R00").map(a => ({
                         id: a.id, name: a.role_name, sub: a.role_code + " · " + a.repo_path })) ];
    const sessionHtml = sessions.map(s =>
      `<div class="chat-session ${s.id === agentId ? "active" : ""}" onclick="App.openChat('${s.id}')">
        <div class="cs-name">${UI.esc(s.name)}</div><div class="cs-sub">${UI.esc(s.sub)}</div></div>`).join("");
    c.innerHTML = `<div class="chat-wrap">
      <div class="chat-sessions">${sessionHtml}</div>
      <div class="chat-main">
        <div class="chat-header" id="chatHeader">${UI.esc((sessions.find(s => s.id === agentId) || {}).name || "主 Agent")}</div>
        <div class="chat-msgs" id="chatMsgs"></div>
        <div class="chat-input">
          <input id="chatInput" placeholder="输入消息，将作为用户来源通信记录（绑定版本号）..." onkeydown="if(event.key==='Enter')App.sendChat()">
          <button class="btn btn-primary" onclick="App.sendChat()">发送</button>
        </div>
      </div></div>`;
    App.chatAgentId = agentId || "main";
    this.loadChatHistory(App.chatAgentId);
  },
  async loadChatHistory(agentId) {
    const box = document.getElementById("chatMsgs");
    if (!box) return;
    const comms = await API.communications();
    const relevant = comms.filter(cm => {
      const to = cm.to.agent_id === agentId || (agentId === "main" && cm.to.agent_type === "main_agent");
      const from = cm.from.agent_id === agentId || (agentId === "main" && cm.from.agent_type === "main_agent");
      return (to || from) && (cm.from.agent_type === "user" || cm.to.agent_type === "user"
        || cm.from.agent_type === "main_agent" || cm.to.agent_type === "main_agent"
        || (cm.to.agent_id === agentId && cm.type === "request"));
    }).slice(-30);
    box.innerHTML = relevant.map(cm => {
      const isUser = cm.from.agent_type === "user";
      const head = `${UI.fmtTime(cm.timestamp)} · ${cm.id} · ${UI.commTypeCn(cm.type)}`;
      if (cm.from.agent_type === "user")
        return `<div class="msg from-user"><div class="m-head">你 · ${UI.fmtTime(cm.timestamp)}</div>
          <div class="m-bubble">${UI.esc(cm.description)}</div></div>`;
      return `<div class="msg"><div class="m-head">${UI.esc(cm.from.role)} → ${UI.esc(cm.to.role)} · ${cm.id}</div>
        <div class="m-bubble"><b>${UI.esc(cm.subject)}</b>\n${UI.esc(cm.description)}</div></div>`;
    }).join("") || `<div class="empty">暂无与该 Agent 的交互记录</div>`;
    box.scrollTop = box.scrollHeight;
  },
  async sendChat() {
    const input = document.getElementById("chatInput");
    const content = input.value.trim();
    if (!content) return;
    const to = App.chatAgentId || "main";
    const res = await API.chat(to, content);
    input.value = "";
    UI.toast("消息已发送，生成通信记录 " + res.comm.id + "（绑定当前版本）");
    this.loadChatHistory(to);
  },
  /* ============ 代码浏览（§10.2.4） ============ */
  async code(repo) {
    const c = document.getElementById("viewContent");
    c.innerHTML = UI.loading();
    const [agents, project] = await Promise.all([API.agents(), API.project()]);
    const repos = [project.main_repo_path, ...agents.filter(a => a.role_code !== "R00").map(a => a.repo_path)];
    const selected = repo || repos[0];
    const tabs = repos.map(r => `<span class="repo-tab ${r === selected ? "active" : ""}" onclick="App.openCode('${r}')">${UI.esc(r)}</span>`).join("");
    c.innerHTML = `<div class="code-wrap">
      <div class="code-tree">
        <div style="padding:4px 8px;font-weight:700;color:#8b98b3;font-size:11px">仓库: ${UI.esc(selected)}</div>
        <div id="codeTreeBox">${UI.loading()}</div>
      </div>
      <div class="code-view">
        <div class="repo-select">${tabs}</div>
        <pre id="codeViewer">选择文件查看内容</pre>
      </div></div>`;
    App.codeRepo = selected;
    this.renderCodeTree(selected);
  },
  async renderCodeTree(repo) {
    const box = document.getElementById("codeTreeBox");
    if (!box) return;
    const tree = await API.repoTree(repo);
    const walk = (node, depth) => {
      const pad = "padding-left:" + (depth * 12 + 8) + "px";
      if (node.type === "dir")
        return `<div class="tree-item dir" style="${pad}" onclick="App.codeToggle(this)">▸ ${UI.esc(node.name)}</div>
          <div class="tree-children">${(node.children || []).map(ch => walk(ch, depth + 1)).join("")}</div>`;
      return `<div class="tree-item file" style="${pad}" onclick="App.openCodeFile('${repo}', '${(node.path || node.name).replace(/'/g, "\\'")}')">${UI.esc(node.name)}</div>`;
    };
    // 用 node.name 构造完整路径
    const buildPath = (node, parentPath) => {
      const p = parentPath ? parentPath + "/" + node.name : node.name;
      node.path = p;
      (node.children || []).forEach(ch => buildPath(ch, p));
    };
    buildPath(tree, "");
    box.innerHTML = (tree.children || []).map(ch => walk(ch, 0)).join("");
  },
  codeToggle(el) {
    const next = el.nextElementSibling;
    if (next && next.classList.contains("tree-children")) {
      next.style.display = next.style.display === "none" ? "" : "none";
      el.textContent = (next.style.display === "none" ? "▸ " : "▾ ") + el.textContent.slice(2);
    }
  },
  async openCodeFile(repo, path) {
    const viewer = document.getElementById("codeViewer");
    if (!viewer) return;
    const f = await API.repoFile(repo, path);
    viewer.textContent = f.content;
    document.querySelectorAll(".tree-item.file").forEach(x => x.classList.remove("selected"));
  },
  /* ============ Commit 校验（§5.4） ============ */
  async commitCheck() {
    const c = document.getElementById("viewContent");
    c.innerHTML = `<div class="card">
      <div class="card-title">Commit Message 规范校验 <span class="hint">依据 §5.4</span></div>
      <div class="detail-block"><div class="db-label">模板</div>
        <pre>&lt;type&gt;(&lt;scope&gt;): &lt;subject&gt;
&lt;body&gt;
Refs:
- Requirement: REQ-{project}-{seq}
- Task: TASK-{project}-{seq}
- Communication: COMM-{seq}
- Parent-Commit: {hash}
- Agent: {role-name}
- Phase: {ipd-phase}
Change-Id: I{generated-hash}</pre></div>
      <div class="detail-block"><div class="db-label">Commit 类型</div>
        <div style="line-height:2">${Object.entries({ feat: "新功能/新设计", fix: "BUG 修复", docs: "文档", refactor: "重构", test: "测试", chore: "配置", review: "评审响应", comm: "通信归档", plan: "计划/WBS" })
          .map(([k, v]) => `<span class="badge blue">${k} ${v}</span>`).join(" ")}</div></div>
      <div class="chat-input" style="padding:0;margin-top:8px">
        <textarea id="commitMsg" rows="8" style="flex:1;background:var(--bg-3);border:1px solid var(--border);border-radius:6px;color:var(--text);padding:10px;font-family:var(--mono);font-size:12px;outline:none"
          placeholder="粘贴待校验的 Commit Message..."></textarea>
      </div>
      <div style="margin-top:10px"><button class="btn btn-primary" onclick="App.doCommitCheck()">校验</button>
        <button class="btn btn-ghost" onclick="App.fillSampleCommit()">填入示例</button></div>
      <div id="commitCheckResult" style="margin-top:12px"></div>
    </div>`;
  },
  async doCommitCheck() {
    const msg = document.getElementById("commitMsg").value;
    const box = document.getElementById("commitCheckResult");
    const res = await API.commitCheck(msg);
    if (res.ok) {
      const p = res.parsed;
      box.innerHTML = `<div class="detail-block"><span class="badge green">✓ 校验通过</span></div>
        ${UI.kvTable({ "type": p.type, "scope": p.scope, "subject": p.subject,
                        "需求": p.requirement_ids.join(", ") || "-", "任务": p.task_ids.join(", ") || "-",
                        "通信": p.comm_ids.join(", ") || "-", "Agent": p.agent || "-",
                        "阶段": p.phase || "-", "Change-Id": p.change_id || "-" })}`;
    } else {
      box.innerHTML = `<div class="detail-block"><span class="badge red">✕ 校验未通过</span></div>
        <ul style="padding-left:18px;color:#ff4d4f">${res.errors.map(e => `<li>${UI.esc(e)}</li>`).join("")}</ul>`;
    }
  },
  fillSampleCommit() {
    const el = document.getElementById("commitMsg");
    if (el) el.value = `feat(rtl): 实现AXI4-Lite从机接口模块
完成AXI4-Lite从机接口的RTL设计，包含：
- 5个通道的完整信号处理
- 地址解码与寄存器映射
- 基础的错误响应机制
- 模块级功能仿真通过（覆盖率92%）
待完成：
- 低功耗模式支持（依赖CLK_CTRL模块，已向EE Agent提需求COMM-0038）
Refs:
- Requirement: REQ-NPU-0023
- Task: TASK-NPU-0045
- Communication: COMM-0038
- Parent-Commit: a1b2c3d
- Agent: RTL设计Agent
- Phase: development
Change-Id: I8f3a2b1c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a`;
  },
  /* ============ 任务 / Agent 详情（供全局点击） ============ */
  async showTaskDetail(id) {
    const tasks = await API.tasks();
    const t = tasks.find(x => x.id === id);
    if (!t) return;
    const agent = App.agents.find(a => a.id === t.agent_id);
    UI.showPanel(UI.panel(`${t.id} · ${t.title}`, [
      { label: "状态 / 阶段 / 优先级",
        html: `${UI.badge(t.status)} <span class="badge ${UI.dot(t.phase)}">${UI.phaseFull(t.phase)}</span> <span class="badge ${t.priority === "critical" ? "red" : t.priority === "high" ? "yellow" : "gray"}">${UI.priorityCn(t.priority)}</span>` },
      { label: "描述", text: t.description },
      { label: "负责 Agent", html: agent ? `${UI.esc(agent.role_name)} <span class="mono">${agent.id}</span>` : "-" },
      { label: "关联需求", html: `<span class="mono">${t.requirement_id}</span>` },
      { label: "验收标准", html: `<ul style="padding-left:16px">${(t.acceptance_criteria || []).map(x => `<li>${UI.esc(x)}</li>`).join("")}</ul>` },
      { label: "关联提交", html: (t.commits || []).map(h => `<span class="mono">${h}</span>`).join(" ") || "-" },
      { label: "依赖", text: (t.dependencies || []).join(", ") || "无" },
    ]));
  },
  async showAgentDetail(roleCode) {
    this.showRole(roleCode);
  },
};
