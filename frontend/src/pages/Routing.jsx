import { useEffect, useState } from 'react';
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
  ['merger_acquisition', 'Merger / acquisition / consolidation'],
  ['capital_expenditure', 'Capital expenditure / project'],
  ['asset_writeoff', 'Asset write-off'],
  ['rights_issue', 'Rights issue (HMETD)'],
  ['ipo', 'Initial public offering (IPO)'],
  ['spin_off', 'Spin-off / carve-out'],
  ['dissolution', 'Dissolution / liquidation'],
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
  const [sops, setSops] = useState([]);
  const [coverage, setCoverage] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [tree, setTree] = useState(null);
  const [rulesVer, setRulesVer] = useState(null);
  const [changes, setChanges] = useState([]);
  const [proposal, setProposal] = useState('');

  const refreshChanges = () => api.ruleChanges().then(setChanges).catch(() => setChanges([]));
  const propose = async () => {
    if (!proposal.trim()) return;
    try { await api.proposeRuleChange(proposal); setProposal(''); refreshChanges(); }
    catch (e) { setError(e.message); }
  };
  const decide = async (id, d) => {
    try { await api.decideRuleChange(id, d); refreshChanges(); }
    catch (e) { setError(e.message); }
  };
  const [simType, setSimType] = useState('capital_expenditure');
  const [simAmount, setSimAmount] = useState(0);
  const [sim, setSim] = useState(null);

  useEffect(() => {
    api.sops().then(setSops).catch(() => setSops([]));
    api.sopCoverage().then(setCoverage).catch(() => setCoverage(null));
    api.decisionTree().then(setTree).catch(() => setTree(null));
    api.rulesVersion().then(setRulesVer).catch(() => setRulesVer(null));
    api.ruleChanges().then(setChanges).catch(() => setChanges([]));
  }, []);

  const simulate = () =>
    api.routingSimulate(simType, simAmount).then(setSim).catch((e) => setError(e.message));

  const fired = new Set(sim?.rules_fired || []);
  const node = (id) => `dam-node ${fired.has(id) ? 'dam-node--fired' : sim ? 'dam-node--dim' : ''}`;
  const rp = (n) => (n == null ? 'no ceiling' : `≤ Rp${(n / 1e9).toLocaleString()} bn`);

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
            {decision.expected_timeline_days != null && (
              <span className="dam-pill dam-pill--info dam-pill--plain">
                ~{decision.expected_timeline_days} business days
              </span>
            )}
          </div>
          {decision.ambiguous && (
            <InlineNotification kind="warning" lowContrast hideCloseButton
              title="Ambiguous routing — escalated to a human resolver"
              subtitle={`No specific SOP confidently applies. Routed to: ${decision.resolver}. Review the fired rules below.`}
              style={{ marginBottom: 'var(--sp-3)' }} />
          )}
          {decision.approval_suppressed && (
            <p className="dam-meta">✓ Unnecessary approval suppressed — value below the delegation threshold.</p>
          )}
          {decision.pre_conditions?.length > 0 && (
            <div style={{ margin: 'var(--sp-3) 0' }}>
              <div className="dam-sop__row" style={{ padding: 0, fontWeight: 600 }}>Pre-conditions to satisfy</div>
              {decision.pre_conditions.map((p) => (
                <div key={p} className="dam-meta" style={{ padding: '2px 0' }}>• {p}</div>
              ))}
            </div>
          )}
          <p style={{ whiteSpace: 'pre-wrap' }}>{decision.explanation}</p>
          <p className="dam-meta">
            SOP v{decision.sop_version} · Rulebook v{decision.rulebook_version} · Rules fired: {decision.rules_fired.map((r) => <code key={r}>{r} </code>)}
            · Trace: <code>{decision.trace_id}</code>
          </p>
        </div>
      )}

      {/* Decision tree + what-if simulator (4.2) */}
      {tree && (
        <>
          <div className="dam-section">
            <h2 className="dam-section__title">Decision tree &amp; what-if</h2>
            <span className="dam-section__meta">Deterministic — the AI never decides this</span>
          </div>
          <div className="dam-card" style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <Select id="sim-type" labelText="Request type" value={simType}
              onChange={(e) => setSimType(e.target.value)} style={{ minWidth: 220 }}>
              {REQUEST_TYPES.map(([v, t]) => <SelectItem key={v} value={v} text={t} />)}
            </Select>
            <NumberInput id="sim-amount" label="Amount (IDR)" value={simAmount}
              onChange={(_, { value }) => setSimAmount(Number(value) || 0)}
              step={1000000000} min={0} />
            <Button kind="tertiary" renderIcon={DecisionTree} onClick={simulate}>Simulate path</Button>
            {sim && (
              <span className="dam-meta">
                → <code>{sim.sop_id}</code> · {sim.approval_required ? sim.approval_level?.replaceAll('_', ' ') : 'no approval'} · {sim.risk_tier} risk
              </span>
            )}
          </div>
          <div className="dam-tree" style={{ marginTop: 'var(--sp-4)' }}>
            <div>
              <div className="dam-lane__title">1 · Applicable SOP</div>
              {tree.sops.map((s) => (
                <div key={s.id} className={node(s.id)}>
                  <code>{s.id}</code> {s.name}
                  {!s.active && <span className="dam-node__sub">{s.status} — does not route</span>}
                </div>
              ))}
            </div>
            <div>
              <div className="dam-lane__title">2 · Approval threshold</div>
              {tree.approval_rules.map((r) => (
                <div key={r.id} className={node(r.id)}>
                  <code>{r.id}</code> {r.approval_required ? (r.approval_level || '').replaceAll('_', ' ') : 'no approval'}
                  <div className="dam-node__sub">{rp(r.max_amount_idr)}</div>
                </div>
              ))}
            </div>
            <div>
              <div className="dam-lane__title">3 · Risk tier</div>
              {tree.risk_rules.map((r) => (
                <div key={r.id} className={node(r.id)}>
                  <code>{r.id}</code> {r.tier} risk
                  <div className="dam-node__sub">{rp(r.max_amount_idr)}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Rule governance — dual-approval (4.4, FR-4/FR-8) */}
      <div className="dam-section">
        <h2 className="dam-section__title">Rule governance</h2>
        {rulesVer && <span className="dam-section__meta">Rulebook v{rulesVer.rulebook_version} · every decision records this</span>}
      </div>
      <div className="dam-card">
        <div style={{ display: 'flex', gap: 'var(--sp-3)', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <TextInput id="proposal" labelText="Propose a rule / threshold change"
            placeholder="e.g. Lower lease approval ceiling to Rp400m"
            value={proposal} onChange={(e) => setProposal(e.target.value)} style={{ minWidth: 320 }} />
          <Button kind="tertiary" onClick={propose} disabled={!proposal.trim()}>Propose change</Button>
        </div>
        <p className="dam-meta" style={{ marginTop: 'var(--sp-2)' }}>
          A change requires a second approver — a proposer can never self-approve.
        </p>
        {changes.map((ch) => (
          <div key={ch.id} className="dam-feed__row">
            <span className={`dam-pill dam-pill--${ch.status === 'approved' ? 'success' : ch.status === 'rejected' ? 'error' : 'warning'} dam-pill--plain`}>{ch.status}</span>
            <div className="dam-feed__text">
              <div className="dam-feed__title">{ch.summary}</div>
              <div className="dam-feed__sub">proposed by {ch.proposed_by}{ch.approved_by ? ` · decided by ${ch.approved_by}` : ''}</div>
            </div>
            {ch.status === 'pending' && (
              <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
                <Button size="sm" kind="ghost" onClick={() => decide(ch.id, 'approved')}>Approve</Button>
                <Button size="sm" kind="ghost" onClick={() => decide(ch.id, 'rejected')}>Reject</Button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* SOP catalogue + coverage (4.1, FR-7) */}
      <div className="dam-section">
        <h2 className="dam-section__title">SOP catalogue</h2>
        {coverage && (
          <span className="dam-section__meta">
            {coverage.served}/{coverage.total} request categories covered by an approved SOP
            · {Math.round(coverage.coverage * 100)}%
          </span>
        )}
      </div>
      <div className="dam-sop-grid">
        {sops.map((s) => {
          const types = !s.request_types ? [] : (Array.isArray(s.request_types) ? s.request_types : [s.request_types]);
          const open = expanded === s.id;
          return (
            <div
              key={s.id}
              className={`dam-sop ${s.status === 'draft' ? 'dam-sop--draft' : ''}`}
              role="button"
              tabIndex={0}
              onClick={() => setExpanded(open ? null : s.id)}
              onKeyDown={(e) => e.key === 'Enter' && setExpanded(open ? null : s.id)}
            >
              <div className="dam-sop__head">
                <span className="dam-sop__id">{s.id}</span>
                <span className={`dam-pill dam-pill--${s.active ? 'success' : s.status === 'draft' ? 'warning' : 'neutral'} dam-pill--plain`}>
                  {s.active ? 'active' : s.status}
                </span>
                <span className="dam-sop__ver">v{s.version}</span>
              </div>
              <div className="dam-sop__name">{s.name}</div>
              <div className="dam-sop__owner">{s.owner}</div>
              {types.length > 0 && (
                <div className="dam-sop__types">
                  {types.map((t) => (
                    <span key={t} className="dam-pill dam-pill--info dam-pill--plain">{t.replaceAll('_', ' ')}</span>
                  ))}
                </div>
              )}
              {open && (
                <div className="dam-sop__detail">
                  <div className="dam-sop__row"><span>Status</span><span>{s.status}{s.active ? '' : s.status === 'approved' ? ' · not yet effective' : ' · will not route'}</span></div>
                  <div className="dam-sop__row"><span>Effective date</span><span>{s.effective_date || '—'}</span></div>
                  <div className="dam-sop__row"><span>Owner</span><span>{s.owner}</span></div>
                  <div className="dam-sop__row"><span>Version</span><span>v{s.version}</span></div>
                  <div className="dam-sop__row"><span>Serves</span><span>{types.length ? types.map((t) => t.replaceAll('_', ' ')).join(', ') : 'fallback (any uncovered request)'}</span></div>
                  <p className="dam-meta" style={{ marginTop: 'var(--sp-2)' }}>
                    Approval level is set by the transaction amount (delegation matrix), not the SOP.
                  </p>
                  {types.length > 0 && (
                    <Button
                      size="sm"
                      kind="tertiary"
                      renderIcon={DecisionTree}
                      onClick={(e) => {
                        e.stopPropagation();
                        set('request_type')(types[0]);
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                      style={{ marginTop: 'var(--sp-2)' }}
                    >
                      Try in simulator
                    </Button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
