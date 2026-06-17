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
  docVersions: (caseId, docId) =>
    fetch(`/api/cases/${caseId}/documents/${docId}/versions`).then(json),
  docCheckout: (caseId, docId) =>
    fetch(`/api/cases/${caseId}/documents/${docId}/checkout`, { method: 'POST' }).then(json),
  docCheckin: (caseId, docId, content, changeSummary) =>
    fetch(`/api/cases/${caseId}/documents/${docId}/checkin`, {
      method: 'POST', body: form({ content, change_summary: changeSummary || '' }),
    }).then(json),
  docDiff: (caseId, docId, a, b) =>
    fetch(`/api/cases/${caseId}/documents/${docId}/diff?a=${a}&b=${b}`).then(json),
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
  listTemplates: () => fetch('/api/templates').then(json),
  draft: (caseId, instructions, templateId) =>
    fetch('/api/agents/draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_id: caseId, instructions, template_id: templateId || null }),
    }).then(json),
  checkConsistency: (caseId) =>
    fetch(`/api/agents/consistency/${caseId}`, { method: 'POST' }).then(json),
  resolveFinding: (caseId, fid, status, justification, kind) =>
    fetch(`/api/cases/${caseId}/findings/${fid}/resolution`, {
      method: 'POST',
      body: form({ status, justification: justification || '', kind: kind || '' }),
    }).then(json),
  findingResolutions: (caseId) =>
    fetch(`/api/cases/${caseId}/findings/resolutions`).then(json),
  boardGate: (caseId) => fetch(`/api/cases/${caseId}/board-gate`).then(json),
  submitReview: (caseId) => fetch(`/api/cases/${caseId}/submit-review`, { method: 'POST' }).then(json),
  acknowledgeReview: (caseId) => fetch(`/api/cases/${caseId}/review/acknowledge`, { method: 'POST' }).then(json),
  reviewState: (caseId) => fetch(`/api/cases/${caseId}/review-state`).then(json),
  reconcile: (caseId) =>
    fetch(`/api/agents/reconcile/${caseId}`, { method: 'POST' }).then(json),
  draftAction: (caseId, paragraphId, action, finalContent) =>
    fetch(`/api/cases/${caseId}/draft/actions`, {
      method: 'POST',
      body: form({ paragraph_id: paragraphId, action, final_content: finalContent || '' }),
    }).then(json),
  draftActionState: (caseId) => fetch(`/api/cases/${caseId}/draft/actions`).then(json),
  draftExportUrl: (caseId) => `/api/cases/${caseId}/draft/export`,
  route: (payload) =>
    fetch('/api/agents/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(json),
  runPipeline: (caseId) => fetch(`/api/agents/pipeline/${caseId}`, { method: 'POST' }).then(json),
  reviewPanel: (caseId) => fetch(`/api/agents/review-panel/${caseId}`, { method: 'POST' }).then(json),
  audit: (limit = 200) => fetch(`/api/audit?limit=${limit}`).then(json),
  sops: () => fetch('/api/sop').then(json),
  sopCoverage: () => fetch('/api/sop/coverage').then(json),
  decisionTree: () => fetch('/api/routing/decision-tree').then(json),
  riskScore: (category, amount, entity, precedents) =>
    fetch(`/api/risk/score?request_category=${category}&amount_idr=${amount || 0}&entity=${encodeURIComponent(entity || '')}&precedents=${precedents || 0}`).then(json),
  automationMetrics: () => fetch('/api/metrics/automation').then(json),
  rulesVersion: () => fetch('/api/rules/version').then(json),
  ruleChanges: () => fetch('/api/rules/changes').then(json),
  proposeRuleChange: (summary, detail) =>
    fetch('/api/rules/changes', { method: 'POST', body: form({ summary, detail: detail || '' }) }).then(json),
  decideRuleChange: (id, decision) =>
    fetch(`/api/rules/changes/${id}/decide`, { method: 'POST', body: form({ decision }) }).then(json),
  routingSimulate: (requestType, amountIdr) =>
    fetch(`/api/routing/simulate?request_type=${requestType}&amount_idr=${amountIdr || 0}`).then(json),
};
