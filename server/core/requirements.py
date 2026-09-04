# -*- coding: utf-8 -*-
"""
requirements.py — 需求层级管理与追溯链（§7）
实现：
  - 需求层级：项目级 → 阶段级 → 角色级 → 任务 → 子任务 → Commit（§7.1）
  - 需求 CRUD 与状态流转（§7.2）
  - 需求-任务-通信-提交 追溯链构建（§7.3）
  - 需求来源标注（user / main_agent / sub_agent / review）
"""
import json

REQ_STATUSES = ["pending", "in_progress", "completed", "verified", "blocked", "cancelled"]
REQ_STATUS_CN = {
    "pending": "待处理", "in_progress": "进行中", "completed": "已完成",
    "verified": "已验证", "blocked": "已阻塞", "cancelled": "已取消",
}

class RequirementManager:
    def __init__(self, store):
        self.store = store
        self._reqs = {}
    def load(self, records):
        self._reqs = {}
        for r in records or []:
            self._reqs[r["id"]] = r

    # -- 创建 ----------------------------------------------------------------
    def create(self, req_id, title, description, source_type, origin,
               comm_id=None, parent_commit=None, priority="medium",
               phase="concept", assigned_role=None, status="pending",
               acceptance_criteria=None):
        rec = {
            "id": req_id,
            "title": title,
            "description": description,
            "source": {
                "type": source_type,
                "origin": origin,
                "comm_id": comm_id,
                "parent_commit": parent_commit,
            },
            "priority": priority,
            "phase": phase,
            "assigned_role": assigned_role,
            "status": status,
            "acceptance_criteria": acceptance_criteria or [],
            "dependencies": [],
            "related_requirements": [],
            "created_at": self.store.now_iso(),
            "completed_at": None,
            "completed_commit": None,
        }
        self._reqs[req_id] = rec
        self.store.save_requirement(rec)
        return rec

    # -- 查询 ----------------------------------------------------------------
    def get(self, req_id):
        return self._reqs.get(req_id)
    def all(self):
        return list(self._reqs.values())

    # -- 状态流转 -------------------------------------------------------------
    def update_status(self, req_id, new_status, commit=None):
        rec = self._reqs.get(req_id)
        if not rec:
            return None
        rec["status"] = new_status
        if new_status in ("completed", "verified", "cancelled"):
            rec["completed_at"] = self.store.now_iso()
            rec["completed_commit"] = commit or rec.get("completed_commit")
        self.store.save_requirement(rec)
        return rec

    # -- 溯源链 ---------------------------------------------------------------
    def traceability_chain(self, req_id, tasks, comms, commits):
        """构建需求追溯链：创建→分配→任务拆解→各子任务Commit→完成验证→关闭（§7.3/§9.3.4）。"""
        rec = self._reqs.get(req_id)
        if not rec:
            return None
        nodes = []
        edges = []
        # 1. 需求创建
        nodes.append({"key": "REQ:%s" % req_id, "type": "requirement", "label": "需求创建",
                      "id": req_id, "commit": rec["source"].get("parent_commit"),
                      "status": rec["status"], "detail": rec["title"]})
        # 2. 分配（来源 main_agent 时，parent_commit 即分配提交）
        if rec["source"].get("comm_id"):
            nodes.append({"key": "DISP", "type": "dispatch", "label": "需求分配",
                          "comm": rec["source"]["comm_id"],
                          "commit": rec["source"].get("parent_commit"),
                          "detail": "来源: %s" % rec["source"].get("origin", "")})
            edges.append(("REQ:%s" % req_id, "DISP"))
        # 3. 任务拆解与提交
        task_nodes = []
        prev = "DISP" if rec["source"].get("comm_id") else "REQ:%s" % req_id
        for t in tasks:
            if t.get("requirement_id") != req_id:
                continue
            tkey = "TASK:%s" % t["id"]
            task_nodes.append({"key": tkey, "type": "task", "label": "任务 %s" % t["id"],
                               "id": t["id"], "status": t["status"],
                               "detail": t["title"], "commits": list(t.get("commits", []))})
            edges.append((prev, tkey))
            prev = tkey
        nodes.extend(task_nodes)
        # 4. 关联 Commit 节点
        last = prev
        for c in commits:
            if req_id in (c.get("requirement_ids") or []):
                ckey = "COMMIT:%s" % c["short"]
                nodes.append({"key": ckey, "type": "commit", "label": "提交 %s" % c["short"],
                              "id": c["short"], "hash": c["hash"],
                              "ctype": c["type"], "detail": c["subject"],
                              "repo": c["repo"], "branch": c.get("branch", "")})
                edges.append((last, ckey))
                last = ckey
        # 5. 完成验证
        fin = {"key": "FIN", "type": "finish", "label": "完成验证/关闭",
               "status": rec["status"], "commit": rec.get("completed_commit"),
               "detail": "当前状态: %s" % REQ_STATUS_CN.get(rec["status"], rec["status"])}
        nodes.append(fin)
        edges.append((last, "FIN"))
        return {"requirement": rec, "nodes": nodes, "edges": edges}
