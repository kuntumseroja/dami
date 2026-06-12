import { useState } from 'react';
import {
  Button,
  InlineLoading,
  InlineNotification,
  Tag,
  TextInput,
} from '@carbon/react';
import { Compare } from '@carbon/icons-react';
import { api } from '../api';

const SEVERITY_TAG = { critical: 'red', major: 'magenta', minor: 'gray' };

export default function Consistency() {
  const [caseId, setCaseId] = useState('');
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setReport(await api.checkConsistency(caseId));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="dam-page">
      <h1 className="dam-page-title">Cross-Document Consistency Checker</h1>
      <p className="dam-page-subtitle">
        Compares review notes, board notes, decision documents, and communications
        against the master submission — flagging inconsistencies, outdated
        references, and missing updates before sign-off.
      </p>

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
      </div>

      {report && (
        <>
          <div className="dam-card dam-card--accent">
            <div className="dam-metric">{report.findings.length}</div>
            <div className="dam-metric-label">
              findings across {report.documents_compared.length} documents · trace{' '}
              <code>{report.trace_id}</code>
            </div>
          </div>
          {report.findings.map((f, i) => (
            <div key={i} className="dam-card">
              <Tag type={SEVERITY_TAG[f.severity]}>{f.severity}</Tag>{' '}
              <Tag type="cool-gray">{f.kind.replace('_', ' ')}</Tag>
              <p>{f.description}</p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <blockquote style={{ borderLeft: '3px solid #78a9ff', margin: 0, paddingLeft: '1rem' }}>
                  <small><code>{f.document_a}</code></small>
                  <p style={{ fontSize: '0.875rem' }}>{f.excerpt_a}</p>
                </blockquote>
                <blockquote style={{ borderLeft: '3px solid #ff8389', margin: 0, paddingLeft: '1rem' }}>
                  <small><code>{f.document_b}</code></small>
                  <p style={{ fontSize: '0.875rem' }}>{f.excerpt_b}</p>
                </blockquote>
              </div>
              <p style={{ background: '#edf5ff', padding: '0.75rem', fontSize: '0.875rem' }}>
                <strong>Suggested resolution:</strong> {f.suggested_resolution}
              </p>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
