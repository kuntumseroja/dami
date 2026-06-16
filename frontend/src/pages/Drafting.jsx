import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Button,
  FileUploaderDropContainer,
  InlineLoading,
  InlineNotification,
  Select,
  SelectItem,
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
  Edit,
  Checkmark,
  Close,
  Download,
} from '@carbon/icons-react';
import { api } from '../api';

const DRAFT_SLA_MS = 60_000;   // mirrors backend SLA_TARGETS_MS["agent.drafting"]

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
  const [templates, setTemplates] = useState([]);
  const [templateId, setTemplateId] = useState('');   // '' = auto (by SOP)
  const [actions, setActions] = useState({});          // paragraph_id -> action record
  const [editing, setEditing] = useState({});          // paragraph_id -> draft edit text

  const act = async (paragraphId, action, finalContent) => {
    try {
      await api.draftAction(caseId, paragraphId, action, finalContent);
      setActions((m) => ({ ...m, [paragraphId]: { action, final_content: finalContent || '' } }));
      if (action !== 'edit') setEditing((m) => { const n = { ...m }; delete n[paragraphId]; return n; });
    } catch (e) { setError(e.message); }
  };

  useEffect(() => { api.listTemplates().then(setTemplates).catch(() => setTemplates([])); }, []);

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
      setDraft(await api.draft(caseId, instructions || null, templateId || null));
      api.draftActionState(caseId).then(setActions).catch(() => setActions({}));
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
            <span className="dam-meta" style={{ marginLeft: 'auto' }}>
              {checklist.sop ? `Profile: ${checklist.sop}` : 'Default profile (not yet routed)'}
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

        <Select
          id="template"
          labelText="NOTA template"
          value={templateId}
          onChange={(e) => setTemplateId(e.target.value)}
          style={{ marginTop: '1.5rem' }}
        >
          <SelectItem value="" text="Auto — select by SOP" />
          {templates.map((t) => <SelectItem key={t.id} value={t.id} text={t.name} />)}
        </Select>

        <TextArea
          id="instructions"
          labelText="Additional instructions (optional)"
          placeholder="e.g. emphasise the downstreaming rationale; keep tone formal."
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          style={{ margin: '1rem 0' }}
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
          <p className="dam-meta" style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', flexWrap: 'wrap' }}>
            <span>Model: <code>{draft.model}</code></span>
            {draft.template_id && <span>Template: <code>{draft.template_id}</code></span>}
            <span className={`dam-pill dam-pill--${draft.complete ? 'success' : 'error'} dam-pill--plain`}>
              {draft.complete ? 'Mandatory complete' : 'Blocked — mandatory missing'}
            </span>
            {draft.latency_ms != null && (
              <span className={`dam-pill dam-pill--${draft.latency_ms <= DRAFT_SLA_MS ? 'success' : 'warning'} dam-pill--plain`}>
                {(draft.latency_ms / 1000).toFixed(1)}s
                {draft.latency_ms <= DRAFT_SLA_MS ? ' · within SLA' : ' · over SLA'}
              </span>
            )}
            {draft.coverage != null && (
              <span className={`dam-pill dam-pill--${draft.source_sufficient ? 'success' : 'warning'} dam-pill--plain`}>
                {Math.round(draft.coverage * 100)}% source coverage
              </span>
            )}
          </p>
          {draft.disclaimer && (
            <InlineNotification kind="info" lowContrast hideCloseButton
              title="AI-assisted" subtitle={draft.disclaimer}
              style={{ marginBottom: 'var(--sp-4)', maxWidth: '100%' }} />
          )}
          <Button kind="tertiary" size="sm" renderIcon={Download}
            href={api.draftExportUrl(caseId)} target="_blank"
            style={{ marginBottom: 'var(--sp-4)' }}>
            Export reviewed NOTA (.md)
          </Button>
          {draft.mandatory_missing && draft.mandatory_missing.length > 0 && (
            <InlineNotification
              kind="error"
              lowContrast
              title="Mandatory sections unfilled (blocks completion)"
              subtitle={`${draft.mandatory_missing.join(', ')} — sources don't support these; they are flagged, not invented. Attach documents and regenerate.`}
              style={{ marginBottom: 'var(--sp-4)' }}
            />
          )}
          {draft.source_sufficient === false && (
            <InlineNotification
              kind="warning"
              lowContrast
              title="Insufficient source material"
              subtitle={`Sections needing more documents: ${draft.insufficient_sections.join(', ')}. Attach supporting docs above and regenerate.`}
              style={{ marginBottom: 'var(--sp-4)' }}
            />
          )}
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
                  {(() => {
                    const a = actions[s.heading];
                    const isEditing = editing[s.heading] !== undefined;
                    const shown = a?.action === 'edit' ? a.final_content : s.content;
                    if (isEditing) {
                      return (
                        <>
                          <TextArea id={`edit-${s.heading}`} labelText="Edit paragraph"
                            value={editing[s.heading]}
                            onChange={(e) => setEditing((m) => ({ ...m, [s.heading]: e.target.value }))} />
                          <div style={{ display: 'flex', gap: 'var(--sp-2)', marginTop: 'var(--sp-2)' }}>
                            <Button size="sm" renderIcon={Checkmark}
                              onClick={() => act(s.heading, 'edit', editing[s.heading])}>Save edit</Button>
                            <Button size="sm" kind="ghost" renderIcon={Close}
                              onClick={() => setEditing((m) => { const n = { ...m }; delete n[s.heading]; return n; })}>Cancel</Button>
                          </div>
                        </>
                      );
                    }
                    return (
                      <>
                        <p style={{ whiteSpace: 'pre-wrap', opacity: a?.action === 'reject' ? 0.45 : 1,
                          textDecoration: a?.action === 'reject' ? 'line-through' : 'none' }}>{shown}</p>
                        {s.sources.length > 0 && (
                          <p className="dam-meta">Sources: {s.sources.map((src) => <code key={src}>{src} </code>)}</p>
                        )}
                        <div style={{ display: 'flex', gap: 'var(--sp-2)', alignItems: 'center' }}>
                          <Button size="sm" kind={a?.action === 'accept' ? 'primary' : 'ghost'}
                            renderIcon={CheckmarkFilled} onClick={() => act(s.heading, 'accept', s.content)}>Accept</Button>
                          <Button size="sm" kind="ghost" renderIcon={Edit}
                            onClick={() => setEditing((m) => ({ ...m, [s.heading]: shown }))}>Edit</Button>
                          <Button size="sm" kind="ghost" renderIcon={TrashCan}
                            onClick={() => act(s.heading, 'reject', '')}>Reject</Button>
                          {a && <span className={`dam-pill dam-pill--${a.action === 'reject' ? 'error' : a.action === 'edit' ? 'warning' : 'success'} dam-pill--plain`}>{a.action}ed</span>}
                        </div>
                      </>
                    );
                  })()}
                </>
              ) : (() => {
                const a = actions[s.heading];
                const isEditing = editing[s.heading] !== undefined;
                if (isEditing) {
                  return (
                    <>
                      <TextArea id={`jedit-${s.heading}`} labelText="Your analysis (human-authored)"
                        value={editing[s.heading]}
                        onChange={(e) => setEditing((m) => ({ ...m, [s.heading]: e.target.value }))} />
                      <div style={{ display: 'flex', gap: 'var(--sp-2)', marginTop: 'var(--sp-2)' }}>
                        <Button size="sm" renderIcon={Checkmark}
                          onClick={() => act(s.heading, 'edit', editing[s.heading])}>Save</Button>
                        <Button size="sm" kind="ghost" renderIcon={Close}
                          onClick={() => setEditing((m) => { const n = { ...m }; delete n[s.heading]; return n; })}>Cancel</Button>
                      </div>
                    </>
                  );
                }
                return (
                  <div className="dam-section-judgment">
                    {a?.action === 'edit' && a.final_content
                      ? <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{a.final_content}</p>
                      : <p style={{ margin: 0 }}>✍️ Analysis &amp; recommendation must be authored by a human reviewer — the AI never fills this section.</p>}
                    <Button size="sm" kind="ghost" renderIcon={Edit} style={{ marginTop: 'var(--sp-2)' }}
                      onClick={() => setEditing((m) => ({ ...m, [s.heading]: a?.final_content || '' }))}>
                      {a?.final_content ? 'Edit analysis' : 'Write analysis'}
                    </Button>
                  </div>
                );
              })()}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
