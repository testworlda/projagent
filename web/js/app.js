/* app.js — 应用引导、路由与全局交互 */
const App = {
  currentView: "dashboard",
  agents: [],
  rolesData: null,
  chatAgentId: "main",
  codeRepo: null,
  _loaded: false,
  async init() {
    document.querySelectorAll(".nav-item").forEach(el => {
      el.addEventListener("click", () => {
        if (location.hash !== "#" + el.dataset.view) {
          location.hash = el.dataset.view;   // 触发 hashchange → switchView
        } else {
          this.switchView(el.dataset.view);
        }
      });
    });
    document.getElementById("btnRunStep").addEventListener("click", () => this.runStep());
    document.getElementById("btnReset").addEventListener("click", () => this.resetDemo());
    document.getElementById("globalSearch").addEventListener("keydown", e => {
      if (e.key === "Enter") this.globalSearch(e.target.value.trim());
    });
    // 预加载角色与 Agent
    try {
      const [rolesData, agents, project] = await Promise.all([API.roles(), API.agents(), API.project()]);
      this.rolesData = rolesData;
      this.agents = agents;
      this.updateTopbar(project);
    } catch (e) {
      UI.toast("后端连接失败: " + e.message);
    }
    // URL hash 路由：支持 #view 直达，如 #review / #chat / #commitcheck
    window.addEventListener("hashchange", () => this.routeHash());
    const target = (location.hash || "#dashboard").replace("#", "");
    this.switchView(this._validView(target) ? target : "dashboard");
    setInterval(() => this.refreshStatusBar(), 15000);
    this._loaded = true;
  },
  _validView(v) {
    return ["dashboard", "phase", "role", "requirement", "communication",
            "commit", "review", "chat", "code", "commitcheck"].includes(v);
  },
  routeHash() {
    const h = location.hash.replace("#", "");
    if (this._validView(h)) {
      this.switchView(h);
    }
  },
  updateTopbar(project) {
    document.querySelector(".project-name").textContent = project.name || "-";
    const badge = document.getElementById("phaseBadge");
    badge.textContent = UI.phaseFull(project.current_phase);
  },
  async refreshStatusBar() {
    try {
      const [ov, commits] = await Promise.all([API.overview(), API.commits()]);
      document.getElementById("sbAgents").textContent = ov.counts.active_agents;
      document.getElementById("sbComms").textContent = ov.counts.communication;
      const last = commits.slice().sort((a, b) => b.timestamp.localeCompare(a.timestamp))[0];
      document.getElementById("sbCommit").textContent = last ? last.short : "-";
    } catch (e) { /* ignore */ }
  },
  /* ---- 视图切换 ---- */
  switchView(view) {
    this.currentView = view;
    document.querySelectorAll(".nav-item").forEach(el =>
      el.classList.toggle("active", el.dataset.view === view));
    const titles = {
      dashboard: ["项目总览", "按 IPD 阶段聚合的项目全局状态"],
      phase: ["阶段看板", "IPD 六阶段 × Kanban 任务看板"],
      role: ["角色视图", "27 个技术角色的状态、任务与提交"],
      requirement: ["需求视图", "需求全生命周期与追溯链"],
      communication: ["通信视图", "Agent 交互拓扑与通信时间线"],
      commit: ["提交视图", "以 Git Commit 为节点的项目演化视图"],
      review: ["评审视图", "CDCP / PDCP / TR4 / TR5 / GA 评审点"],
      chat: ["聊天", "与主 Agent 或任意 Sub-Agent 直接交互"],
      code: ["代码浏览", "多仓库文件浏览与内容查看"],
      commitcheck: ["Commit 校验", "Commit Message 规范校验（§5.4）"],
    };
    const [t, sub] = titles[view] || [view, ""];
    const titleEl = document.getElementById("viewTitle");
    titleEl.innerHTML = `${t} <span class="sub">${sub}</span>`;
    const c = document.getElementById("viewContent");
    c.scrollTop = 0;
    switch (view) {
      case "dashboard": Views.dashboard(); break;
      case "phase": Views.phase(); break;
      case "role": Views.role(); break;
      case "requirement": Views.requirement(); break;
      case "communication": Views.communication(); break;
      case "commit": Views.commit(); break;
      case "review": Views.review(); break;
      case "chat": Views.chat(); break;
      case "code": Views.code(); break;
      case "commitcheck": Views.commitCheck(); break;
    }
  },
  /* ---- 角色 / 详情跳转 ---- */
  showRole(code) { Views.role(code); },
  showTaskDetail(id) { Views.showTaskDetail(id); },
  showAgentDetail(code) { Views.showAgentDetail(code); },
  showCommDetail(id) { Views.showCommDetail(id); },
  showCommitDetail(hash) { Views.showCommitDetail(hash); },
  showRequirementDetail(rid) { Views.requirementDetail(rid); },
  traceNodeClick(rid, key, type) { Views.traceNodeClick(rid, key, type); },
  applyCommFilter() { Views.applyCommFilter(); },
  applyCommitFilter() { Views.applyCommitFilter(); },
  doCommitCheck() { Views.doCommitCheck(); },
  fillSampleCommit() { Views.fillSampleCommit(); },
  codeToggle(el) { Views.codeToggle(el); },
  openCodeFile(repo, path) { Views.openCodeFile(repo, path); },
  openChat(id) { Views.chat(id); },
  openCode(repo) { Views.code(repo); },
  sendChat() { Views.sendChat(); },
  /* ---- 运行演示（单步推进 Agent 交互） ---- */
  async runStep() {
    const btn = document.getElementById("btnRunStep");
    btn.disabled = true;
    try {
      const res = await API.runStep();
      if (res.done) UI.toast("演示推进完成：" + res.message);
      else UI.toast(res.message);
      Views.invalidate();
      this.refreshStatusBar();
      this.switchView(this.currentView);
    } catch (e) {
      UI.toast("运行失败: " + e.message);
    } finally {
      btn.disabled = false;
    }
  },
  async resetDemo() {
    if (!confirm("确定重置演示数据？所有当前数据将被重建。")) return;
    const res = await API.reset();
    UI.toast("演示数据已重置");
    location.reload();
  },
  /* ---- 全局搜索 ---- */
  async globalSearch(q) {
    if (!q) return;
    const [reqs, tasks, comms, commits] = await Promise.all([
      API.requirements(), API.tasks(), API.communications(), API.commits()]);
    const hitReqs = reqs.filter(r => (r.id + r.title + r.description).toLowerCase().includes(q.toLowerCase()));
    const hitTasks = tasks.filter(t => (t.id + t.title + t.description).toLowerCase().includes(q.toLowerCase()));
    const hitComms = comms.filter(c => (c.id + c.subject + c.description).toLowerCase().includes(q.toLowerCase()));
    const hitCommits = commits.filter(c => (c.hash + c.subject + c.body).toLowerCase().includes(q.toLowerCase()));
    const html = `
      <div class="card"><div class="card-title">搜索结果: "${UI.esc(q)}"</div></div>
      ${hitReqs.length ? `<div class="card"><div class="card-title">需求 (${hitReqs.length})</div>${hitReqs.slice(0, 10).map(r =>
        `<div style="padding:6px 0;cursor:pointer" onclick="App.showRequirementDetail('${r.id}')"><span class="mono">${r.id}</span> ${UI.hl(r.title, q)} <span class="badge ${UI.dot(r.status)}">${UI.statusCn(r.status)}</span></div>`).join("")}</div>` : ""}
      ${hitTasks.length ? `<div class="card"><div class="card-title">任务 (${hitTasks.length})</div>${hitTasks.slice(0, 10).map(t =>
        `<div style="padding:6px 0;cursor:pointer" onclick="App.showTaskDetail('${t.id}')"><span class="mono">${t.id}</span> ${UI.hl(t.title, q)} <span class="badge ${UI.dot(t.status)}">${UI.statusCn(t.status)}</span></div>`).join("")}</div>` : ""}
      ${hitComms.length ? `<div class="card"><div class="card-title">通信 (${hitComms.length})</div>${hitComms.slice(0, 10).map(cm =>
        `<div style="padding:6px 0;cursor:pointer" onclick="App.showCommDetail('${cm.id}')"><span class="mono">${cm.id}</span> ${UI.hl(cm.subject, q)} <span style="color:#8b98b3">${UI.esc(cm.from.role)}→${UI.esc(cm.to.role)}</span></div>`).join("")}</div>` : ""}
      ${hitCommits.length ? `<div class="card"><div class="card-title">提交 (${hitCommits.length})</div>${hitCommits.slice(0, 10).map(cm =>
        `<div style="padding:6px 0;cursor:pointer" onclick="App.showCommitDetail('${cm.hash}')"><span class="mono">${cm.short}</span> ${UI.hl(cm.subject, q)} ${UI.commitTypeBadge(cm.type)}</div>`).join("")}</div>` : ""}
      ${!hitReqs.length && !hitTasks.length && !hitComms.length && !hitCommits.length ? `<div class="empty">无匹配结果</div>` : ""}`;
    document.getElementById("viewContent").innerHTML = html;
  },
};
document.addEventListener("DOMContentLoaded", () => App.init());
