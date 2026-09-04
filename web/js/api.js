/* api.js — REST API 客户端 */
const API = {
  async get(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error((await r.text()) || r.statusText);
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) throw new Error((await r.text()) || r.statusText);
    return r.json();
  },
  overview: () => API.get("/api/overview"),
  project: () => API.get("/api/project"),
  roles: () => API.get("/api/roles"),
  agents: () => API.get("/api/agents"),
  requirements: () => API.get("/api/requirements"),
  tasks: () => API.get("/api/tasks"),
  communications: () => API.get("/api/communications"),
  commits: () => API.get("/api/commits"),
  wbs: () => API.get("/api/wbs"),
  trace: (rid) => API.get("/api/requirements/" + encodeURIComponent(rid) + "/trace"),
  repoTree: (repo) => API.get("/api/repos/" + encodeURIComponent(repo) + "/tree"),
  repoFile: (repo, path) =>
    API.get("/api/repos/" + encodeURIComponent(repo) + "/file?path=" + encodeURIComponent(path)),
  chat: (to, content) => API.post("/api/chat", { to, content }),
  runStep: () => API.post("/api/run/step", {}),
  commitCheck: (message) => API.post("/api/commit/check", { message }),
  reset: () => API.post("/api/reset", {}),
};
