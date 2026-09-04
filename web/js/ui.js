/* ui.js — UI 工具：状态映射、提交类型图标、渲染辅助 */
const UI = {
  /* 状态 → 颜色点（§10.3 状态指示规范） */
  dot(status) {
    const map = {
      completed: "green", verified: "green", closed: "green", ok: "green",
      in_progress: "blue", working: "blue", inprogress: "blue", active: "blue",
      pending: "yellow", idle: "yellow", accepted: "blue", planning: "yellow",
      blocked: "red", error: "red", rejected: "red", failed: "red",
      cancelled: "gray", inactive: "gray", initializing: "gray", paused: "gray", needs_revision: "orange",
    };
    const key = String(status || "").toLowerCase();
    return map[key] || "gray";
  },
  dotHtml(status) {
    return `<span class="dot ${this.dot(status)}"></span>`;
  },
  badge(status, text) {
    const map = {
      completed: "green", verified: "green", closed: "green",
      in_progress: "blue", working: "blue", active: "blue",
      pending: "yellow", idle: "yellow", accepted: "blue",
      blocked: "red", error: "red", rejected: "red", failed: "red",
      cancelled: "gray", inactive: "gray", initializing: "gray", paused: "gray",
      inprogress: "blue", needs_revision: "orange",
    };
    const cls = map[String(status || "").toLowerCase()] || "gray";
    return `<span class="badge ${cls}">${text || status}</span>`;
  },
  /* 状态中文名 */
  statusCn(status) {
    const map = {
      completed: "已完成", verified: "已验证", closed: "已闭环", pending: "待处理",
      in_progress: "进行中", inprogress: "进行中", blocked: "已阻塞", rejected: "已拒绝",
      cancelled: "已取消", idle: "待命", working: "工作中", inactive: "未激活",
      initializing: "初始化中", error: "错误", accepted: "已接收", needs_revision: "需修改",
      active: "进行中", paused: "已暂停",
    };
    return map[String(status || "").toLowerCase()] || status;
  },
  /* 通信类型中文（§6.2） */
  commTypeCn(t) {
    return { request: "请求", response: "响应", notification: "通知",
             inquiry: "咨询", review: "评审", escalation: "升级" }[t] || t;
  },
  commTypeColor(t) {
    return { request: "blue", response: "green", notification: "gray",
             inquiry: "cyan", review: "purple", escalation: "red" }[t] || "gray";
  },
  /* Commit type 图标与颜色（§5.4） */
  commitTypeMeta(t) {
    const map = {
      feat: { icon: "✦", color: "#52c41a", cn: "功能" },
      fix: { icon: "✕", color: "#ff4d4f", cn: "修复" },
      docs: { icon: "▤", color: "#1677ff", cn: "文档" },
      refactor: { icon: "↻", color: "#13c2c2", cn: "重构" },
      test: { icon: "✓", color: "#faad14", cn: "测试" },
      chore: { icon: "⚙", color: "#8b98b3", cn: "配置" },
      review: { icon: "★", color: "#722ed1", cn: "评审" },
      comm: { icon: "⇄", color: "#13c2c2", cn: "通信" },
      plan: { icon: "◎", color: "#1677ff", cn: "计划" },
    };
    return map[t] || { icon: "•", color: "#8b98b3", cn: t };
  },
  commitTypeBadge(t) {
    const m = this.commitTypeMeta(t);
    return `<span class="badge" style="color:${m.color};background:${m.color}22">${m.icon} ${m.cn}</span>`;
  },
  priorityCn(p) {
    return { critical: "紧急", high: "高", medium: "中", low: "低" }[p] || p;
  },
  /* IPD 阶段 */
  phaseCn(p) {
    return { concept: "概念", plan: "计划", development: "开发",
             verification: "验证", release: "发布", lifecycle: "生命周期" }[p] || p;
  },
  phaseFull(p) {
    return { concept: "概念阶段", plan: "计划阶段", development: "开发阶段",
             verification: "验证阶段", release: "发布阶段", lifecycle: "生命周期阶段" }[p] || p;
  },
  timeAgo(iso) {
    if (!iso) return "";
    const t = new Date(iso);
    if (isNaN(t)) return iso;
    const diff = (Date.now() - t.getTime()) / 1000;
    if (diff < 60) return "刚刚";
    if (diff < 3600) return Math.floor(diff / 60) + " 分钟前";
    if (diff < 86400) return Math.floor(diff / 3600) + " 小时前";
    if (diff < 2592000) return Math.floor(diff / 86400) + " 天前";
    return iso.slice(0, 10);
  },
  fmtTime(iso) {
    if (!iso) return "";
    return String(iso).replace("T", " ").slice(0, 19);
  },
  esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  },
  nl2br(s) {
    return this.esc(s).replace(/\n/g, "<br>");
  },
  hl(text, query) {
    if (!query) return this.esc(text);
    const re = new RegExp("(" + query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
    return this.esc(text).replace(re, "<mark>$1</mark>");
  },
  /* 右侧详情面板 */
  showPanel(html) {
    document.getElementById("rightPanelContent").innerHTML = html;
  },
  panel(title, blocks) {
    return `<div class="detail-block"><div class="db-label" style="font-size:13px;font-weight:700;color:${titleColor(title)}">${this.esc(title)}</div></div>`
      + blocks.map(b =>
          `<div class="detail-block">
             <div class="db-label">${b.label}</div>
             <div class="db-value">${b.html || this.esc(b.text)}</div>
           </div>`).join("");
  },
  kvTable(obj) {
    return `<table class="tbl"><tbody>` + Object.entries(obj)
      .map(([k, v]) => `<tr><th style="width:90px">${k}</th><td>${v}</td></tr>`).join("") + `</tbody></table>`;
  },
  loading() {
    return `<div class="empty">加载中...</div>`;
  },
  toast(msg) {
    const el = document.createElement("div");
    el.style.cssText = "position:fixed;top:64px;right:20px;background:var(--bg-4);border:1px solid var(--blue);color:var(--text);padding:10px 16px;border-radius:8px;z-index:9999;font-size:12.5px;box-shadow:0 4px 16px rgba(0,0,0,.4);";
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2800);
  },
};
function titleColor(t) { return "#1677ff"; }
