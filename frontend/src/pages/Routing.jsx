import { useState } from 'react';
import {
  Button,
  InlineLoading,
  InlineNotification,
  NumberInput,
  Select,
  SelectItem,
  Tag,
  TextInput,
} from '@carbon/react';
import { DecisionTree } from '@carbon/icons-react';
import { api } from '../api';

const RISK_TAG = { low: 'green', medium: 'blue', high: 'red' };

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
      <h1 className="dam-page-title">SOP Routing &amp; Eligibility</h1>
      <p className="dam-page-subtitle">
        Deterministic rules — digitized SOPs and delegation-of-authority
        thresholds — decide which SOP applies, whether approval is required, and
        the automation tier. The AI only explains; it never overrides the rules.
      </p>

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
            <SelectItem value="asset_lease" text="Asset lease" />
            <SelectItem value="asset_utilization" text="Asset utilization" />
            <SelectItem value="asset_disposal" text="Asset disposal" />
            <SelectItem value="asset_acquisition" text="Asset acquisition" />
            <SelectItem value="investment" text="Investment" />
            <SelectItem value="other" text="Other" />
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
          <p>
            <Tag type={decision.approval_required ? 'red' : 'green'}>
              {decision.approval_required
                ? `Approval required — ${decision.approval_level?.replaceAll('_', ' ')}`
                : 'No approval required'}
            </Tag>{' '}
            <Tag type={RISK_TAG[decision.risk_tier]}>{decision.risk_tier} risk</Tag>
          </p>
          <p style={{ whiteSpace: 'pre-wrap' }}>{decision.explanation}</p>
          <p style={{ fontSize: '0.75rem', color: '#525252' }}>
            Rules fired: {decision.rules_fired.map((r) => <code key={r}>{r} </code>)}
            · Trace: <code>{decision.trace_id}</code>
          </p>
        </div>
      )}
    </div>
  );
}
