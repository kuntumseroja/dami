import { useEffect, useState } from 'react';
import {
  Button,
  Column,
  Grid,
  Modal,
  Tag,
  TextInput,
  Tile,
} from '@carbon/react';
import { Add } from '@carbon/icons-react';
import { api } from '../api';

const STAGE_LABELS = {
  submission: 'Submission',
  evaluation: 'Evaluation',
  board: 'Board',
  decision: 'Decision',
  communication: 'Communication',
  closed: 'Closed',
};

const RISK_TAG = { low: 'green', medium: 'blue', high: 'red' };

export default function Dashboard() {
  const [cases, setCases] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [title, setTitle] = useState('');

  const refresh = () => api.listCases().then(setCases).catch(() => setCases([]));
  useEffect(() => { refresh(); }, []);

  const createCase = async () => {
    if (!title.trim()) return;
    await api.createCase(title.trim());
    setTitle('');
    setModalOpen(false);
    refresh();
  };

  return (
    <div className="dam-page">
      <h1 className="dam-page-title">Governance Dashboard</h1>
      <p className="dam-page-subtitle">
        Submission → evaluation → board → decision → communication. Low-risk cases
        advance automatically; medium and high-risk cases pause at human checkpoints.
      </p>

      <Grid narrow style={{ marginBottom: '2rem' }}>
        <Column lg={4} md={4} sm={4}>
          <Tile className="dam-card dam-card--accent">
            <div className="dam-metric">{cases.length}</div>
            <div className="dam-metric-label">Active cases</div>
          </Tile>
        </Column>
        <Column lg={4} md={4} sm={4}>
          <Tile className="dam-card dam-card--accent">
            <div className="dam-metric">
              {cases.filter((c) => c.risk_tier === 'low').length}
            </div>
            <div className="dam-metric-label">Fully automated (low risk)</div>
          </Tile>
        </Column>
        <Column lg={4} md={4} sm={4}>
          <Tile className="dam-card dam-card--accent">
            <div className="dam-metric">
              {cases.filter((c) => c.stage === 'board').length}
            </div>
            <div className="dam-metric-label">Awaiting board</div>
          </Tile>
        </Column>
        <Column lg={4} md={4} sm={4}>
          <Tile className="dam-card" style={{ display: 'flex', alignItems: 'center' }}>
            <Button renderIcon={Add} onClick={() => setModalOpen(true)}>
              New case
            </Button>
          </Tile>
        </Column>
      </Grid>

      {cases.map((c) => (
        <div key={c.case_id} className="dam-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <strong>{c.title}</strong>
              <div style={{ color: '#525252', fontSize: '0.875rem' }}>
                <code>{c.case_id}</code>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <Tag type={RISK_TAG[c.risk_tier] || 'gray'}>{c.risk_tier} risk</Tag>
              <Tag type="blue">{STAGE_LABELS[c.stage] || c.stage}</Tag>
              <Button
                kind="tertiary"
                size="sm"
                onClick={() =>
                  api
                    .advanceCase(c.case_id, c.risk_tier === 'low' ? null : 'reviewer')
                    .then(refresh)
                    .catch((e) => alert(e.message))
                }
              >
                Advance
              </Button>
            </div>
          </div>
        </div>
      ))}

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
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </Modal>
    </div>
  );
}
