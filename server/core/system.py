# -*- coding: utf-8 -*-
"""
system.py — ProjectSystem 主类
组装 store / roles / requirements / comm / wbs / agent_engine，
对外提供统一的应用服务接口（供 API 层与种子脚本调用）。
"""
import os
from .store import Store
from . import roles as roles_mod
from .requirements import RequirementManager
from .comm import CommunicationBus
from .wbs import WbsBuilder
from .agent_engine import AgentRuntime
from .ids import IdGenerator
from . import models

class ProjectSystem:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.store = Store(data_dir)
        self.roles = roles_mod.ROLES
        self.ids = IdGenerator("PROJ")
        self.requirements = RequirementManager(self.store)
        self.bus = CommunicationBus(self.store)
        self.wbs = WbsBuilder(self.store, self.roles)
        self.runtime = AgentRuntime(self)
        self.project = self.store.load_project() or {}
        self.agents = self.store.load_agents()
        self.tasks = self.store.load_tasks()
        self.main_commit = None
        self._commits_cache = None
        # 加载既有数据
        self.requirements.load(self.store.load_requirements())
        self.bus.load(self.store.load_communications())

    # -- 项目 -------------------------------------------------------------
    def create_project(self, name, ptype, description="", activate_roles=None):
        self.project = models.new_project(
            "proj-001", name, ptype, description=description,
            current_phase="concept", status="planning",
            config={"active_roles": activate_roles or roles_mod.active_roles_for(ptype),
                    "role_group": roles_mod.PROJECT_TYPE_CN.get(ptype, ptype)},
        )
        self.ids = IdGenerator(self.project["id"].split("-")[-1].upper())
        self.store.save_project(self.project)
        # 初始化 Agent 注册表
        self._init_agents(activate_roles or roles_mod.active_roles_for(ptype))
        return self.project
    def _init_agents(self, role_codes):
        self.agents = []
        for code in role_codes:
            abbr = roles_mod.role_abbr(code)
            agent = models.new_agent(
                "agent-%s-%s" % (abbr.lower(), len(self.agents) + 1), code,
                repo_path="agent-%s" % abbr.lower(), status="idle",
                current_branch="develop",
            )
            if code == "R00":
                agent["id"] = "agent-main"
                agent["repo_path"] = self.project.get("main_repo_path", "project-main")
                agent["current_branch"] = "main"
            self.agents.append(agent)
        self.store.save_agents(self.agents)

    # -- Agent ------------------------------------------------------------
    def get_agent(self, agent_id):
        for a in self.agents:
            if a["id"] == agent_id:
                return a
        return None
    def get_agent_by_role(self, role_code):
        for a in self.agents:
            if a["role_code"] == role_code:
                return a
        return None
    def activate_agent(self, role_code):
        if self.get_agent_by_role(role_code):
            return self.get_agent_by_role(role_code)
        abbr = roles_mod.role_abbr(role_code)
        agent = models.new_agent("agent-%s-%d" % (abbr.lower(), len(self.agents) + 1),
                                 role_code, repo_path="agent-%s" % abbr.lower(),
                                 status="initializing", current_branch="develop")
        self.agents.append(agent)
        self.store.save_agents(self.agents)
        self.project.setdefault("config", {})["active_roles"] = [a["role_code"] for a in self.agents]
        self.store.save_project(self.project)
        return agent

    # -- 需求 / 任务 / 通信 / 提交 -------------------------------------------
    def get_requirement(self, req_id):
        return self.requirements.get(req_id)
    def get_task(self, task_id):
        for t in self.tasks:
            if t["id"] == task_id:
                return t
        return None
    def add_task(self, task):
        self.tasks.append(task)
        self.store.save_task(task)
        return task
    def commits(self):
        if self._commits_cache is None:
            self._commits_cache = self.store.load_commits()
        return self._commits_cache
    def refresh_commits(self):
        self._commits_cache = self.store.load_commits()
        return self._commits_cache

    # -- 统计聚合（看板数据源） ------------------------------------------------
    def overview(self):
        reqs = self.requirements.all()
        tasks = self.tasks
        comms = self.bus.all()
        commits = self.commits()
        phase_status = {p: {"done": 0, "total": 0, "commits": 0} for p in roles_mod.IPD_PHASES}
        for t in tasks:
            ph = t.get("phase", "development")
            if ph in phase_status:
                phase_status[ph]["total"] += 1
                if t["status"] in ("completed", "verified"):
                    phase_status[ph]["done"] += 1
        for c in commits:
            ph = c.get("phase")
            if ph in phase_status:
                phase_status[ph]["commits"] += 1
        req_by_status = {"pending": 0, "in_progress": 0, "completed": 0,
                         "verified": 0, "blocked": 0, "cancelled": 0}
        for r in reqs:
            req_by_status[r["status"]] = req_by_status.get(r["status"], 0) + 1
        task_by_status = {"pending": 0, "in_progress": 0, "completed": 0,
                          "verified": 0, "blocked": 0}
        for t in tasks:
            task_by_status[t["status"]] = task_by_status.get(t["status"], 0) + 1
        # Agent 活跃度
        agent_status = {}
        for a in self.agents:
            agent_status[a["id"]] = {
                "role_code": a["role_code"], "role_name": a["role_name"],
                "status": a["status"], "latest_commit": a.get("latest_commit"),
                "repo": a["repo_path"], "branch": a.get("current_branch"),
                "active_tasks": sum(1 for t in tasks if t.get("agent_id") == a["id"] and t["status"] == "in_progress"),
            }
        return {
            "project": self.project,
            "phases": phase_status,
            "requirements": req_by_status,
            "tasks": task_by_status,
            "agents": agent_status,
            "counts": {
                "requirement": len(reqs), "task": len(tasks),
                "communication": len(comms), "commit": len(commits),
                "active_agents": sum(1 for a in self.agents if a["status"] not in ("inactive",)),
            },
        }
