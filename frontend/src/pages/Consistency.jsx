import { useState } from 'react';
import {
  Button,
  InlineLoading,
  InlineNotification,
  TextInput,
} from '@carbon/react';
import { Compare, Calculator } from '@carbon/icons-react';
import { api } from '../api';

const SEVERITY_PILL = {
  critical: 'error', warning: 'warning', informational: 'neutral',
  major: 'warning', minor: 'neutral', info: 'neutral',   // reconciliation severities
};
const idr = (n) => (Math.abs(n) >= 1e9 ? `${(n / 1e9).toFixed(2)} bn` : n.toLocaleString());

export default function Consistency() {
  const [caseId, setCaseId] = useState('');
  const [report, setReport] = useState(null);
  const [recon, setRecon] = useState(null);
  const [busy, setBusy] = useState(false);
  const [reconBusy, setReconBusy] = useState(false);
  const [error, setError] = useState(null);

  const [resolutions, setResolutions] = useState({});
  const [justif, setJustif] = useState({});
  const [gate, setGate] = useState(null);
  const [review, setReview] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const refreshGate = (id = caseId) =>
    api.boardGate(id).then(setGate).catch(() => setGate(null));
  const refreshReview = (id = caseId) =>
    api.reviewState(id).then((s) => setReview(s && s.submitted_at ? s : null)).catch(() => setReview(null));

  const submitReview = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await api.submitReview(caseId);   // auto-runs consistency, queues pending ack
      setReport(await api.checkConsistency(caseId).catch(() => report));
      refreshReview(); refreshGate();
    } catch (e) { setError(e.message); } finally { setSubmitting(false); }
  };

  const acknowledge = async () => {
    try { await api.acknowledgeReview(caseId); refreshReview(); }
    catch (e) { setError(e.message); }
  };

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setReport(await api.checkConsistency(caseId));
      api.findingResolutions(caseId).then(setResolutions).catch(() => setResolutions({}));
      refreshGate(); refreshReview();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const resolve = async (f, status) => {
    const j = justif[f.id] || '';
    if ((status === 'accepted_as_is' || status === 'incorrect_flag') && !j.trim()) {
      setError('A justification is required for accept-as-is / incorrect-flag.');
      return;
    }
    try {
      await api.resolveFinding(caseId, f.id, status, j, f.kind);
      setResolutions((m) => ({ ...m, [f.id]: { status, justification: j } }));
      refreshGate();
    } catch (e) { setError(e.message); }
  };

  const reconcile = async () => {
    setReconBusy(true);
    setError(null);
    try {
      setRecon(await api.reconcile(caseId));
    } catch (e) {
      setError(e.message);
    } finally {
      setReconBusy(false);
    }
  };

  return (
    <div className="dam-page">
      <div className="dam-page-header">
        <div>
          <h1 className="dam-page-title">Cross-Document Consistency Checker</h1>
          <p className="dam-page-subtitle">
            Compares review notes, board notes, decision documents, and communications
            against the master submission — flagging inconsistencies, outdated
            references, and missing updates before sign-off.
          </p>
        </div>
      </div>

      {error && (
        <InlineNotification kind="error" title="Error" subtitle={error} lowContrast />
      )}

      <div className="dam-card" style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
        <TextInput
          id="case-id"
          labelText="Case ID"
          placeholder="case_xxxxxxxxxx"
          value={caseId}
          onChange={(e) => setCaseId(e.target.value)}
        />
        {busy ? (
          <InlineLoading description="Comparing documents…" />
        ) : (
          <Button renderIcon={Compare} onClick={run} disabled={!caseId}>
            Run consistency check
          </Button>
        )}
        {reconBusy ? (
          <InlineLoading description="Recomputing figures…" />
        ) : (
          <Button kind="tertiary" renderIcon={Calculator} onClick={reconcile} disabled={!caseId}>
            Reconcile figures
          </Button>
        )}
      </div>

      {/* Senior review queue: auto-trigger consistency + acknowledgment gate (3.6) */}
      <div className="dam-card" style={{ display: 'flex', gap: 'var(--sp-3)', alignItems: 'center', flexWrap: 'wrap' }}>
        {submitting ? (
          <InlineLoading description="Submitting & auto-checking…" />
        ) : (
          <Button kind="tertiary" onClick={submitReview} disabled={!caseId}>
            Submit to senior review queue
          </Button>
        )}
        {review && (
          <>
            <span className={`dam-pill dam-pill--${review.acknowledged ? 'success' : 'warning'} dam-pill--plain`}>
              {review.acknowledged ? 'Acknowledged — in senior inbox' : 'Submitted — awaiting acknowledgment'}
            </span>
            <span className="dam-meta">{review.findings_count} findings · {review.critical_count} critical</span>
            {!review.acknowledged && (
              <Button kind="ghost" size="sm" onClick={acknowledge}>Acknowledge report</Button>
            )}
          </>
        )}
      </div>

      {recon && (
        <>
          <div className="dam-summary" style={{ borderLeftColor: recon.mismatches ? 'var(--ibm-error)' : 'var(--ibm-success)' }}>
            <span className="dam-summary__value">{recon.mismatches}</span>
            <div>
              <div className="dam-summary__label">
                numeric mismatch{recon.mismatches === 1 ? '' : 'es'} · {recon.claims_checked} figures recomputed
              </div>
              <div className="dam-meta">deterministic calculator · trace <code>{recon.trace_id}</code></div>
            </div>
          </div>
          {recon.findings.filter((f) => f.status !== 'ok').map((f, i) => (
            <div key={i} className={`dam-card dam-finding dam-finding--${f.severity === 'critical' ? 'critical' : 'major'}`}>
              <div style={{ display: 'flex', gap: 'var(--sp-2)', marginBottom: 'var(--sp-2)' }}>
                <span className={`dam-pill dam-pill--${SEVERITY_PILL[f.severity]}`}>{f.severity}</span>
                <span className="dam-pill dam-pill--neutral dam-pill--plain">{f.status}</span>
                <span className="dam-pill dam-pill--neutral dam-pill--plain">{f.relationship}</span>
              </div>
              <p style={{ marginTop: 0 }}>{f.description}</p>
              {f.status === 'mismatch' && (
                <p className="dam-meta">
                  Stated <b>{f.claimed_result}{f.unit === '%' ? '%' : ''}</b> ·
                  recomputed <b style={{ color: 'var(--ibm-error)' }}>{f.recomputed_result}{f.unit === '%' ? '%' : ''}</b>
                  {f.unit === 'IDR' && ` (operands: ${f.operands.map(idr).join(', ')})`}
                </p>
              )}
              <p className="dam-resolution">{f.explanation}{f.source_refs.length > 0 && <> · sources: {f.source_refs.map((s) => <code key={s}>{s} </code>)}</>}</p>
            </div>
          ))}
          {recon.mismatches === 0 && (
            <div className="dam-card dam-muted">All {recon.claims_checked} recomputed figures match the stated values.</div>
          )}
        </>
      )}

      {gate && (
        <InlineNotification
          kind={gate.blocked ? 'error' : 'success'}
          lowContrast
          hideCloseButton
          title={gate.blocked ? 'Board preparation blocked' : 'Cleared for board preparation'}
          subtitle={gate.blocked
            ? `${gate.blocking.length} unresolved Critical item(s) must be resolved (or dual-approval override): ${gate.blocking.map((b) => b.kind).join(', ')}`
            : 'No unresolved Critical items.'}
          style={{ marginBottom: 'var(--sp-4)' }}
        />
      )}

      {report && (
        <>
          <div className="dam-summary">
            <span className="dam-summary__value">{report.findings.length}</span>
            <div>
              <div className="dam-summary__label">
                {report.findings.length === 0 ? 'No inconsistencies found' : 'findings'} across{' '}
                {report.documents_compared.length} documents
              </div>
              <div className="dam-meta">trace <code>{report.trace_id}</code></div>
            </div>
          </div>
          {report.findings.map((f, i) => {
            const r = resolutions[f.id];
            const border = f.severity === 'critical' ? 'critical' : f.severity === 'warning' ? 'major' : 'minor';
            return (
            <div key={i} className={`dam-card dam-finding dam-finding--${border}`}>
              <div style={{ display: 'flex', gap: 'var(--sp-2)', marginBottom: 'var(--sp-2)', alignItems: 'center' }}>
                <span className={`dam-pill dam-pill--${SEVERITY_PILL[f.severity]}`}>{f.severity}</span>
                <span className="dam-pill dam-pill--neutral dam-pill--plain">{f.kind.replaceAll('_', ' ')}</span>
                {r && <span className={`dam-pill dam-pill--${r.status === 'incorrect_flag' ? 'neutral' : r.status === 'resolved' ? 'success' : 'warning'} dam-pill--plain`} style={{ marginLeft: 'auto' }}>{r.status.replaceAll('_', ' ')}</span>}
              </div>
              <p style={{ marginTop: 0 }}>{f.description}</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-4)' }}>
                <blockquote className="dam-excerpt dam-excerpt--reference">
                  <small><code>{f.document_a}</code></small>
                  <p style={{ font: 'var(--type-link)' }}>{f.excerpt_a}</p>
                </blockquote>
                <blockquote className="dam-excerpt dam-excerpt--conflict">
                  <small><code>{f.document_b}</code></small>
                  <p style={{ font: 'var(--type-link)' }}>{f.excerpt_b}</p>
                </blockquote>
              </div>
              <p className="dam-resolution">
                <strong>Suggested resolution:</strong> {f.suggested_resolution}
              </p>
              {r?.justification && <p className="dam-meta">Justification: {r.justification}</p>}
              <TextInput id={`just-${f.id}`} size="sm" labelText=""
                placeholder="Justification (required for accept-as-is / incorrect flag)"
                value={justif[f.id] || ''}
                onChange={(e) => setJustif((m) => ({ ...m, [f.id]: e.target.value }))}
                style={{ marginBottom: 'var(--sp-2)' }} />
              <div style={{ display: 'flex', gap: 'var(--sp-2)', flexWrap: 'wrap' }}>
                <Button size="sm" kind="ghost" onClick={() => resolve(f, 'resolved')}>Resolved</Button>
                <Button size="sm" kind="ghost" onClick={() => resolve(f, 'accepted_as_is')}>Accept as-is</Button>
                <Button size="sm" kind="ghost" onClick={() => resolve(f, 'deferred')}>Defer</Button>
                <Button size="sm" kind="ghost" onClick={() => resolve(f, 'incorrect_flag')}>Incorrect flag</Button>
              </div>
            </div>
            );
          })}
        </>
      )}
    </div>
  );
}
