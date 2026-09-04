# -*- coding: utf-8 -*-
"""
ids.py — 全局唯一 ID 生成与解析
依据 PRD §5.4 / §6.1 / §7.2 的 ID 规范：
  - 需求: REQ-{project}-{seq}
  - 任务: TASK-{project}-{seq}
  - 通信: COMM-{seq}
  - 变更: Change-Id: I{40位十六进制}
"""
import hashlib
import itertools
import re

_REQ = re.compile(r"^REQ-([A-Z0-9]+)-(\d+)$")
_TASK = re.compile(r"^TASK-([A-Z0-9]+)-(\d+)$")
_COMM = re.compile(r"^COMM-(\d+)$")

class IdGenerator:
    """线程安全（GIL 下自增即可）的序列 ID 生成器。"""
    def __init__(self, project_key="NPU"):
        self.project_key = project_key
        self._req_counter = itertools.count(1)
        self._task_counter = itertools.count(1)
        self._comm_counter = itertools.count(1)
    def next_req(self):
        return "REQ-%s-%04d" % (self.project_key, next(self._req_counter))
    def next_task(self):
        return "TASK-%s-%04d" % (self.project_key, next(self._task_counter))
    def next_comm(self):
        return "COMM-%04d" % next(self._comm_counter)

def make_change_id(*parts):
    """生成 Commit 的 Change-Id（I + 40 位十六进制）。"""
    raw = "|".join(str(p) for p in parts)
    return "I" + hashlib.sha1(raw.encode("utf-8")).hexdigest()

def short_sha(sha, n=8):
    return sha[:n] if sha else None

def parse_req_id(rid):
    m = _REQ.match(rid or "")
    return m.groups() if m else None

def parse_task_id(tid):
    m = _TASK.match(tid or "")
    return m.groups() if m else None

def parse_comm_id(cid):
    m = _COMM.match(cid or "")
    return m.groups() if m else None
