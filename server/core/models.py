# -*- coding: utf-8 -*-
"""
models.py — 核心数据模型
依据 PRD §6.1（Communication 数据结构）、§7.2（Requirement 数据结构）、
§11.2（Project / Agent / Task / Commit 核心实体字段）实现。
所有实体均为普通 dict 风格对象（便于 JSON 持久化与 API 透传），
通过 *_to_dict() 提供干净的序列化视图。
"""
import time

def now_iso():
    """返回本地时区的 ISO 8601 时间戳。"""
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")

# ---------------------------------------------------------------------------
# Project（§11.2）
# ---------------------------------------------------------------------------
def new_project(project_id, name, ptype, description="", main_repo_path="project-main",
                current_phase="concept", status="planning", config=None):
    return {
        "id": project_id,
        "name": name,
        "type": ptype,
        "description": description,
        "main_repo_path": main_repo_path,
        "current_phase": current_phase,
        "status": status,
        "created_at": now_iso(),
        "config": config or {},
    }

# ---------------------------------------------------------------------------
# Agent（§11.2）
# ---------------------------------------------------------------------------
def new_agent(agent_id, role_code, repo_path=None, status="idle",
              current_branch="develop", latest_commit=None, context_summary=""):
    from .roles import role_name, role_abbr
    return {
        "id": agent_id,
        "role_code": role_code,
        "role_name": role_name(role_code),
        "role_abbr": role_abbr(role_code),
        "status": status,
        "repo_path": repo_path or ("agent-%s" % role_abbr(role_code).lower()),
        "current_branch": current_branch,
        "latest_commit": latest_commit,
        "context_summary": context_summary,
        "activated_at": now_iso(),
    }

# ---------------------------------------------------------------------------
# Requirement（§7.2）
# ---------------------------------------------------------------------------
def new_requirement(req_id, title, description, source_type, origin,
                    comm_id=None, parent_commit=None, priority="medium",
                    phase="concept", assigned_role=None, status="pending",
                    acceptance_criteria=None, dependencies=None):
    return {
        "id": req_id,
        "title": title,
        "description": description,
        "source": {
            "type": source_type,          # user / main_agent / sub_agent / review
            "origin": origin,
            "comm_id": comm_id,
            "parent_commit": parent_commit,
        },
        "priority": priority,             # critical / high / medium / low
        "phase": phase,
        "assigned_role": assigned_role,
        "status": status,                 # pending / in_progress / completed / verified / blocked / cancelled
        "acceptance_criteria": acceptance_criteria or [],
        "dependencies": dependencies or [],
        "related_requirements": [],
        "created_at": now_iso(),
        "completed_at": None,
        "completed_commit": None,
    }

# ---------------------------------------------------------------------------
# Task（§11.2）
# ---------------------------------------------------------------------------
def new_task(task_id, title, description, requirement_id, agent_id, phase,
             status="pending", priority="medium", parent_task_id=None,
             dependencies=None, acceptance_criteria=None):
    return {
        "id": task_id,
        "title": title,
        "description": description,
        "requirement_id": requirement_id,
        "agent_id": agent_id,
        "phase": phase,
        "status": status,                 # pending / in_progress / completed / verified / blocked
        "priority": priority,
        "parent_task_id": parent_task_id,
        "dependencies": dependencies or [],
        "commits": [],
        "acceptance_criteria": acceptance_criteria or [],
        "created_at": now_iso(),
        "completed_at": None,
    }

# ---------------------------------------------------------------------------
# Communication（§6.1）
# ---------------------------------------------------------------------------
def new_communication(comm_id, comm_type, priority, subject, description,
                      from_info, to_info, references=None):
    return {
        "id": comm_id,
        "timestamp": now_iso(),
        "type": comm_type,                # request / response / notification / inquiry / review / escalation
        "priority": priority,             # critical / high / medium / low
        "status": "pending",              # pending / accepted / rejected / in_progress / completed / blocked / closed
        "from": from_info,                # {agent_type, role, agent_id, repo, commit, branch}
        "to": to_info,
        "subject": subject,
        "description": description,
        "references": references or {
            "requirement_ids": [],
            "task_ids": [],
            "related_comm_ids": [],
            "files": [],
        },
        "response": None,
        "closure": None,
    }

def agent_ref(agent_type, role, agent_id, repo, commit, branch="main"):
    return {
        "agent_type": agent_type,
        "role": role,
        "agent_id": agent_id,
        "repo": repo,
        "commit": commit,
        "branch": branch,
    }

# ---------------------------------------------------------------------------
# Commit 记录（§11.2 扩展的 Git Commit 元数据）
# ---------------------------------------------------------------------------
def new_commit_record(sha, repo, agent_id, ctype, subject, body="", phase=None,
                      requirement_ids=None, task_ids=None, comm_ids=None,
                      parent_commit=None, change_id=None, author=None, timestamp=None,
                      file_changes=None, branch=None):
    return {
        "hash": sha,
        "short": sha[:8] if sha else None,
        "repo": repo,
        "agent_id": agent_id,
        "type": ctype,                    # feat/fix/docs/refactor/test/chore/review/comm/plan
        "subject": subject,
        "body": body,
        "phase": phase,
        "requirement_ids": requirement_ids or [],
        "task_ids": task_ids or [],
        "comm_ids": comm_ids or [],
        "parent_commit": parent_commit,
        "change_id": change_id,
        "author": author or "agent",
        "timestamp": timestamp or now_iso(),
        "file_changes": file_changes or [],
        "branch": branch,
    }
