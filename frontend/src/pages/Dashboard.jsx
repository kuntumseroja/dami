import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Modal, TextInput } from '@carbon/react';
import {
  Add,
  WarningAltFilled,
  InformationFilled,
  Document,
  DocumentTasks,
  Compare,
  DecisionTree,
  CheckmarkFilled,
  ArrowRight,
} from '@carbon/icons-react';
import { api } from '../api';

// Workflow lifecycle in order; index drives the progress dots.
const STAGES = ['submission', 'evaluation', 'board', 'decision', 'communication', 'closed'];
const STAGE_LABELS = {
  submission: 'Submission',
  evaluation: 'Evaluation',
  board: 'Board',
  decision: 'Decision',
  communication: 'Communication',
  closed: 'Closed',
};

// Risk tier → who must sign off at a human checkpoint.
const CHECKPOINT = {
  medium: { role: 'reviewer', pill: 'info', label: 'Needs reviewer' },
  high: { role: 'approver', pill: 'error', label: 'Needs approver' },
};

function statusOf(c) {
  if (c.stage === 'closed') return { pill: 'neutral', label: 'Closed' };
  if (c.risk_tier === 'low') return { pill: 'success', label: 'Auto-advancing' };
  const cp = CHECKPOINT[c.risk_tier] || { pill: 'info', label: 'In review' };
  return { pill: cp.pill, label: cp.label };
}

// Friendly recent-activity rendering keyed by audit event name.
const EVENT_META = {
  'agent.drafting': { icon: DocumentTasks, label: 'NOTA drafted' },
  'agent.draft': { icon: DocumentTasks, label: 'NOTA drafted' },
  'agent.consistency': { icon: Compare, label: 'Consistency check' },
  'agent.routing': { icon: DecisionTree, label: 'Request routed' },
  'agent.route': { icon: DecisionTree, label: 'Request routed' },
  'agent.extraction': { icon: Document, label: 'Fields extracted' },
  'document.ingested': { icon: Document, label: 'Document ingested' },
  'workflow.advanced': { icon: CheckmarkFilled, label: 'Stage advanced' },
  'workflow.case_created': { icon: Add, label: 'Case created' },
  'workflow.risk_tier_set': { icon: DecisionTree, label: 'Risk tier set' },
  'orchestrator.pipeline_completed': { icon: CheckmarkFilled, label: 'Pipeline completed' },
};

// Humanize any unmapped audit event ("a.b_c" → "B c").
function prettyEvent(ev) {
  const tail = String(ev).split('.').pop().replace(/_/g, ' ');
  return tail.charAt(0).toUpperCase() + tail.slice(1);
}

function timeAgo(ts) {
  if (!ts) return '';
  const then = new Date(ts).getTime();
  if (Number.isNaN(then)) return '';
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

const today = new Intl.DateTimeFormat('en-US', {
  weekday: 'long', month: 'long', day: 'numeric',
}).format(new Date());

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [activity, setActivity] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [title, setTitle] = useState('');
  const navigate = useNavigate();

  const refresh = () => {
    api.listCases().then(setCases).catch(() => setCases([]));
    api.audit(8).then(setActivity).catch(() => setActivity([]));
  };
  useEffect(() => { refresh(); }, []);

  const createCase = async () => {
    if (!title.trim()) return;
    await api.createCase(title.trim());
    setTitle('');
    setModalOpen(false);
    refresh();
  };

  const advance = (c) =>
    api
      .advanceCase(c.case_id, c.risk_tier === 'low' ? null : CHECKPOINT[c.risk_tier]?.role)
      .then(refresh)
      .catch((e) => alert(e.message));

  const open = cases.filter((c) => c.stage !== 'closed');
  // "Needs attention" = genuinely blocked at a human checkpoint, i.e. already
  // past intake (stage beyond submission) and not auto-advancing (low risk).
  // A freshly-submitted case isn't paused yet — it lives in Active processes.
  const attention = open.filter(
    (c) => c.stage !== 'submission' && (c.risk_tier === 'medium' || c.risk_tier === 'high'),
  );

  return (
    <div className="dam-page">
      <div className="dam-page-header">
        <div>
          <h1 className="dam-page-title">Governance Dashboard</h1>
          <p className="dam-page-subtitle">
            Low-risk cases advance automatically; medium and high-risk cases pause
            at human checkpoints for sign-off.
          </p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 'var(--sp-3)' }}>
          <span className="dam-page-date">{today}</span>
          <Button renderIcon={Add} onClick={() => setModalOpen(true)}>New case</Button>
        </div>
      </div>

      {/* Needs attention */}
      {attention.length > 0 && (
        <>
          <div className="dam-section">
            <h2 className="dam-section__title">Needs attention</h2>
            <span className="dam-section__meta">
              {attention.length} case{attention.length > 1 ? 's' : ''} paused at a checkpoint
            </span>
          </div>
          {attention.map((c) => {
            const critical = c.risk_tier === 'high';
            return (
              <div key={c.case_id} className={`dam-alert ${critical ? 'dam-alert--critical' : ''}`}>
                <span className="dam-alert__icon">
                  {critical ? <WarningAltFilled size={20} /> : <InformationFilled size={20} />}
                </span>
                <div className="dam-alert__body">
                  <div className="dam-alert__title">{c.title}</div>
                  <div className="dam-alert__detail">
                    Paused at {STAGE_LABELS[c.stage] || c.stage} — {CHECKPOINT[c.risk_tier]?.label.toLowerCase()} sign-off · {c.risk_tier} risk
                  </div>
                </div>
                <Button kind="tertiary" size="md" onClick={() => advance(c)}>Review</Button>
              </div>
            );
          })}
        </>
      )}

      {/* Active processes */}
      <div className="dam-section">
        <h2 className="dam-section__title">Active processes</h2>
        <span className="dam-section__meta">{open.length} open</span>
      </div>

      {open.length === 0 ? (
        <div className="dam-card dam-empty">
          No active processes yet. Create a case to start a governance workflow.
        </div>
      ) : (
        <div className="dam-process-grid">
          {open.map((c) => {
            const status = statusOf(c);
            const idx = Math.max(0, STAGES.indexOf(c.stage));
            return (
              <div
                key={c.case_id}
                className="dam-process"
                role="button"
                tabIndex={0}
                onClick={() => navigate('/drafting')}
                onKeyDown={(e) => e.key === 'Enter' && navigate('/drafting')}
              >
                <div className="dam-stack" aria-hidden="true">
                  <span className="dam-stack__sheet" />
                  <span className="dam-stack__sheet" />
                  <span className="dam-stack__sheet"><Document size={20} /></span>
                </div>
                <div className="dam-process__title">{c.title}</div>
                <div className="dam-process__sub">
                  {(c.entity || 'DAM')} · {STAGE_LABELS[c.stage] || c.stage}
                </div>
                <div className="dam-dots" aria-label={`stage ${idx + 1} of ${STAGES.length}`}>
                  {STAGES.map((s, i) => (
                    <span
                      key={s}
                      className={`dam-dots__dot ${
                        i < idx ? 'dam-dots__dot--done' : i === idx ? 'dam-dots__dot--current' : ''
                      }`}
                    />
                  ))}
                </div>
                <span className={`dam-pill dam-pill--${status.pill}`}>{status.label}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Recent activity + portfolio panel */}
      <div className="dam-split" style={{ marginTop: 'var(--sp-6)' }}>
        <div>
          <div className="dam-section" style={{ marginTop: 0 }}>
            <h2 className="dam-section__title">Recent activity</h2>
          </div>
          <div className="dam-card" style={{ paddingTop: 'var(--sp-2)', paddingBottom: 'var(--sp-2)' }}>
            {activity.length === 0 ? (
              <div className="dam-empty" style={{ padding: 'var(--sp-5)' }}>No activity recorded yet.</div>
            ) : (
              activity.map((r, i) => {
                const meta = EVENT_META[r.event] || { icon: Document, label: prettyEvent(r.event) };
                const Icon = meta.icon;
                return (
                  <div className="dam-feed__row" key={i}>
                    <span className="dam-feed__icon"><Icon size={16} /></span>
                    <div className="dam-feed__text">
                      <div className="dam-feed__title">{meta.label}</div>
                      <div className="dam-feed__sub">
                        {r.case_id ? <code>{r.case_id}</code> : 'system'}
                      </div>
                    </div>
                    <span className="dam-feed__time">{timeAgo(r.ts)}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div>
          <div className="dam-section" style={{ marginTop: 0 }}>
            <h2 className="dam-section__title">Portfolio</h2>
          </div>
          <div className="dam-card">
            <div className="dam-stat">
              <span className="dam-stat__label">Active processes</span>
              <span className="dam-stat__value">{open.length}</span>
            </div>
            <div className="dam-stat">
              <span className="dam-stat__label">Auto-advancing (low risk)</span>
              <span className="dam-stat__value">{open.filter((c) => c.risk_tier === 'low').length}</span>
            </div>
            <div className="dam-stat">
              <span className="dam-stat__label">Awaiting sign-off</span>
              <span className="dam-stat__value">{attention.length}</span>
            </div>
            <div className="dam-stat">
              <span className="dam-stat__label">High risk</span>
              <span className="dam-stat__value">{open.filter((c) => c.risk_tier === 'high').length}</span>
            </div>
            <div className="dam-stat">
              <span className="dam-stat__label">Closed</span>
              <span className="dam-stat__value">{cases.length - open.length}</span>
            </div>
          </div>
          <Button
            kind="ghost"
            size="sm"
            renderIcon={ArrowRight}
            onClick={() => navigate('/audit')}
            style={{ marginTop: 'var(--sp-2)' }}
          >
            View full audit trail
          </Button>
        </div>
      </div>

      <Modal
        open={modalOpen}
        modalHeading="Create governance case"
        primaryButtonText="Create"
        secondaryButtonText="Cancel"
        onRequestClose={() => setModalOpen(false)}
        onRequestSubmit={createCase}
      >
        <TextInput
          id="case-title"
          labelText="Case title"
          placeholder="e.g. PTPN III — Divestasi Kebun Sei Meranti"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </Modal>
    </div>
  );
}
