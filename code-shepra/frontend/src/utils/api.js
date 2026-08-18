const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api';

export async function fetchProjects() {
  const res = await fetch(`${BASE_URL}/projects`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function createProject(name, sourcePath, description = '') {
  const res = await fetch(`${BASE_URL}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, source_path: sourcePath, description })
  });
  if (!res.ok) {
    const errorText = await res.text();
    let detail = errorText;
    try {
      detail = JSON.parse(errorText).detail || errorText;
    } catch (e) {}
    throw new Error(detail);
  }
  return res.json();
}

export async function deleteProject(projectId) {
  const res = await fetch(`${BASE_URL}/projects/${projectId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function startIngestion(projectId) {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/ingest`, { method: 'POST' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchFileTree(projectId) {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/files`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchFileContent(projectId, filePath) {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/files/content?file_path=${encodeURIComponent(filePath)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchMemory(projectId) {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/memory`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchExplorationSummary(projectId) {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/memory/summary`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function addSemanticMemory(projectId, content) {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteMemory(projectId, memoryId, type = 'semantic') {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/memory/${memoryId}?type=${type}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function clearMemory(projectId, type = 'semantic') {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/memory/clear?type=${type}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function searchMemory(projectId, q) {
  const res = await fetch(`${BASE_URL}/projects/${projectId}/memory/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function getIngestionProgressUrl(projectId) {
  return `${BASE_URL}/projects/${projectId}/ingest/progress`;
}

export function getChatUrl(projectId) {
  return `${BASE_URL}/projects/${projectId}/chat`;
}
