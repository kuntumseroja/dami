import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Button, InlineLoading, InlineNotification, TextInput } from '@carbon/react';
import { Scales } from '@carbon/icons-react';
import { api } from '../api';

const SEV = { critical: 'error', major: 'warning', minor: 'neutral', ok: 'success' };
const REC = {
  endorse: { pill: 'success', label: 'Endorse' },
  endorse_with_conditions: { pill: 'warning', label: 'Endorse with conditions' },
  return_for_revision: { pill: 'error', label: 'Return for revision' },
};

export default function ReviewPanel() {
  const { caseId: routeCaseId } = useParams();
  const [caseId, setCaseId] = useState(routeCaseId || '');
  const [review, setReview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setReview(await api.reviewPanel(caseId));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const chair = review?.chair;
  const rec = chair && (REC[chair.recommendation] || { pill: 'neutral', label: chair.recommendation });

  return (
    <div className="dam-page">
      <div className="dam-page-header">
        <div>
          <h1 className="dam-page-title">NOTA Review Panel</h1>
          <p className="dam-page-subtitle">
            Specialist MD reviewers (Investment · Risk · Legal · Finance) + deterministic
            reconciliation score the draft against the governance rubric; a bias-controlled
            Chair adjudicates. Every finding is cited; the panel reviews — humans decide.
          </p>
        </div>
      </div>

      {error && <InlineNotification kind="error" title="Error" subtitle={error} lowContrast />}

      <div className="dam-card" style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
        <TextInput id="case-id" labelText="Case ID" placeholder="case_xxxxxxxxxx"
          value={caseId} onChange={(e) => setCaseId(e.target.value)} />
        {busy ? (
          <InlineLoading description="Convening panel (4 reviewers + reconciliation + chair)…" />
        ) : (
          <Button renderIcon={Scales} onClick={run} disabled={!caseId}>Convene review panel</Button>
        )}
      </div>

      {chair && (
        <>
          {/* Chair adjudication */}
          <div className="dam-card dam-card--accent">
            <div style={{ display: 'flex', gap: 'var(--sp-3)', alignItems: 'center', flexWrap: 'wrap', marginBottom: 'var(--sp-3)' }}>
              <span className={`dam-pill dam-pill--${rec.pill}`}>{rec.label}</span>
              <span className="dam-pill dam-pill--info dam-pill--plain">confidence {Math.round((chair.confidence || 0) * 100)}%</span>
              <span className="dam-pill dam-pill--neutral dam-pill--plain">{review.risk_tier} risk</span>
              {review.dropped_uncited > 0 && (
                <span className="dam-meta">{review.dropped_uncited} uncited finding(s) dropped (FR-1 gate)</span>
              )}
            </div>
            <p style={{ marginTop: 0 }}>{chair.summary}</p>
            {chair.needs_human_review && (
              <InlineNotification kind="warning" lowContrast hideCloseButton
                title="Needs human review"
                subtitle={chair.unresolved_issues.length
                  ? `Unresolved: ${chair.unresolved_issues.join('; ')}`
                  : 'Chair flags this for the human four-eyes checker.'}
                style={{ marginBottom: 'var(--sp-3)' }} />
            )}
            {chair.dimension_scores.length > 0 && (
              <div className="dam-process-grid">
                {chair.dimension_scores.map((d) => (
                  <div key={d.dimension} className="dam-card" style={{ margin: 0, boxShadow: 'none' }}>
                    <div className="dam-doc__meta">{d.dimension}</div>
                    <span className={`dam-pill dam-pill--${SEV[d.severity] || 'neutral'}`}>{d.severity}</span>
                    {d.status && <p className="dam-meta" style={{ marginTop: 'var(--sp-2)' }}>{d.status}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Specialist reviewers */}
          <div className="dam-section"><h2 className="dam-section__title">Specialist findings</h2>
            <span className="dam-section__meta">{review.findings.length} cited findings</span></div>
          {review.reviewers.map((r) => (
            <div key={r.reviewer_id} className="dam-card">
              <h3 className="dam-subhead" style={{ marginTop: 0 }}>
                {r.title}
                <span className="dam-pill dam-pill--info dam-pill--plain">confidence {Math.round((r.confidence || 0) * 100)}%</span>
              </h3>
              {r.findings.length === 0 ? (
                <p className="dam-muted">No issues raised on its dimensions.</p>
              ) : r.findings.map((f, i) => (
                <div key={i} className={`dam-finding dam-finding--${f.severity === 'critical' ? 'critical' : f.severity === 'major' ? 'major' : 'minor'}`} style={{ paddingLeft: 'var(--sp-4)', marginBottom: 'var(--sp-3)' }}>
                  <div style={{ display: 'flex', gap: 'var(--sp-2)', alignItems: 'center' }}>
                    <span className={`dam-pill dam-pill--${SEV[f.severity]}`}>{f.severity}</span>
                    <span className="dam-pill dam-pill--neutral dam-pill--plain">{f.dimension}</span>
                    <strong>{f.title}</strong>
                  </div>
                  <p style={{ margin: 'var(--sp-2) 0' }}>{f.detail}</p>
                  <p className="dam-meta">cite: <code>{f.citation}</code></p>
                </div>
              ))}
            </div>
          ))}
          {review.findings.some((f) => f.reviewer_id === 'financial_reconciliation') && (
            <div className="dam-card">
              <h3 className="dam-subhead" style={{ marginTop: 0 }}>Financial &amp; Statistical Reconciliation
                <span className="dam-pill dam-pill--neutral dam-pill--plain">deterministic</span></h3>
              {review.findings.filter((f) => f.reviewer_id === 'financial_reconciliation').map((f, i) => (
                <div key={i} className="dam-finding dam-finding--critical" style={{ paddingLeft: 'var(--sp-4)', marginBottom: 'var(--sp-3)' }}>
                  <span className="dam-pill dam-pill--error">{f.severity}</span>
                  <p style={{ margin: 'var(--sp-2) 0' }}>{f.detail}</p>
                  <p className="dam-meta">cite: <code>{f.citation}</code></p>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
