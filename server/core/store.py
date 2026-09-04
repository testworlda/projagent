# -*- coding: utf-8 -*-
"""
store.py — 持久化存储
依据 PRD §5.1 仓库拓扑，将系统数据持久化到 data/ 目录：
  data/
  ├── project.json             # 项目配置（对应 .project-agent/project.yaml）
  ├── agents.json              # Agent 注册信息（对应 agents.yaml）
  ├── requirements.json        # 需求（对应 requirements/）
  ├── tasks.json               # 任务列表
  ├── communications/          # 通信记录归档（COMM-{id}.yaml，§6.4）
  ├── commits.json             # Commit 索引（§11.2 扩展元数据）
  └── wbs.json                 # WBS 工作分解结构
"""
import json
import os
import time

DEFAULT_DIRS = [
    "docs", "deliverables/concept", "deliverables/plan", "deliverables/development",
    "deliverables/verification", "deliverables/release", "submodules",
]

class Store:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self._now_cache = None
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(data_dir, "communications"), exist_ok=True)
        for d in DEFAULT_DIRS:
            os.makedirs(os.path.join(data_dir, d), exist_ok=True)

    # -- 时间 ----------------------------------------------------------------
    def now_iso(self):
        return time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # -- 通用 JSON 读写 -------------------------------------------------------
    def _path(self, name):
        return os.path.join(self.data_dir, name)
    def _load(self, name, default):
        p = self._path(name)
        if not os.path.exists(p):
            return default
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    def _save(self, name, obj):
        p = self._path(name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

    # -- 各实体持久化 ----------------------------------------------------------
    def load_project(self):
        return self._load("project.json", None)
    def save_project(self, project):
        self._save("project.json", project)
    def load_agents(self):
        return self._load("agents.json", [])
    def save_agents(self, agents):
        self._save("agents.json", agents)
    def load_requirements(self):
        return self._load("requirements.json", [])
    def save_requirement(self, req):
        reqs = self.load_requirements()
        reqs = [r for r in reqs if r["id"] != req["id"]]
        reqs.append(req)
        self._save("requirements.json", reqs)
    def load_tasks(self):
        return self._load("tasks.json", [])
    def save_task(self, task):
        tasks = self.load_tasks()
        tasks = [t for t in tasks if t["id"] != task["id"]]
        tasks.append(task)
        self._save("tasks.json", tasks)
    def load_communications(self):
        return self._load("communications.json", [])
    def save_communication(self, comm):
        comms = self.load_communications()
        comms = [c for c in comms if c["id"] != comm["id"]]
        comms.append(comm)
        self._save("communications.json", comms)
    def load_commits(self):
        return self._load("commits.json", [])
    def save_commit(self, commit):
        commits = self.load_commits()
        commits = [c for c in commits if c["hash"] != commit["hash"]]
        commits.append(commit)
        self._save("commits.json", commits)
    def load_wbs(self):
        return self._load("wbs.json", [])
    def save_wbs(self, wbs):
        self._save("wbs.json", wbs)
    def save_communication_archive(self, comm_records):
        """将通信记录归档到 communications/ 目录（§6.4 COMM-{id}.yaml）。"""
        from .comm import CommunicationBus
        bus = CommunicationBus(self)
        bus.load(comm_records)
        return bus.persist_archive_dir(os.path.join(self.data_dir, "communications"))
