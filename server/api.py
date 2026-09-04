# -*- coding: utf-8 -*-
"""
api.py — REST API 层（基于 Python 标准库 http.server，无第三方依赖）
提供看板/聊天/代码浏览等 GUI 所需的数据接口，并暴露 Agent 运行时
（单步推进演示、用户消息、任务分配）等操作接口。
"""
import json
import re
import urllib.parse
from .core import roles as roles_mod
from .core import models
from .core.commit import COMMIT_TYPES, COMMIT_TYPE_CN, format_commit, parse_commit, validate_commit

def json_response(handler, obj, status=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)

class ApiRouter:
    def __init__(self, system):
        self.system = system

    # ------------------------------------------------------------------ #
    # 路由
    # ------------------------------------------------------------------ #
    def handle(self, handler, method, path, query, body_bytes):
        sys_ = self.system
        m = None
        try:
            if method == "GET" and path == "/api/overview":
                return json_response(handler, sys_.overview())
            if method == "GET" and path == "/api/project":
                return json_response(handler, sys_.project)
            if method == "GET" and path == "/api/roles":
                return json_response(handler, self._roles_payload())
            if method == "GET" and path == "/api/agents":
                return json_response(handler, sys_.agents)
            if method == "GET" and path == "/api/requirements":
                return json_response(handler, sys_.requirements.all())
            if method == "GET" and path == "/api/tasks":
                return json_response(handler, sys_.tasks)
            if method == "GET" and path == "/api/communications":
                return json_response(handler, sys_.bus.all())
            if method == "GET" and path == "/api/commits":
                return json_response(handler, sys_.refresh_commits())
            if method == "GET" and path == "/api/wbs":
                return json_response(handler, sys_.store.load_wbs())
            if method == "GET" and path == "/api/wbs/critical-path":
                return json_response(handler, sys_.wbs.critical_path())
            if method == "GET" and re.match(r"^/api/requirements/[^/]+/trace$", path):
                rid = path.split("/")[3]
                chain = sys_.requirements.traceability_chain(rid, sys_.tasks, sys_.bus.all(), sys_.commits())
                return json_response(handler, chain or {"error": "not found"}, 404 if not chain else 200)
            if method == "GET" and re.match(r"^/api/repos/[^/]+/files", path):
                return json_response(handler, self._repo_files(path.split("/")[3]))
            if method == "GET" and re.match(r"^/api/repos/[^/]+/tree", path):
                return json_response(handler, self._repo_tree(path.split("/")[3]))
            if method == "GET" and re.match(r"^/api/repos/[^/]+/file", path):
                q = urllib.parse.parse_qs(query)
                fp = (q.get("path") or [""])[0]
                return json_response(handler, self._repo_file(path.split("/")[3], fp))
            if method == "POST" and path == "/api/chat":
                return self._chat(handler, body_bytes)
            if method == "POST" and path == "/api/run/step":
                return self._run_step(handler)
            if method == "POST" and path == "/api/commit/check":
                return self._commit_check(handler, body_bytes)
            if method == "POST" and path == "/api/reset":
                return self._reset(handler)
            return json_response(handler, {"error": "not found", "path": path}, 404)
        except Exception as e:  # noqa
            return json_response(handler, {"error": str(e), "type": type(e).__name__}, 500)

    # ------------------------------------------------------------------ #
    # Payload 构造
    # ------------------------------------------------------------------ #
    def _roles_payload(self):
        out = []
        for code in sorted(roles_mod.ROLES.keys()):
            r = roles_mod.ROLES[code]
            out.append({
                "code": code, "name": r["name"], "abbr": r["abbr"], "group": r["group"],
                "responsibilities": r["responsibilities"], "deliverables": r["deliverables"],
                "phase": r["phase"], "is_main": r.get("is_main", False),
            })
        return {"roles": out, "groups": dict(roles_mod.ROLE_GROUPS),
                "ipd_phases": roles_mod.IPD_PHASES,
                "phase_cn": roles_mod.IPD_PHASE_CN,
                "project_type_roles": roles_mod.PROJECT_TYPE_ROLES,
                "project_type_cn": roles_mod.PROJECT_TYPE_CN,
                "commit_types": COMMIT_TYPE_CN}

    # -- 仓库文件浏览（模拟 §5.1 仓库拓扑） -----------------------------------
    def _repo_files(self, repo):
        """返回某仓库的虚拟文件树（模拟各 Sub-Agent 仓库内容）。"""
        sys_ = self.system
        agent = next((a for a in sys_.agents if a["repo_path"] == repo), None)
        if not agent and repo != sys_.project.get("main_repo_path"):
            return []
        base = []
        if repo == sys_.project.get("main_repo_path"):
            base = [".project-agent", "docs", "deliverables", "submodules"]
        else:
            base = ["src", "docs", "tests", ".agent"]
        files = []
        for b in base:
            files.append({"name": b, "type": "dir", "path": b})
        return files
    def _repo_tree(self, repo):
        """返回更完整的虚拟文件树（含样例文件）。"""
        sys_ = self.system
        agent = next((a for a in sys_.agents if a["repo_path"] == repo), None)
        if repo == sys_.project.get("main_repo_path"):
            return {
                "name": repo, "type": "dir", "children": [
                    {"name": ".project-agent", "type": "dir", "children": [
                        {"name": "project.yaml", "type": "file"},
                        {"name": "agents.yaml", "type": "file"},
                        {"name": "wbs.yaml", "type": "file"},
                        {"name": "communications", "type": "dir", "children": [
                            {"name": "COMM-0001.yaml", "type": "file"},
                            {"name": "COMM-0002.yaml", "type": "file"}]},
                    ]},
                    {"name": "docs", "type": "dir", "children": [
                        {"name": "srs_v0.9.md", "type": "file"},
                        {"name": "architecture_v0.8.md", "type": "file"},
                        {"name": "system_plan_v1.0.md", "type": "file"}]},
                    {"name": "deliverables", "type": "dir", "children": [
                        {"name": "concept", "type": "dir"}, {"name": "plan", "type": "dir"},
                        {"name": "development", "type": "dir"}, {"name": "verification", "type": "dir"},
                        {"name": "release", "type": "dir"}]},
                    {"name": "submodules", "type": "dir", "children": []},
                ],
            }
        if agent:
            role = agent["role_code"]
            abbr = agent["role_abbr"].lower()
            files = []
            if role in ("R01", "R03", "R05", "R16", "R10", "R25"):
                files.append({"name": "docs", "type": "dir", "children": [
                    {"name": "%s_design.md" % abbr, "type": "file"},
                    {"name": "%s_spec.md" % abbr, "type": "file"}]})
            if role in ("R05", "R11", "R12", "R13", "R14", "R15", "R16", "R18"):
                files.append({"name": "src", "type": "dir", "children": [
                    {"name": "module_%s.c" % abbr, "type": "file"},
                    {"name": "module_%s.py" % abbr, "type": "file"}]})
            if role in ("R05", "R11", "R18", "R16"):
                files.append({"name": "tests", "type": "dir", "children": [
                    {"name": "test_%s.py" % abbr, "type": "file"}]})
            files.append({"name": ".agent", "type": "dir", "children": [
                {"name": "role.yaml", "type": "file"},
                {"name": "tasks.yaml", "type": "file"},
                {"name": "requirements.yaml", "type": "file"},
                {"name": "communications.log", "type": "file"}]})
            return {"name": repo, "type": "dir", "children": files}
        return {"name": repo, "type": "dir", "children": []}
    def _repo_file(self, repo, path):
        sys_ = self.system
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if path.endswith("project.yaml"):
            return {"path": path, "content": "# 项目配置（§5.1）\nproject:\n  name: %s\n  type: %s\n  current_phase: %s\n" % (
                sys_.project.get("name", ""), sys_.project.get("type", ""), sys_.project.get("current_phase", ""))}
        if path.endswith("agents.yaml"):
            lines = ["# Agent 注册信息（§5.1）\nagents:"]
            for a in sys_.agents:
                lines.append("  - id: %s\n    role: %s\n    repo: %s\n    status: %s" % (
                    a["id"], a["role_name"], a["repo_path"], a["status"]))
            return {"path": path, "content": "\n".join(lines)}
        if path.endswith("wbs.yaml"):
            lines = ["# WBS 工作分解结构（§5.1）\nwbs:"]
            for w in sys_.store.load_wbs():
                lines.append("  - id: %s\n    title: %s\n    role: %s\n    phase: %s" % (
                    w["id"], w["title"], w.get("role", ""), w["phase"]))
            return {"path": path, "content": "\n".join(lines)}
        if "COMM-" in path and path.endswith(".yaml"):
            cid = path.split("/")[-1].replace(".yaml", "")
            rec = sys_.bus.get(cid)
            if rec:
                from .core.comm import CommunicationBus
                return {"path": path, "content": CommunicationBus(sys_.store).to_yaml(rec)}
        if path.endswith("communications.log"):
            lines = ["# 通信记录本地缓存（§4.2）"]
            for c in sys_.bus.all()[-20:]:
                lines.append("%s | %s -> %s | %s | %s" % (
                    c["timestamp"], c["from"].get("role"), c["to"].get("role"),
                    c["id"], c["subject"]))
            return {"path": path, "content": "\n".join(lines)}
        if path.endswith("tasks.yaml"):
            lines = ["# 任务列表（§4.2）\ntasks:"]
            agent_repo = repo
            for t in sys_.tasks:
                agent = sys_.get_agent(t["agent_id"])
                if agent and agent["repo_path"] == agent_repo:
                    lines.append("  - id: %s\n    title: %s\n    status: %s" % (
                        t["id"], t["title"], t["status"]))
            return {"path": path, "content": "\n".join(lines)}
        if path.endswith("role.yaml"):
            agent_repo = repo
            agent = next((a for a in sys_.agents if a["repo_path"] == agent_repo), None)
            if agent:
                r = roles_mod.ROLES.get(agent["role_code"], {})
                return {"path": path, "content": "# 角色定义（§4.2）\nrole:\n  code: %s\n  name: %s\n  abbr: %s\n  responsibilities:\n%s" % (
                    agent["role_code"], agent["role_name"], agent["role_abbr"],
                    "\n".join("    - %s" % x for x in r.get("responsibilities", [])))}
        # 通用文本回退
        return {"path": path,
                "content": "# %s\n\n（该文件为 %s 仓库中的虚拟示例文件，实际内容由各 Agent 在开发过程中生成。）"
                          % (path, repo)}

    # ------------------------------------------------------------------ #
    # 操作接口
    # ------------------------------------------------------------------ #
    def _chat(self, handler, body_bytes):
        data = json.loads(body_bytes or b"{}")
        to = data.get("to", "main")
        content = data.get("content", "")
        if not content:
            return json_response(handler, {"error": "empty content"}, 400)
        rec = self.system.runtime.user_message(to, content)
        return json_response(handler, {"comm": rec})
    def _run_step(self, handler):
        result = self.system.runtime.step()
        if result is None:
            return json_response(handler, {"done": True, "message": "无待执行动作"})
        return json_response(handler, {"done": False, "message": result})
    def _commit_check(self, handler, body_bytes):
        data = json.loads(body_bytes or b"{}")
        message = data.get("message", "")
        ok, errors = validate_commit(message)
        parsed = None
        if ok:
            parsed = parse_commit(message)
        return json_response(handler, {"ok": ok, "errors": errors, "parsed": parsed})
    def _reset(self, handler):
        import shutil
        shutil.rmtree(self.system.data_dir, ignore_errors=True)
        from .seed.demo_npu import seed
        system2 = self.system.__class__(self.system.data_dir)
        seed(system2)
        self.system = system2
        return json_response(handler, {"ok": True})
