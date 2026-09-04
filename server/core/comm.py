# -*- coding: utf-8 -*-
"""
comm.py — Agent 间通信协议与状态机
依据 PRD §6 实现：
  - 通信类型（§6.2）：request / response / notification / inquiry / review / escalation
  - 状态机（§6.3）：pending → accepted / rejected / blocked → in_progress → completed → closed
  - 通信记录持久化为 COMM-{id}.yaml（§6.4），同时入内存索引
  - 用户与 Sub-Agent 直接交互同样生成通信记录（§6.5）
"""
import json
import os
import re
from .ids import make_change_id

COMM_TYPES = ["request", "response", "notification", "inquiry", "review", "escalation"]
COMM_STATUSES = ["pending", "accepted", "rejected", "in_progress", "completed", "blocked", "closed"]

# 允许的状态迁移（§6.3 状态机）
TRANSITIONS = {
    "pending": ["accepted", "rejected", "blocked"],
    "accepted": ["in_progress", "rejected", "blocked"],
    "in_progress": ["completed", "blocked"],
    "completed": ["closed"],
    "blocked": ["in_progress", "closed", "rejected"],
    "rejected": ["closed", "in_progress"],
    "closed": [],
}

class CommError(Exception):
    pass

class CommunicationBus:
    """通信总线：管理通信记录创建、状态流转、持久化。"""
    def __init__(self, store):
        self.store = store
        self._records = {}      # comm_id -> record dict
        self._counter = 0

    # -- 初始化 / 加载 -------------------------------------------------------
    def load(self, records):
        self._records = {}
        self._counter = 0
        for r in records or []:
            self._records[r["id"]] = r
            m = re.match(r"^COMM-(\d+)$", r["id"])
            if m:
                self._counter = max(self._counter, int(m.group(1)))
    def _next_id(self):
        self._counter += 1
        return "COMM-%04d" % self._counter

    # -- 创建 ----------------------------------------------------------------
    def create(self, comm_type, priority, subject, description,
               from_info, to_info, references=None):
        if comm_type not in COMM_TYPES:
            raise CommError("未知通信类型: %s" % comm_type)
        if priority not in ("critical", "high", "medium", "low"):
            priority = "medium"
        rec = {
            "id": self._next_id(),
            "timestamp": self.store.now_iso(),
            "type": comm_type,
            "priority": priority,
            "status": "pending",
            "from": from_info,
            "to": to_info,
            "subject": subject,
            "description": description,
            "references": references or {
                "requirement_ids": [], "task_ids": [], "related_comm_ids": [], "files": []
            },
            "response": None,
            "closure": None,
        }
        self._records[rec["id"]] = rec
        self.store.save_communication(rec)
        return rec

    # -- 查询 ----------------------------------------------------------------
    def get(self, comm_id):
        return self._records.get(comm_id)
    def all(self):
        return list(self._records.values())
    def filter(self, **kwargs):
        out = []
        for r in self.all():
            ok = True
            for k, v in kwargs.items():
                if k == "from_role":
                    if r["from"].get("role") != v:
                        ok = False
                elif k == "to_role":
                    if r["to"].get("role") != v:
                        ok = False
                elif k == "status":
                    if r["status"] != v:
                        ok = False
                elif k == "type":
                    if r["type"] != v:
                        ok = False
                else:
                    if r.get(k) != v:
                        ok = False
            if ok:
                out.append(r)
        return out

    # -- 状态机 ---------------------------------------------------------------
    def transition(self, comm_id, new_status, actor=None, note=None):
        rec = self._records.get(comm_id)
        if not rec:
            raise CommError("通信记录不存在: %s" % comm_id)
        old = rec["status"]
        if old == new_status:
            return rec
        allowed = TRANSITIONS.get(old, [])
        if new_status not in allowed:
            raise CommError("非法状态迁移 %s -> %s (允许: %s)" % (old, new_status, allowed))
        rec["status"] = new_status
        self.store.save_communication(rec)
        return rec

    # -- 响应 / 闭环 ----------------------------------------------------------
    def respond(self, comm_id, summary, delivered_files=None, commit=None, status="completed"):
        """接收方对 request 的响应（§6.1 response 字段）。"""
        rec = self._records.get(comm_id)
        if not rec:
            raise CommError("通信记录不存在: %s" % comm_id)
        rec["response"] = {
            "timestamp": self.store.now_iso(),
            "commit": commit,
            "summary": summary,
            "delivered_files": delivered_files or [],
        }
        if status in TRANSITIONS.get(rec["status"], []):
            rec["status"] = status
        self.store.save_communication(rec)
        return rec

    def close(self, comm_id, confirmed_by, result, notes="", commit=None):
        """发起方确认并闭环（§6.1 closure 字段）。"""
        rec = self._records.get(comm_id)
        if not rec:
            raise CommError("通信记录不存在: %s" % comm_id)
        rec["closure"] = {
            "confirmed_by": confirmed_by,
            "timestamp": self.store.now_iso(),
            "commit": commit,
            "result": result,     # accepted / rejected / needs_revision
            "notes": notes,
        }
        if rec["status"] in ("completed", "blocked", "rejected"):
            rec["status"] = "closed"
        self.store.save_communication(rec)
        return rec

    # -- 持久化导出 -----------------------------------------------------------
    def to_yaml(self, rec):
        """输出类 YAML 的归档文本（§6.4 以 COMM-{id}.yaml 归档）。"""
        lines = ["communication:", "  id: %s" % rec["id"],
                 "  timestamp: %s" % rec["timestamp"],
                 "  type: %s" % rec["type"],
                 "  priority: %s" % rec["priority"],
                 "  status: %s" % rec["status"],
                 "  from:",
                 "    agent_type: %s" % rec["from"].get("agent_type"),
                 "    role: %s" % rec["from"].get("role"),
                 "    agent_id: %s" % rec["from"].get("agent_id"),
                 "    repo: %s" % rec["from"].get("repo"),
                 "    commit: %s" % (rec["from"].get("commit") or ""),
                 "    branch: %s" % rec["from"].get("branch"),
                 "  to:",
                 "    agent_type: %s" % rec["to"].get("agent_type"),
                 "    role: %s" % rec["to"].get("role"),
                 "    agent_id: %s" % rec["to"].get("agent_id"),
                 "    repo: %s" % rec["to"].get("repo"),
                 "    commit: %s" % (rec["to"].get("commit") or ""),
                 "    branch: %s" % rec["to"].get("branch"),
                 "  subject: %s" % rec["subject"],
                 "  description: |",
                 ]
        for line in (rec["description"] or "").splitlines():
            lines.append("    " + line)
        lines.append("  references:")
        refs = rec["references"]
        lines.append("    requirement_ids: %s" % json.dumps(refs.get("requirement_ids", []), ensure_ascii=False))
        lines.append("    task_ids: %s" % json.dumps(refs.get("task_ids", []), ensure_ascii=False))
        lines.append("    related_comm_ids: %s" % json.dumps(refs.get("related_comm_ids", []), ensure_ascii=False))
        if rec["response"]:
            lines.append("  response:")
            lines.append("    timestamp: %s" % rec["response"]["timestamp"])
            lines.append("    commit: %s" % (rec["response"].get("commit") or ""))
            lines.append("    summary: |")
            for line in (rec["response"]["summary"] or "").splitlines():
                lines.append("      " + line)
        if rec["closure"]:
            lines.append("  closure:")
            lines.append("    confirmed_by: %s" % rec["closure"]["confirmed_by"])
            lines.append("    timestamp: %s" % rec["closure"]["timestamp"])
            lines.append("    result: %s" % rec["closure"]["result"])
            lines.append("    notes: %s" % (rec["closure"].get("notes") or ""))
        return "\n".join(lines)

    def persist_archive_dir(self, directory):
        """将全部通信记录归档为 COMM-{id}.yaml 文件（§6.4）。"""
        os.makedirs(directory, exist_ok=True)
        for rec in self.all():
            path = os.path.join(directory, "%s.yaml" % rec["id"])
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.to_yaml(rec))
        return len(self.all())
