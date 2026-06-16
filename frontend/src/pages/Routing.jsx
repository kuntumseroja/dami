import { useState } from 'react';
import {
  Button,
  InlineLoading,
  InlineNotification,
  NumberInput,
  Select,
  SelectItem,
  TextInput,
} from '@carbon/react';
import { DecisionTree } from '@carbon/icons-react';
import { api } from '../api';

const RISK_PILL = { low: 'success', medium: 'warning', high: 'error' };

// Mirrors the SubmissionFields.request_category enum + SOP routing rules.
const REQUEST_TYPES = [
  ['asset_lease', 'Asset lease'],
  ['asset_utilization', 'Asset utilization'],
  ['asset_disposal', 'Asset disposal'],
  ['asset_acquisition', 'Asset acquisition'],
  ['investment', 'Investment'],
  ['debt_issuance', 'Debt issuance (bonds / sukuk)'],
  ['merger_acquisition', 'Merger & acquisition'],
  ['capital_expenditure', 'Capital expenditure / project'],
  ['asset_writeoff', 'Asset write-off'],
  ['other', 'Other'],
];

export default function Routing() {
  const [payload, setPayload] = useState({
    case_id: '',
    request_type: 'asset_lease',
    amount_idr: 0,
    business_unit: '',
  });
  const [decision, setDecision] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const set = (key) => (value) => setPayload((p) => ({ ...p, [key]: value }));

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setDecision(await api.route(payload));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="dam-page">
      <div className="dam-page-header">
        <div>
          <h1 className="dam-page-title">SOP Routing &amp; Eligibility</h1>
          <p className="dam-page-subtitle">
            Deterministic rules — digitized SOPs and delegation-of-authority
            thresholds — decide which SOP applies, whether approval is required, and
            the automation tier. The AI only explains; it never overrides the rules.
          </p>
        </div>
      </div>

      {error && (
        <InlineNotification kind="error" title="Error" subtitle={error} lowContrast />
      )}

      <div className="dam-card">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <TextInput
            id="case-id"
            labelText="Case ID"
            value={payload.case_id}
            onChange={(e) => set('case_id')(e.target.value)}
          />
          <Select
            id="request-type"
            labelText="Request type"
            value={payload.request_type}
            onChange={(e) => set('request_type')(e.target.value)}
          >
            {REQUEST_TYPES.map(([value, text]) => (
              <SelectItem key={value} value={value} text={text} />
            ))}
          </Select>
          <NumberInput
            id="amount"
            label="Amount (IDR)"
            value={payload.amount_idr}
            onChange={(_, { value }) => set('amount_idr')(Number(value) || 0)}
            step={1000000000}
            min={0}
          />
          <TextInput
            id="bu"
            labelText="Business unit"
            value={payload.business_unit}
            onChange={(e) => set('business_unit')(e.target.value)}
          />
        </div>
        <div style={{ marginTop: '1rem' }}>
          {busy ? (
            <InlineLoading description="Evaluating rules…" />
          ) : (
            <Button renderIcon={DecisionTree} onClick={run} disabled={!payload.case_id}>
              Evaluate routing
            </Button>
          )}
        </div>
      </div>

      {decision && (
        <div className="dam-card dam-card--accent">
          <h2 style={{ fontWeight: 300, marginTop: 0 }}>{decision.applicable_sop}</h2>
          <div style={{ display: 'flex', gap: 'var(--sp-2)', flexWrap: 'wrap', margin: 'var(--sp-3) 0' }}>
            <span className={`dam-pill dam-pill--${decision.approval_required ? 'warning' : 'success'}`}>
              {decision.approval_required
                ? `Approval — ${decision.approval_level?.replaceAll('_', ' ')}`
                : 'No approval required'}
            </span>
            <span className={`dam-pill dam-pill--${RISK_PILL[decision.risk_tier]}`}>
              {decision.risk_tier} risk
            </span>
          </div>
          <p style={{ whiteSpace: 'pre-wrap' }}>{decision.explanation}</p>
          <p className="dam-meta">
            Rules fired: {decision.rules_fired.map((r) => <code key={r}>{r} </code>)}
            · Trace: <code>{decision.trace_id}</code>
          </p>
        </div>
      )}
    </div>
  );
}
