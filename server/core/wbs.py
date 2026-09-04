# -*- coding: utf-8 -*-
"""
wbs.py — WBS 工作分解结构（§4.1.2 / §13.4）
实现主 Agent 的需求 → IPD 六阶段 WBS 拆解。
每个工作包字段：编号（WBS-{阶段缩写}-{序号}）、标题、描述、负责角色、
前置依赖、验收标准、预计产出物。支持关键路径识别与技术风险点标注。
"""
PHASE_ABBR = {
    "concept": "CON",
    "plan": "PLN",
    "development": "DEV",
    "verification": "VER",
    "release": "REL",
    "lifecycle": "LIF",
}

class WbsBuilder:
    def __init__(self, store, roles):
        self.store = store
        self.roles = roles
        self._seq = {}
    def _next(self, phase):
        abbr = PHASE_ABBR.get(phase, phase.upper()[:3])
        self._seq[phase] = self._seq.get(phase, 0) + 1
        return "WBS-%s-%02d" % (abbr, self._seq[phase])
    def build(self, project, packages):
        """packages: list of dict(phase, title, description, role, deps, acceptance, deliverable, risk)"""
        wbs = []
        for p in packages:
            wbs.append({
                "id": self._next(p["phase"]),
                "phase": p["phase"],
                "title": p["title"],
                "description": p["description"],
                "role": p.get("role"),
                "role_name": self.roles.get(p.get("role"), {}).get("name", p.get("role")),
                "deps": p.get("deps", []),
                "acceptance": p.get("acceptance", ""),
                "deliverable": p.get("deliverable", ""),
                "risk": p.get("risk", ""),
                "status": "pending",
            })
        self.store.save_wbs(wbs)
        return wbs
    def critical_path(self, wbs=None):
        """简单关键路径识别：沿依赖链深度优先求最长路径。"""
        wbs = wbs or self.store.load_wbs()
        by_id = {w["id"]: w for w in wbs}
        def depth(node_id, path):
            node = by_id.get(node_id)
            if not node:
                return 0, []
            best = 0
            best_path = []
            for d in node.get("deps", []):
                dlen, dpath = depth(d, path + [node_id])
                if dlen + 1 > best:
                    best = dlen + 1
                    best_path = dpath
            return best, best_path + [node_id]
        longest = []
        start = None
        for nid in by_id:
            dlen, dpath = depth(nid, [])
            if len(dpath) > len(longest):
                longest = dpath
                start = nid
        return [by_id[x]["id"] for x in longest]
    def risks(self, wbs=None):
        wbs = wbs or self.store.load_wbs()
        return [w for w in wbs if w.get("risk")]
