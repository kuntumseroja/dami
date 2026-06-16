import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Button,
  FileUploaderDropContainer,
  InlineLoading,
  InlineNotification,
  TextArea,
  TextInput,
} from '@carbon/react';
import {
  MachineLearningModel,
  Document,
  DocumentAdd,
  View,
  ViewOff,
  TrashCan,
  Locked,
  CheckmarkFilled,
  WarningAltFilled,
  Subtract,
} from '@carbon/icons-react';
import { api } from '../api';

const STAGE_LABELS = {
  submission_intake: 'Submission Intake', eligibility_check: 'Eligibility Check',
  nota_drafting: 'NOTA Drafting', internal_review: 'Internal Review',
  board_preparation: 'Board Preparation', decision: 'Decision',
  communication_dispatch: 'Communication Dispatch', closed: 'Closed',
};
const DOCTYPE_LABELS = {
  cover_sheet: 'Cover sheet', submission: 'Submission', supporting: 'Supporting',
  review_note: 'Review note', board_note: 'Board note',
  decision: 'Decision', communication: 'Communication',
};

export default function Drafting() {
  const { caseId: routeCaseId } = useParams();
  const [caseId, setCaseId] = useState(routeCaseId || '');
  const [caseInfo, setCaseInfo] = useState(null);
  const [docs, setDocs] = useState([]);
  const [checklist, setChecklist] = useState(null);
  const [instructions, setInstructions] = useState('');
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [previewId, setPreviewId] = useState(null);

  // Refresh the document list + the auto-reconciled completeness checklist.
  const refreshDocs = (id = caseId) => {
    if (!id) return;
    api.listDocuments(id).then(setDocs).catch(() => setDocs([]));
    api.checklist(id).then(setChecklist).catch(() => setChecklist(null));
  };

  // When opened from an active process, load the case + its already-attached
  // submission documents from the SOE.
  const loadCase = (id) => {
    if (!id) return;
    api.getCase(id).then(setCaseInfo).catch(() => setCaseInfo(null));
    refreshDocs(id);
  };
  useEffect(() => {
    if (routeCaseId) { setCaseId(routeCaseId); loadCase(routeCaseId); }
  }, [routeCaseId]);

  // Analyst additions are 'supporting' (non-master) → removable, unlike the
  // SOE submission package which is locked.
  const attachMore = async (files) => {
    if (!files.length || !caseId) return;
    setUploading(true);
    setError(null);
    try {
      for (const f of files) await api.ingest(f, 'supporting', caseId);
      refreshDocs(caseId);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const removeDoc = async (doc) => {
    if (!window.confirm(`Remove "${doc.title}" from this case?`)) return;
    setError(null);
    try {
      await api.deleteDocument(caseId, doc.id);
      if (previewId === doc.id) setPreviewId(null);
      refreshDocs(caseId);
    } catch (e) {
      setError(e.message);
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

      {/* Case context — present when launched from an active process */}
      {caseInfo && (
        <div className="dam-casebar">
          <div>
            <div className="dam-casebar__title">{caseInfo.title}</div>
            <div className="dam-casebar__meta">
              <code>{caseInfo.case_id}</code> · {caseInfo.entity || 'DAM'} ·{' '}
              {STAGE_LABELS[caseInfo.stage] || caseInfo.stage}
            </div>
          </div>
          <span className="dam-casebar__spacer" />
          <span className="dam-pill dam-pill--info dam-pill--plain">
            {docs.length} document{docs.length === 1 ? '' : 's'} attached
          </span>
        </div>
      )}

      {/* Auto-reconciled completeness checklist — reflects the docs actually
          attached, not a static field on the cover sheet. */}
      {checklist && (
        <div className="dam-card">
          <h3 className="dam-subhead" style={{ marginTop: 0 }}>
            Completeness checklist
            <span className={`dam-pill dam-pill--${checklist.complete ? 'success' : 'warning'}`}>
              {checklist.complete ? 'Complete' : `${checklist.missing.length} missing`}
            </span>
          </h3>
          {checklist.items.map((it) => {
            const state = it.present ? 'ok' : it.required ? 'missing' : 'optional';
            const Icon = state === 'ok' ? CheckmarkFilled
              : state === 'missing' ? WarningAltFilled : Subtract;
            return (
              <div className={`dam-check dam-check--${state}`} key={it.key}>
                <Icon size={18} className="dam-check__icon" />
                <span className="dam-check__label">{it.label}</span>
                {!it.required && <span className="dam-check__opt">recommended</span>}
                <span className="dam-check__status">
                  {it.present ? (it.matched[0] || 'present') : it.required ? 'Required — missing' : 'Not provided'}
                </span>
              </div>
            );
          })}
        </div>
      )}

      <div className="dam-card">
        {!routeCaseId && (
          <TextInput
            id="case-id"
            labelText="Case ID"
            placeholder="case_xxxxxxxxxx"
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            onBlur={(e) => loadCase(e.target.value.trim())}
            style={{ marginBottom: '1rem' }}
          />
        )}

        {/* Documents already attached from the SOE submission */}
        {docs.length > 0 && (
          <>
            <h3 className="dam-subhead">
              <Document size={16} /> Documents from submission
            </h3>
            {docs.map((d) => (
              <div key={d.id}>
                <div className="dam-doc">
                  <span className="dam-doc__icon"><Document size={18} /></span>
                  <div>
                    <div className="dam-doc__name">{d.title}</div>
                    <div className="dam-doc__meta">
                      <code>{d.id}</code>
                      {d.is_master && ' · master'}
                    </div>
                  </div>
                  <div className="dam-doc__tags">
                    <span className="dam-pill dam-pill--neutral dam-pill--plain">
                      {DOCTYPE_LABELS[d.doc_type] || d.doc_type}
                    </span>
                    {d.classification && (
                      <span className="dam-pill dam-pill--warning dam-pill--plain">
                        {d.classification}
                      </span>
                    )}
                    <Button
                      kind="ghost"
                      size="sm"
                      hasIconOnly
                      iconDescription={previewId === d.id ? 'Hide preview' : 'Preview'}
                      tooltipPosition="bottom"
                      renderIcon={previewId === d.id ? ViewOff : View}
                      onClick={() => setPreviewId(previewId === d.id ? null : d.id)}
                    />
                    {d.is_master ? (
                      <Button
                        kind="ghost"
                        size="sm"
                        hasIconOnly
                        disabled
                        iconDescription="SOE submission — locked"
                        tooltipPosition="bottom"
                        renderIcon={Locked}
                      />
                    ) : (
                      <Button
                        kind="ghost"
                        size="sm"
                        hasIconOnly
                        iconDescription="Remove"
                        tooltipPosition="bottom"
                        renderIcon={TrashCan}
                        onClick={() => removeDoc(d)}
                      />
                    )}
                  </div>
                </div>
                {previewId === d.id && (
                  <iframe
                    title={`preview-${d.id}`}
                    src={api.documentFileUrl(d.id)}
                    className="dam-doc-preview"
                  />
                )}
              </div>
            ))}
          </>
        )}

        {/* Analyst can still attach more source material */}
        <h3 className="dam-subhead" style={{ marginTop: 'var(--sp-5)' }}>
          <DocumentAdd size={16} /> Attach more documents <span className="dam-meta">(optional)</span>
        </h3>
        {uploading ? (
          <InlineLoading description="Uploading & indexing…" />
        ) : (
          <FileUploaderDropContainer
            labelText="Drag and drop additional PDF / DOCX here, or click to upload"
            accept={['.pdf', '.docx', '.txt']}
            multiple
            disabled={!caseId}
            onAddFiles={(_, { addedFiles }) => attachMore(addedFiles)}
          />
        )}

        <TextArea
          id="instructions"
          labelText="Additional instructions (optional)"
          placeholder="e.g. emphasise the downstreaming rationale; keep tone formal."
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          style={{ margin: '1.5rem 0 1rem' }}
        />
        {busy ? (
          <InlineLoading description="Drafting NOTA from sources…" />
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
