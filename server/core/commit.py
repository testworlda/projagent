# -*- coding: utf-8 -*-
"""
commit.py — Commit Message 规范（§5.4）
实现 Commit 消息的生成、解析与校验：
  <type>(<scope>): <subject>
  <body>
  Refs:
    - Requirement: REQ-{project}-{seq}
    - Task: TASK-{project}-{seq}
    - Communication: COMM-{seq}
    - Parent-Commit: {hash}
    - Agent: {role-name}
    - Phase: {ipd-phase}
  Change-Id: {generated-hash}
"""
import re

COMMIT_TYPES = ["feat", "fix", "docs", "refactor", "test", "chore", "review", "comm", "plan"]
COMMIT_TYPE_CN = {
    "feat": "新功能/新设计/新模块",
    "fix": "BUG 修复",
    "docs": "文档新增/更新",
    "refactor": "重构（不改变功能）",
    "test": "测试相关",
    "chore": "构建/工具/配置变更",
    "review": "评审意见响应",
    "comm": "通信记录提交",
    "plan": "项目计划/WBS 变更",
}

class CommitError(Exception):
    pass

def format_commit(ctype, scope, subject, body=None, requirement_ids=None,
                  task_ids=None, comm_ids=None, parent_commit=None,
                  agent=None, phase=None, change_id=None):
    """按 §5.4 规范生成完整 Commit Message。"""
    if ctype not in COMMIT_TYPES:
        raise CommitError("非法 commit type: %s" % ctype)
    head = "%s(%s): %s" % (ctype, scope, subject)
    lines = [head]
    if body:
        lines.append("")
        lines.append(body.strip())
    lines.append("")
    lines.append("Refs:")
    for rid in (requirement_ids or []):
        lines.append("- Requirement: %s" % rid)
    for tid in (task_ids or []):
        lines.append("- Task: %s" % tid)
    for cid in (comm_ids or []):
        lines.append("- Communication: %s" % cid)
    if parent_commit:
        lines.append("- Parent-Commit: %s" % (parent_commit[:8] if parent_commit else ""))
    if agent:
        lines.append("- Agent: %s" % agent)
    if phase:
        lines.append("- Phase: %s" % phase)
    lines.append("")
    lines.append("Change-Id: %s" % (change_id or ""))
    return "\n".join(lines)

_REF_RE = re.compile(r"^\s*-\s*(Requirement|Task|Communication|Parent-Commit|Agent|Phase):\s*(.+?)\s*$")
_HEAD_RE = re.compile(r"^([a-z]+)\(([^)]+)\):\s*(.+)$")

def parse_commit(message):
    """解析 Commit Message，返回结构化 dict。"""
    result = {
        "type": None, "scope": None, "subject": None, "body": "",
        "requirement_ids": [], "task_ids": [], "comm_ids": [],
        "parent_commit": None, "agent": None, "phase": None, "change_id": None,
    }
    lines = message.splitlines()
    body_lines = []
    in_refs = False
    for i, line in enumerate(lines):
        if i == 0:
            m = _HEAD_RE.match(line)
            if not m:
                raise CommitError("Commit 头格式错误: %s" % line)
            result["type"], result["scope"], result["subject"] = m.groups()
            continue
        if line.strip() == "Refs:":
            in_refs = True
            continue
        if in_refs:
            m = _REF_RE.match(line)
            if m:
                key, val = m.groups()
                if key == "Requirement":
                    result["requirement_ids"].append(val.strip())
                elif key == "Task":
                    result["task_ids"].append(val.strip())
                elif key == "Communication":
                    result["comm_ids"].append(val.strip())
                elif key == "Parent-Commit":
                    result["parent_commit"] = val.strip()
                elif key == "Agent":
                    result["agent"] = val.strip()
                elif key == "Phase":
                    result["phase"] = val.strip()
            elif line.startswith("Change-Id:"):
                result["change_id"] = line.split(":", 1)[1].strip()
            elif line.strip() == "":
                continue
            else:
                # Refs 块中的其他行忽略
                continue
        else:
            body_lines.append(line)
    result["body"] = "\n".join(body_lines).strip()
    return result

def validate_commit(message, require_refs=True):
    """校验 Commit 是否符合规范，返回 (ok, errors)。"""
    errors = []
    try:
        parsed = parse_commit(message)
    except CommitError as e:
        return False, [str(e)]
    if parsed["type"] not in COMMIT_TYPES:
        errors.append("type 不在枚举内: %s" % parsed["type"])
    if not parsed["subject"]:
        errors.append("缺少 subject")
    if require_refs and not parsed["requirement_ids"] and not parsed["task_ids"]:
        errors.append("缺少 Requirement/Task 关联（可追溯性要求）")
    if not parsed["change_id"]:
        errors.append("缺少 Change-Id")
    return (len(errors) == 0), errors
