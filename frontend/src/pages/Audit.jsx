import { useEffect, useState } from 'react';
import {
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  Tag,
} from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import { api } from '../api';

const EVENT_TAG = {
  'agent.drafting': 'blue',
  'agent.consistency': 'teal',
  'agent.routing': 'purple',
  'agent.extraction': 'cyan',
  'document.ingested': 'gray',
  'workflow.advanced': 'green',
};

export default function Audit() {
  const [records, setRecords] = useState([]);

  const refresh = () => api.audit().then(setRecords).catch(() => setRecords([]));
  useEffect(() => { refresh(); }, []);

  return (
    <div className="dam-page" style={{ maxWidth: '1312px' }}>
      <h1 className="dam-page-title">Audit Trail &amp; Explainability</h1>
      <p className="dam-page-subtitle">
        Every AI invocation, rule evaluation, and workflow transition is recorded
        append-only. Any output can be traced back to its sources, fired rules, and
        sign-offs — no individual carries unrecorded liability.
      </p>

      <Button kind="tertiary" size="sm" renderIcon={Renew} onClick={refresh} style={{ marginBottom: '1rem' }}>
        Refresh
      </Button>

      <TableContainer className="dam-card" style={{ padding: 0 }}>
        <Table size="md">
          <TableHead>
            <TableRow>
              <TableHeader>Time (UTC)</TableHeader>
              <TableHeader>Event</TableHeader>
              <TableHeader>Trace</TableHeader>
              <TableHeader>Case</TableHeader>
              <TableHeader>Detail</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {records.map((r, i) => (
              <TableRow key={i}>
                <TableCell>{r.ts?.slice(0, 19).replace('T', ' ')}</TableCell>
                <TableCell>
                  <Tag type={EVENT_TAG[r.event] || 'cool-gray'}>{r.event}</Tag>
                </TableCell>
                <TableCell><code>{r.trace_id}</code></TableCell>
                <TableCell><code>{r.case_id || '—'}</code></TableCell>
                <TableCell style={{ fontSize: '0.75rem', color: '#525252' }}>
                  {r.rules_fired?.join(', ') ||
                    r.sources?.length != null && `${r.sources.length} sources` ||
                    r.filename ||
                    (r.to && `→ ${r.to}`) ||
                    ''}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  );
}
