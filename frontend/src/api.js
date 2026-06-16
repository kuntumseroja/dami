const json = (res) => {
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
};

const form = (data) => {
  const fd = new FormData();
  Object.entries(data).forEach(([k, v]) => v != null && fd.append(k, v));
  return fd;
};

export const api = {
  listCases: () => fetch('/api/cases').then(json),
  getCase: (caseId) => fetch(`/api/cases/${caseId}`).then(json),
  listDocuments: (caseId) => fetch(`/api/cases/${caseId}/documents`).then(json),
  checklist: (caseId) => fetch(`/api/cases/${caseId}/checklist`).then(json),
  documentFileUrl: (docId) => `/api/documents/${docId}/file`,
  deleteDocument: (caseId, docId) =>
    fetch(`/api/cases/${caseId}/documents/${docId}`, { method: 'DELETE' }).then(json),
  createCase: (title) => fetch('/api/cases', { method: 'POST', body: form({ title }) }).then(json),
  advanceCase: (caseId, signoffBy) =>
    fetch(`/api/cases/${caseId}/advance`, { method: 'POST', body: form({ signoff_by: signoffBy }) }).then(json),
  ingest: (file, docType, caseId) =>
    fetch('/api/documents/ingest', {
      method: 'POST',
      body: form({ file, doc_type: docType, case_id: caseId }),
    }).then(json),
  draft: (caseId, instructions) =>
    fetch('/api/agents/draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_id: caseId, instructions }),
    }).then(json),
  checkConsistency: (caseId) =>
    fetch(`/api/agents/consistency/${caseId}`, { method: 'POST' }).then(json),
  route: (payload) =>
    fetch('/api/agents/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(json),
  runPipeline: (caseId) => fetch(`/api/agents/pipeline/${caseId}`, { method: 'POST' }).then(json),
  audit: (limit = 200) => fetch(`/api/audit?limit=${limit}`).then(json),
};
