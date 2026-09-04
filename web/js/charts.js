/* charts.js — SVG 可视化组件（无外部依赖）
   包含：环形进度、条形图、甘特图、通信拓扑图、Git 提交图 */
const Charts = {
  NS: "http://www.w3.org/2000/svg",
  svg(w, h) {
    const s = document.createElementNS(this.NS, "svg");
    s.setAttribute("width", w);
    s.setAttribute("height", h);
    s.setAttribute("viewBox", `0 0 ${w} ${h}`);
    return s;
  },
  node(tag, attrs, parent) {
    const el = document.createElementNS(this.NS, tag);
    for (const k in attrs) el.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(el);
    return el;
  },
  /* ---- 环形进度 ---- */
  ring(value, size = 110, stroke = 10, color = "#1677ff", label = "") {
    const s = this.svg(size, size);
    const r = (size - stroke) / 2;
    const c = size / 2;
    const circ = 2 * Math.PI * r;
    this.node("circle", { cx: c, cy: c, r, fill: "none", stroke: "#1c2536", "stroke-width": stroke }, s);
    this.node("circle", {
      cx: c, cy: c, r, fill: "none", stroke: color, "stroke-width": stroke,
      "stroke-linecap": "round", "stroke-dasharray": `${circ * value}, ${circ}`,
      transform: `rotate(-90 ${c} ${c})`,
    }, s);
    const txt = this.node("text", { x: c, y: c - 4, "text-anchor": "middle", fill: "#d8e1f0", "font-size": 18, "font-weight": 700 }, s);
    txt.textContent = Math.round(value * 100) + "%";
    if (label) {
      const lt = this.node("text", { x: c, y: c + 14, "text-anchor": "middle", fill: "#8b98b3", "font-size": 9 }, s);
      lt.textContent = label;
    }
    return s.outerHTML;
  },
  /* ---- 水平条形 ---- */
  hbar(items, { h = 22, color = "#1677ff", max = null } = {}) {
    const maxV = max || Math.max(...items.map(i => i.value), 1);
    const w = 260;
    const rows = items.map((it, idx) => {
      const y = idx * (h + 10);
      const bw = Math.max(2, (it.value / maxV) * w);
      return `<g>
        <text x="0" y="${y + h - 7}" font-size="10" fill="#8b98b3">${this.esc(it.label)}</text>
        <rect x="72" y="${y + 2}" width="${w - 72}" height="${h - 4}" rx="3" fill="#1c2536"/>
        <rect x="72" y="${y + 2}" width="${bw * (1 - 72 / w) > 0 ? Math.max(2, bw - 72) : 0}" height="${h - 4}" rx="3" fill="${it.color || color}"/>
        <text x="${w + 76}" y="${y + h - 7}" font-size="10" fill="#d8e1f0">${it.value}</text>
      </g>`;
    }).join("");
    return `<svg width="${w + 100}" height="${items.length * (h + 10)}" viewBox="0 0 ${w + 100} ${items.length * (h + 10)}">${rows}</svg>`;
  },
  /* ---- 甘特图（关键路径） ---- */
  gantt(tasks, { dayW = 26, rowH = 26 } = {}) {
    const phaseColors = { concept: "#1677ff", plan: "#722ed1", development: "#13c2c2",
                          verification: "#faad14", release: "#52c41a", lifecycle: "#8b98b3" };
    const phases = ["concept", "plan", "development", "verification", "release", "lifecycle"];
    const phaseIndex = {};
    phases.forEach((p, i) => phaseIndex[p] = i);
    const total = phases.length;
    const w = total * dayW;
    const h = tasks.length * rowH + 24;
    let rows = "";
    // 表头
    let heads = "";
    phases.forEach((p, i) => {
      heads += `<rect x="${i * dayW}" y="0" width="${dayW}" height="20" fill="#151c2c" stroke="#2a3550"/>
        <text x="${i * dayW + dayW / 2}" y="14" font-size="9" text-anchor="middle" fill="#8b98b3">${UI.phaseCn(p)}</text>`;
    });
    tasks.forEach((t, idx) => {
      const y = 24 + idx * rowH;
      const pi = phaseIndex[t.phase] != null ? phaseIndex[t.phase] : 2;
      const x = pi * dayW + 2;
      const color = t.status === "completed" ? "#52c41a" : (t.status === "in_progress" ? phaseColors[t.phase] : "#3a4a66");
      rows += `<text x="0" y="${y + rowH / 2 + 3}" font-size="10" fill="#d8e1f0">${this.esc(t.id)}</text>`;
      rows += `<rect x="110" y="${y + 3}" width="${w - 110}" height="20" rx="4" fill="#1c2536"/>`;
      rows += `<rect x="${110 + x - 100}" y="${y + 3}" width="${dayW - 4}" height="20" rx="4" fill="${color}" opacity="0.85"/>`;
      rows += `<text x="${112 + x - 100}" y="${y + 17}" font-size="9" fill="#fff">${this.esc(t.title.slice(0, 8))}</text>`;
    });
    return `<svg width="${w + 140}" height="${h}" viewBox="0 0 ${w + 140} ${h}">
      <g transform="translate(100,0)">${heads}</g>${rows}</svg>`;
  },
  esc(s) { return UI.esc(s); },
  /* ---- 通信拓扑图（径向布局 + 力导向风格） ---- */
  topology(agents, comms) {
    const W = 560, H = 460;
    const cx = W / 2, cy = H / 2;
    const R = 170;
    // 主 Agent 在中心，其余按组分布
    const nodes = [];
    const main = agents.find(a => a.role_code === "R00") || { id: "main", role_name: "项目管理 Agent", role_code: "R00" };
    const others = agents.filter(a => a.role_code !== "R00");
    nodes.push({ ...main, x: cx, y: cy, r: 26, isMain: true });
    const total = others.length;
    // 各技术分组配色
    const groupColor = c => {
      const n = parseInt(String(c).slice(1), 10);
      if (n >= 1 && n <= 2) return "#13c2c2";      // 项目与系统层
      if (n >= 3 && n <= 9) return "#faad14";      // 硬件设计层
      if (n >= 10 && n <= 15) return "#52c41a";    // 软件设计层
      if (n >= 16 && n <= 19) return "#1677ff";    // 验证与测试层
      if (n >= 20 && n <= 24) return "#722ed1";    // 制造与质量层
      return "#8b98b3";                            // 技术支撑层
    };
    others.forEach((a, i) => {
      const ang = (2 * Math.PI * i) / total - Math.PI / 2;
      nodes.push({
        ...a, x: cx + R * Math.cos(ang), y: cy + R * Math.sin(ang),
        r: 17, isMain: false,
        color: groupColor(a.role_code),
      });
    });
    const byId = {};
    nodes.forEach(n => byId[n.id] = n);
    // 统计边
    const edgeMap = {};
    comms.forEach(c => {
      const f = c.from.agent_id, t = c.to.agent_id;
      if (!byId[f] || !byId[t]) return;
      const key = [f, t].sort().join("||");
      if (!edgeMap[key]) edgeMap[key] = { from: f, to: t, count: 0, types: {} };
      edgeMap[key].count++;
      edgeMap[key].types[c.type] = (edgeMap[key].types[c.type] || 0) + 1;
    });
    const typeColor = { request: "#1677ff", response: "#52c41a", notification: "#8b98b3",
                        inquiry: "#13c2c2", review: "#722ed1", escalation: "#ff4d4f" };
    let edges = "";
    Object.values(edgeMap).forEach(e => {
      const a = byId[e.from], b = byId[e.to];
      const w = Math.min(6, 2 + e.count * 1.2);
      const topType = Object.entries(e.types).sort((x, y) => y[1] - x[1])[0][0];
      const color = typeColor[topType] || "#8b98b3";
      edges += `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${color}"
        stroke-width="${w}" opacity="0.55" data-comm="${e.count}" class="topo-edge"/>`;
    });
    // 边方向箭头由发起方决定：简化用半透明线条
    let circles = "";
    nodes.forEach(n => {
      circles += `<circle cx="${n.x}" cy="${n.y}" r="${n.r}" fill="${n.isMain ? "#1677ff" : (n.color || "#2a3550")}"
        stroke="#0f1420" stroke-width="2" class="topo-node" data-id="${n.id}"/>`;
      circles += `<text x="${n.x}" y="${n.y + 3}" text-anchor="middle" font-size="${n.isMain ? 9 : 7.5}" fill="#fff" font-weight="700">${n.isMain ? "LPDT" : n.role_code}</text>`;
      const ty = n.isMain ? n.y + n.r + 13 : n.y - n.r - 7;
      circles += `<text x="${n.x}" y="${ty}" text-anchor="middle" font-size="8.5" fill="#8b98b3">${this.esc(n.role_name)}</text>`;
    });
    return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${edges}${circles}</svg>`;
  },
  /* ---- Git 提交图（跨仓库合并视图，按仓库分 lane） ---- */
  gitGraph(commits) {
    const repos = [...new Set(commits.map(c => c.repo))];
    const laneColor = ["#1677ff", "#52c41a", "#faad14", "#ff4d4f", "#722ed1", "#13c2c2", "#8b98b3"];
    const repoLane = {};
    repos.forEach((r, i) => repoLane[r] = i);
    const laneW = 34;
    const rows = commits.slice().reverse().map(c => {
      const lane = repoLane[c.repo];
      const x = lane * laneW + laneW / 2;
      const m = UI.commitTypeMeta(c.type);
      return `<div class="gg-row" data-hash="${c.hash}">
        <div class="gg-lanes">
          <span class="gg-node" style="left:${x - 5}px;background:${laneColor[lane % laneColor.length]}"></span>
          <span style="position:absolute;left:${x + 8}px;top:12px;font-size:9px;color:#5a6b86;width:${laneW * (repos.length - lane)}px">${this.esc(c.repo.replace("agent-", ""))}</span>
        </div>
        <div class="gg-commit">
          <span class="mono" style="color:${laneColor[lane % laneColor.length]}">${this.esc(c.short || (c.hash || "").slice(0, 8))}</span>
          ${UI.commitTypeBadge(c.type)}
          <span style="font-weight:600">${this.esc(c.subject)}</span>
          <span style="margin-left:auto;color:#8b98b3;font-size:11px">${this.esc(c.author || c.agent_id)}</span>
          <span class="mono" style="color:#5a6b86">${UI.timeAgo(c.timestamp)}</span>
        </div>
      </div>`;
    }).join("");
    return `<div class="git-graph">${rows}</div>`;
  },
};
