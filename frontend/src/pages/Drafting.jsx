import { useState } from 'react';
import {
  Button,
  FileUploaderDropContainer,
  InlineLoading,
  InlineNotification,
  TextArea,
  TextInput,
} from '@carbon/react';
import { MachineLearningModel } from '@carbon/icons-react';
import { api } from '../api';

export default function Drafting() {
  const [caseId, setCaseId] = useState('');
  const [instructions, setInstructions] = useState('');
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const uploadSubmission = async (files) => {
    if (!files.length || !caseId) return;
    setBusy(true);
    setError(null);
    try {
      await api.ingest(files[0], 'submission', caseId);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      setDraft(await api.draft(caseId, instructions || null));
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
          <h1 className="dam-page-title">AI-Assisted NOTA Drafting</h1>
          <p className="dam-page-subtitle">
            The drafting agent generates the descriptive 80% of a NOTA from submission
            documents, templates, and historical notes. Judgment sections stay empty —
            analysis and recommendations remain yours.
          </p>
        </div>
      </div>

      {error && (
        <InlineNotification kind="error" title="Error" subtitle={error} lowContrast />
      )}

      <div className="dam-card">
        <TextInput
          id="case-id"
          labelText="Case ID"
          placeholder="case_xxxxxxxxxx"
          value={caseId}
          onChange={(e) => setCaseId(e.target.value)}
          style={{ marginBottom: '1rem' }}
        />
        <p style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>
          Upload submission documents (PDF / DOCX)
        </p>
        <FileUploaderDropContainer
          labelText="Drag and drop files here, or click to upload"
          accept={['.pdf', '.docx', '.txt']}
          onAddFiles={(_, { addedFiles }) => uploadSubmission(addedFiles)}
        />
        <TextArea
          id="instructions"
          labelText="Additional instructions (optional)"
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          style={{ margin: '1rem 0' }}
        />
        {busy ? (
          <InlineLoading description="Working…" />
        ) : (
          <Button renderIcon={MachineLearningModel} onClick={generate} disabled={!caseId}>
            Generate first draft
          </Button>
        )}
      </div>

      {draft && (
        <div className="dam-card dam-card--accent">
          <h2 style={{ fontWeight: 300, marginTop: 0 }}>{draft.title}</h2>
          <p className="dam-meta">
            Model: <code>{draft.model}</code> · Trace: <code>{draft.trace_id}</code>
          </p>
          {draft.sections.map((s) => (
            <div key={s.heading} style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ fontWeight: 400, fontSize: '1.125rem', display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
                {s.heading}
                <span className={`dam-pill dam-pill--${s.kind === 'descriptive' ? 'info' : 'neutral'} dam-pill--plain`}>
                  {s.kind === 'descriptive' ? 'AI draft' : 'human judgment'}
                </span>
              </h3>
              {s.kind === 'descriptive' ? (
                <>
                  <p style={{ whiteSpace: 'pre-wrap' }}>{s.content}</p>
                  {s.sources.length > 0 && (
                    <p className="dam-meta">
                      Sources: {s.sources.map((src) => <code key={src}>{src} </code>)}
                    </p>
                  )}
                </>
              ) : (
                <div className="dam-section-judgment">
                  Reserved for reviewer analysis and recommendation.
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
