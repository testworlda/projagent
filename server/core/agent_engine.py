# -*- coding: utf-8 -*-
"""
agent_engine.py — Agent 运行时引擎（模拟多智能体执行）
实现 PRD §4 的 Agent 体系行为：
  - 主 Agent（LPDT）：需求解析、WBS 拆解、任务分配、进度监控、广播
  - Sub-Agent：接收任务→确认→拆解子任务→执行→Commit→自检→汇报
  - 对等模式：Sub-Agent 间通过通信总线发起 request / inquiry / review 等
  - 用户直接交互：用户消息同样生成通信记录（§6.5）
本引擎采用确定性模拟驱动（无需外部 LLM），所有产出物按 §5.4 Commit 规范生成，
可通过 API 触发单步/批量推进，用于演示完整的 IPD 多 Agent 协作闭环。
实际部署时可将 execute_subtasks 替换为 LLM 调用（OpenAI 兼容接口）。
"""
import hashlib
import random
import time
from .ids import make_change_id
from .commit import format_commit
from .models import agent_ref

COMMIT_TYPES = ["feat", "fix", "docs", "refactor", "test", "chore", "review", "comm", "plan"]

def _sha(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

class AgentRuntime:
    def __init__(self, system):
        self.system = system          # ProjectSystem 实例
        self.pending = []             # 待执行动作队列（每个动作一个 dict）
        self._subtask_seq = {}

    # ------------------------------------------------------------------ #
    # 基础设施
    # ------------------------------------------------------------------ #
    def _now(self):
        return self.system.store.now_iso()
    def _next_subtask_no(self, agent_id):
        self._subtask_seq[agent_id] = self._subtask_seq.get(agent_id, 0) + 1
        return self._subtask_seq[agent_id]
    def _agent(self, agent_id):
        if agent_id == "main":
            agent_id = "agent-main"
        return self.system.get_agent(agent_id)
    def _role_ref(self, agent):
        if agent is None:
            return agent_ref("main_agent", "项目管理 Agent", "agent-main",
                             self.system.project.get("main_repo_path", "project-main"),
                             self.system.main_commit, "main")
        if agent["id"] == "agent-main":
            return agent_ref("main_agent", agent["role_name"], agent["id"],
                             agent["repo_path"], agent.get("latest_commit"), agent.get("current_branch"))
        return agent_ref("sub_agent", agent["role_name"], agent["id"],
                         agent["repo_path"], agent.get("latest_commit"), agent.get("current_branch"))
    def _main_ref(self):
        p = self.system.project
        return agent_ref("main_agent", "项目管理 Agent", "agent-main",
                         p.get("main_repo_path", "project-main"),
                         self.system.main_commit, "main")
    def _user_ref(self):
        p = self.system.project
        return agent_ref("user", "user", "user", p.get("main_repo_path", "project-main"),
                         self.system.main_commit, "main")

    # ------------------------------------------------------------------ #
    # Commit 生成
    # ------------------------------------------------------------------ #
    def commit(self, agent_id, ctype, scope, subject, body="", requirement_ids=None,
               task_ids=None, comm_ids=None, parent_commit=None, phase=None, files=None, branch=None):
        """生成一个符合 §5.4 规范的 Commit，并写入 Commit 索引。"""
        agent = self._agent(agent_id)
        if not agent:
            agent = {"id": agent_id, "role_name": "Agent", "repo_path": "project-main"}
        change_id = make_change_id(agent_id, subject, self._now())
        # hash 用可复现的方式生成
        raw = "%s|%s|%s|%s" % (agent_id, subject, self._now(), change_id)
        sha = _sha(raw)
        message = format_commit(ctype, scope, subject, body=body,
                                requirement_ids=requirement_ids, task_ids=task_ids,
                                comm_ids=comm_ids, parent_commit=parent_commit,
                                agent=agent["role_name"], phase=phase or self.system.project.get("current_phase"),
                                change_id=change_id)
        rec = {
            "hash": sha, "short": sha[:8], "repo": agent.get("repo_path"),
            "agent_id": agent_id, "type": ctype, "subject": subject, "body": body,
            "phase": phase or self.system.project.get("current_phase"),
            "requirement_ids": requirement_ids or [], "task_ids": task_ids or [],
            "comm_ids": comm_ids or [], "parent_commit": parent_commit,
            "change_id": change_id, "author": agent.get("role_name"),
            "timestamp": self._now(), "branch": branch or agent.get("current_branch", "develop"),
            "file_changes": files or [{"path": "%s/%s" % (scope, subject[:20]), "change_type": "add"}],
        }
        self.system.store.save_commit(rec)
        # 更新 Agent 最新 commit
        agent["latest_commit"] = sha
        self.system.store.save_agents(self.system.agents)
        return rec

    # ------------------------------------------------------------------ #
    # 任务执行（Sub-Agent 主流程）
    # ------------------------------------------------------------------ #
    def _find_assign_comm(self, task_id):
        """查找主 Agent 分配给该任务的 request 通信。"""
        for c in self.system.bus.filter(type="request"):
            if task_id in c["references"].get("task_ids", []) and \
                    c["from"].get("agent_type") == "main_agent":
                return c
        return None
    def execute_task(self, agent_id, task_id, subtasks, parent_commit=None):
        """
        模拟 Sub-Agent 执行任务（§4.3.1 主从模式完整闭环）：
          确认理解 → 拆解子任务 → 逐个 Commit → 自检 → 更新任务/需求状态 → 汇报
        subtasks: list of dict(ctype, scope, subject, body, files)
        """
        system = self.system
        task = system.get_task(task_id)
        if not task:
            return None
        agent = self._agent(agent_id)
        # 将主 Agent 的分配 request 流转为 accepted → in_progress
        assign_comm = self._find_assign_comm(task_id)
        if assign_comm:
            self.system.bus.transition(assign_comm["id"], "accepted", actor=agent_id)
            self.system.bus.transition(assign_comm["id"], "in_progress", actor=agent_id)
        # 任务确认：生成 comm 类型提交
        ack_comm = self.commit(
            agent_id, "comm", task["id"].lower(), "确认接收任务 %s" % task_id,
            body="任务理解确认：目标=%s\n验收标准=%s" % (task["title"], "; ".join(task.get("acceptance_criteria") or [])),
            requirement_ids=[task["requirement_id"]], task_ids=[task_id],
            parent_commit=parent_commit, phase=task["phase"],
        )
        task["status"] = "in_progress"
        system.store.save_task(task)
        # 执行各子任务
        commit_hashes = []
        last = parent_commit
        for i, st in enumerate(subtasks):
            st_rec = {
                "id": "TASK-%s-S%02d" % (task_id.split("-", 1)[-1], self._next_subtask_no(agent_id)),
                "parent_task_id": task_id,
                "title": st["subject"],
                "status": "completed",
                "commit": None,
            }
            c = self.commit(
                agent_id, st["ctype"], st.get("scope", task["id"].lower()), st["subject"],
                body=st.get("body", ""), requirement_ids=[task["requirement_id"]],
                task_ids=[task_id, st_rec["id"]], parent_commit=last,
                phase=task["phase"], files=st.get("files"),
            )
            st_rec["commit"] = c["short"]
            last = c["hash"]
            commit_hashes.append(c["hash"])
            task["commits"] = task.get("commits", []) + [c["short"]]
            system.store.save_task(task)
        # 自检通过，任务完成
        task["status"] = "completed"
        task["completed_at"] = self._now()
        system.store.save_task(task)
        # 分配 request 完成
        if assign_comm:
            self.system.bus.transition(assign_comm["id"], "completed", actor=agent_id)
        # 更新需求状态（若该需求下所有任务完成）
        req = system.get_requirement(task["requirement_id"])
        if req:
            related_tasks = [t for t in system.tasks if t.get("requirement_id") == req["id"]]
            if related_tasks and all(t["status"] == "completed" for t in related_tasks):
                system.requirements.update_status(req["id"], "completed", commit=last)
        # 汇报主 Agent（生成 response 通信）
        report_comm = system.bus.create(
            "response", "high", "任务完成汇报: %s" % task_id,
            "已完成任务 %s (%s)，共 %d 个子任务。\nCommit 列表: %s\n自检结果: 全部通过\n遗留问题: 无"
            % (task_id, task["title"], len(subtasks), ", ".join(h[:8] for h in commit_hashes)),
            self._role_ref(agent), self._main_ref(),
            references={"requirement_ids": [task["requirement_id"]], "task_ids": [task_id],
                        "related_comm_ids": [assign_comm["id"]] if assign_comm else [],
                        "files": []},
        )
        system.bus.transition(report_comm["id"], "accepted", actor=agent_id)
        system.bus.transition(report_comm["id"], "in_progress", actor=agent_id)
        system.bus.respond(report_comm["id"], "任务完成汇报已提交，详见提交记录。",
                           commit=last, status="completed")
        system.bus.close(report_comm["id"], "项目管理 Agent", "accepted",
                         notes="任务交付已验证，需求状态更新为 completed", commit=last)
        if assign_comm:
            system.bus.close(assign_comm["id"], "项目管理 Agent", "accepted",
                             notes="任务执行闭环", commit=last)
        # 同时生成一条归档提交
        self.commit(
            agent_id, "comm", "report", "汇报任务 %s 完成" % task_id,
            body="Completed: %s\nPending: 无\nSource: main_agent\nSelf-check: passed"
                 % task["title"],
            requirement_ids=[task["requirement_id"]], task_ids=[task_id],
            comm_ids=[report_comm["id"]], parent_commit=last, phase=task["phase"],
        )
        return {"task": task_id, "commits": [h[:8] for h in commit_hashes], "report_comm": report_comm["id"]}

    # ------------------------------------------------------------------ #
    # 对等通信（§4.3.2）
    # ------------------------------------------------------------------ #
    def peer_request(self, from_agent_id, to_agent_id, comm_type, subject, description,
                     requirement_ids=None, task_ids=None, priority="medium"):
        """Sub-Agent A → Sub-Agent B 发起 request/inquiry/review。"""
        a = self._agent(from_agent_id)
        b = self._agent(to_agent_id)
        rec = self.system.bus.create(
            comm_type, priority, subject, description,
            self._role_ref(a), self._role_ref(b),
            references={"requirement_ids": requirement_ids or [], "task_ids": task_ids or [],
                        "related_comm_ids": [], "files": []},
        )
        # 生成 comm 类型提交归档
        self.commit(from_agent_id, "comm", subject[:16], "发起通信 %s: %s" % (rec["id"], subject),
                    requirement_ids=requirement_ids, task_ids=task_ids, comm_ids=[rec["id"]],
                    phase=self.system.project.get("current_phase"))
        # 加入待办队列，接收方将在下一步自动响应
        self.pending.append({"action": "respond_comm", "comm_id": rec["id"],
                             "agent_id": to_agent_id})
        return rec
    def respond_comm(self, comm_id, agent_id):
        """接收方响应通信（生成 response + 交付物提交 + 闭环）。幂等：已闭环则直接返回。"""
        rec = self.system.bus.get(comm_id)
        if not rec:
            return None
        if rec["status"] == "closed":
            return rec
        agent = self._agent(agent_id)
        self.system.bus.transition(comm_id, "accepted", actor=agent_id)
        self.system.bus.transition(comm_id, "in_progress", actor=agent_id)
        # 交付提交
        deliver = self.commit(
            agent_id, "docs", rec["subject"][:16], "响应 %s 交付物" % rec["id"],
            body="针对通信 %s 的交付：%s" % (rec["id"], rec["subject"]),
            requirement_ids=rec["references"].get("requirement_ids", []),
            task_ids=rec["references"].get("task_ids", []), comm_ids=[comm_id],
            phase=self.system.project.get("current_phase"),
        )
        self.system.bus.respond(
            comm_id, "已响应并交付，详见提交 %s" % deliver["short"],
            delivered_files=[{"repo": agent["repo_path"], "path": rec["subject"], "commit": deliver["short"]}],
            commit=deliver["hash"],
        )
        # 发起方闭环确认
        self.system.bus.close(comm_id, rec["from"]["role"], "accepted",
                              notes="接收方响应已确认，需求已闭环", commit=deliver["hash"])
        return rec

    # ------------------------------------------------------------------ #
    # 用户直接交互（§6.5）
    # ------------------------------------------------------------------ #
    def user_message(self, to_agent_id, content):
        """用户向指定 Agent（主/子）发送消息，生成用户来源通信记录。"""
        to_agent = self._agent(to_agent_id) if to_agent_id != "main" else None
        to_ref = self._role_ref(to_agent) if to_agent else self._main_ref()
        rec = self.system.bus.create(
            "inquiry", "high", "用户消息", content,
            self._user_ref(), to_ref,
            references={"requirement_ids": [], "task_ids": [], "related_comm_ids": [], "files": []},
        )
        # 接收方生成一条 comm 提交归档
        if to_agent:
            self.commit(to_agent_id, "comm", "user", "接收用户消息 %s" % rec["id"],
                        body="用户消息已记录并归档，等待处理。", comm_ids=[rec["id"]],
                        phase=self.system.project.get("current_phase"))
            # 加入待办队列，供"运行演示"推进响应
            self.pending.append({"action": "respond_comm", "comm_id": rec["id"],
                                 "agent_id": to_agent_id})
        return rec

    # ------------------------------------------------------------------ #
    # 主 Agent 分配任务（§4.3.1 主从模式）
    # ------------------------------------------------------------------ #
    def main_assign_task(self, to_agent_id, task):
        """主 Agent 向 Sub-Agent 分配任务，并生成 request 通信。"""
        agent = self._agent(to_agent_id)
        rec = self.system.bus.create(
            "request", task.get("priority", "high"), "任务分配: %s" % task["id"],
            "任务标题: %s\n任务描述: %s\n验收标准: %s\n依赖: %s"
            % (task["title"], task["description"], "; ".join(task.get("acceptance_criteria") or []),
               ", ".join(task.get("dependencies") or []) or "无"),
            self._main_ref(), self._role_ref(agent),
            references={"requirement_ids": [task["requirement_id"]], "task_ids": [task["id"]],
                        "related_comm_ids": [], "files": []},
        )
        # 主 Agent 生成 plan 类型提交
        self.commit("main", "plan", "assign", "分配任务 %s 给 %s" % (task["id"], agent["role_name"]),
                    body="WBS 拆解后分配，关联需求 %s" % task["requirement_id"],
                    requirement_ids=[task["requirement_id"]], task_ids=[task["id"]],
                    comm_ids=[rec["id"]], phase=task["phase"],
                    branch="main")
        task["status"] = "pending"
        self.system.store.save_task(task)
        return rec

    # ------------------------------------------------------------------ #
    # 单步推进（返回执行的步骤描述，供 GUI "运行演示" 使用）
    # ------------------------------------------------------------------ #
    def step(self):
        if not self.pending:
            return None
        action = self.pending.pop(0)
        if action["action"] == "respond_comm":
            self.respond_comm(action["comm_id"], action["agent_id"])
            return "Agent %s 响应通信 %s" % (action["agent_id"], action["comm_id"])
        return None
