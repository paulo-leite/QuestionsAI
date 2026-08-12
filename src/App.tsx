import { type ChangeEvent, type DragEvent, type FormEvent, useEffect, useRef, useState } from 'react'
import './App.css'

type Source = {
  page: number | null
  row_start: number | null
  row_end: number | null
  excerpt: string
}

type UploadedDocument = {
  document_id: string
  filename: string
  file_type: 'pdf' | 'csv'
  pages: number | null
  rows: number | null
  chunks: number
  chunking_method: string
  max_tokens_per_chunk: number
  minimum_chunk_tokens: number
  average_chunk_tokens: number
  maximum_chunk_tokens: number
  average_chunk_characters: number
}

type Answer = { answer: string; sources: Source[] }

type ResearchFinding = {
  subquestion: string
  answer: string
  sources: Source[]
  evidence_count: number
  error?: string | null
}

type ReportData = {
  short_summary: string
  markdown_report: string
  follow_up_questions: string[]
}

type SufficiencyResult = {
  is_sufficient: boolean
  reason: string
  missing_information: string[]
}

type ResearchReview = {
  unsupported_subquestions: string[]
  conflicting_subquestions: string[]
  follow_up_questions: string[]
}

type ResearchResult = {
  answer: string
  findings: ResearchFinding[]
  review: ResearchReview
  sources: Source[]
  rounds_completed: number
  sufficiency_check: SufficiencyResult
}

type ResearchSession = {
  session_id: string
  document_id: string
  original_query: string
  depth: number
  status: 'pending' | 'awaiting_clarification' | 'researching' | 'completed'
  clarification_questions?: string[]
  clarification_responses?: string[]
  report_data: ReportData | null
  findings: ResearchFinding[]
  sources: Source[]
  rounds_completed: number
  sufficiency_check: SufficiencyResult | null
}

type QueryMode = 'question' | 'research_direct' | 'research_guided'

const apiUrl = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

const readApiError = async (response: Response) => {
  const body = await response.json().catch(() => null)
  return body?.detail || 'Não foi possível concluir a solicitação. Tente novamente.'
}

const requestJson = async <T,>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${apiUrl}${path}`, init)
  if (!response.ok) throw new Error(await readApiError(response))
  return response.json() as Promise<T>
}

function App() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isDark, setIsDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches)
  const [file, setFile] = useState<File | null>(null)
  const [document, setDocument] = useState<UploadedDocument | null>(null)
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<QueryMode>('question')
  const [depth, setDepth] = useState(2)
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [directResearch, setDirectResearch] = useState<ResearchResult | null>(null)
  const [researchSession, setResearchSession] = useState<ResearchSession | null>(null)
  const [clarificationAnswer, setClarificationAnswer] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    window.document.documentElement.classList.toggle('dark-mode', isDark)
  }, [isDark])

  const clearResult = () => {
    setAnswer(null)
    setDirectResearch(null)
    setResearchSession(null)
    setClarificationAnswer('')
  }

  const selectFile = (selectedFile?: File) => {
    setError('')
    clearResult()
    setDocument(null)
    if (!selectedFile) return
    const extension = selectedFile.name.toLowerCase().split('.').pop()
    if (extension !== 'pdf' && extension !== 'csv') {
      setFile(null)
      setError('Escolha um arquivo em formato PDF ou CSV.')
      return
    }
    if (selectedFile.size > 20 * 1024 * 1024) {
      setFile(null)
      setError('O arquivo deve ter no máximo 20 MB.')
      return
    }
    setFile(selectedFile)
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => selectFile(event.target.files?.[0])
  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    selectFile(event.dataTransfer.files[0])
  }

  const uploadDocument = async () => {
    if (!file) return
    setIsUploading(true)
    setError('')
    const formData = new FormData()
    formData.append('file', file)
    try {
      setDocument(await requestJson<UploadedDocument>('/documents', { method: 'POST', body: formData }))
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Falha ao enviar o arquivo.')
    } finally {
      setIsUploading(false)
    }
  }

  const submitQuery = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!document || question.trim().length < 3) return
    setIsAsking(true)
    setError('')
    clearResult()
    try {
      const request = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: document.document_id, question: question.trim(), ...(mode !== 'question' ? { depth } : {}) }),
      }
      if (mode === 'research_guided') {
        setResearchSession(await requestJson<ResearchSession>('/research/sessions', request))
      } else if (mode === 'research_direct') {
        setDirectResearch(await requestJson<ResearchResult>('/research', request))
      } else {
        setAnswer(await requestJson<Answer>('/questions', request))
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Não foi possível obter a resposta.')
    } finally {
      setIsAsking(false)
    }
  }

  const submitClarification = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!researchSession || !clarificationAnswer.trim()) return
    setIsAsking(true)
    setError('')
    try {
      const updatedSession = await requestJson<ResearchSession>(
        `/research/sessions/${researchSession.session_id}/clarifications`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ answer: clarificationAnswer.trim() }),
        },
      )
      setResearchSession(updatedSession)
      setClarificationAnswer('')
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Não foi possível enviar o esclarecimento.')
    } finally {
      setIsAsking(false)
    }
  }
  useEffect(() => {
    if (researchSession?.status !== 'researching') return
    const timer = window.setInterval(async () => {
      try {
        const updatedSession = await requestJson<ResearchSession>(`/research/sessions/${researchSession.session_id}`)
        setResearchSession(updatedSession)
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : 'Não foi possível atualizar a pesquisa.')
        window.clearInterval(timer)
      }
    }, 2000)
    return () => window.clearInterval(timer)
  }, [researchSession?.session_id, researchSession?.status])

  const resetDocument = () => {
    setFile(null)
    setDocument(null)
    clearResult()
    setQuestion('')
    setError('')
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const renderSources = (sources: Source[]) => sources.length > 0 && (
    <div className="sources">
      <h3>Trechos consultados</h3>
      {sources.map((source, index) => {
        const location = source.row_start !== null
          ? source.row_start === (source.row_end ?? source.row_start) ? `Linha ${source.row_start}` : `Linhas ${source.row_start}–${source.row_end}`
          : `Pág. ${source.page}`
        return <article className="source" key={`${location}-${index}`}><span>{location}</span><p>{source.excerpt}</p></article>
      })}
    </div>
  )

  const renderSufficiency = (sufficiency: SufficiencyResult | null) => sufficiency && (
    <div className={`sufficiency ${sufficiency.is_sufficient ? 'is-sufficient' : 'has-gaps'}`}>
      <div className="sufficiency-heading">
        <strong>{sufficiency.is_sufficient ? 'Evidências suficientes' : 'Pesquisa com lacunas'}</strong>
        <span>{sufficiency.is_sufficient ? 'Verificada' : 'Revisar'}</span>
      </div>
      <p>{sufficiency.reason}</p>
      {sufficiency.missing_information.length > 0 && <div className="missing-information"><small>Informações ainda necessárias</small><ul>{sufficiency.missing_information.map((item) => <li key={item}>{item}</li>)}</ul></div>}
    </div>
  )

  const renderResearch = ({
    label,
    answer: researchAnswer,
    findings,
    sources,
    rounds,
    followUps,
    sufficiency,
  }: {
    label: string
    answer: string
    findings: ResearchFinding[]
    sources: Source[]
    rounds: number
    followUps: string[]
    sufficiency: SufficiencyResult | null
  }) => (
    <section className="answer-card research-card" aria-live="polite">
      <p className="answer-label">{label} · {rounds} {rounds === 1 ? 'RODADA' : 'RODADAS'}</p>
      <p className="answer-text">{researchAnswer}</p>
      {renderSufficiency(sufficiency)}
      {findings.length > 0 && <div className="findings"><h3>Achados da pesquisa</h3>{findings.map((finding, index) => <article className="finding" key={`${finding.subquestion}-${index}`}><strong>{finding.subquestion}</strong><p>{finding.answer}</p><small>{finding.error ? finding.error : `${finding.evidence_count} ${finding.evidence_count === 1 ? 'evidência encontrada' : 'evidências encontradas'}`}</small></article>)}</div>}
      {followUps.length > 0 && <div className="review"><h3>Pontos a investigar</h3>{followUps.map((item) => <p key={item}>{item}</p>)}</div>}
      {renderSources(sources)}
    </section>
  )

  const clarificationQuestions = researchSession?.clarification_questions ?? []
  const clarificationIndex = researchSession?.clarification_responses?.length ?? 0
  const currentClarification = clarificationQuestions[clarificationIndex]
  const processedUnits = document?.file_type === 'csv'
    ? `${document.rows ?? 0} ${(document.rows ?? 0) === 1 ? 'linha processada' : 'linhas processadas'}`
    : `${document?.pages ?? 0} ${(document?.pages ?? 0) === 1 ? 'página processada' : 'páginas processadas'}`

  return (
    <main className="app-shell">
      <header className="hero">
        <button className={`theme-toggle ${isDark ? 'is-dark' : ''}`} type="button" role="switch" aria-checked={isDark} onClick={() => setIsDark((current) => !current)} aria-label={isDark ? 'Ativar modo claro' : 'Ativar modo escuro'}>
          <span className="theme-icon" aria-hidden="true">☀</span><span className="switch-thumb" aria-hidden="true" /><span className="theme-icon" aria-hidden="true">☾</span>
        </button>
        <div className="brand-mark" aria-hidden="true">✦</div>
        <p className="eyebrow">LEITOR INTELIGENTE</p>
        <h1>Converse com seu documento</h1>
        <p className="subtitle">Envie um PDF ou CSV e obtenha respostas baseadas exclusivamente no conteúdo dele.</p>
      </header>

      <section className="workspace" aria-label="Consulta de documento">
        <div className="step-heading"><span>1</span><div><h2>Envie seu arquivo</h2><p>PDF ou CSV de até 20 MB</p></div></div>
        {!document ? <>
          <div className={`drop-zone ${file ? 'has-file' : ''}`} onDragOver={(event) => event.preventDefault()} onDrop={handleDrop}>
            <input ref={fileInputRef} id="document-upload" type="file" accept=".pdf,.csv,application/pdf,text/csv" onChange={handleFileChange} />
            <div className="file-icon" aria-hidden="true">⌁</div>
            {file ? <div className="selected-file"><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB</span></div> : <><strong>Arraste o PDF ou CSV aqui</strong><span>ou</span></>}
            <label htmlFor="document-upload" className="secondary-button">Selecionar arquivo</label>
          </div>
          {file && <button className="primary-button upload-button" type="button" onClick={uploadDocument} disabled={isUploading}>{isUploading ? 'Preparando documento…' : 'Enviar e preparar'}</button>}
        </> : <div className="document-ready"><div className="ready-icon" aria-hidden="true">✓</div><div><strong>{document.filename}</strong><p>{processedUnits} · {document.chunks} trechos prontos</p></div><button className="text-button" type="button" onClick={resetDocument}>Trocar</button></div>}
        {error && <p className="error-message" role="alert">{error}</p>}

        <div className={`question-section ${document ? 'is-ready' : ''}`}>
          <div className="step-heading"><span>2</span><div><h2>Pergunte ao documento</h2><p>{document ? 'Escolha entre resposta rápida e dois fluxos de pesquisa aprofundada' : 'Disponível após o envio do arquivo'}</p></div></div>
          <form onSubmit={submitQuery}>
            <div className="query-options" role="radiogroup" aria-label="Tipo de consulta">
              <label className={mode === 'question' ? 'is-selected' : ''}><input type="radio" name="query-mode" value="question" checked={mode === 'question'} onChange={() => setMode('question')} disabled={!document || isAsking} /><span><strong>Resposta rápida</strong><small>Uma pergunta, com os trechos mais relevantes.</small></span></label>
              <label className={mode === 'research_direct' ? 'is-selected' : ''}><input type="radio" name="query-mode" value="research_direct" checked={mode === 'research_direct'} onChange={() => setMode('research_direct')} disabled={!document || isAsking} /><span><strong>Pesquisa direta</strong><small>Executa todo o plano sem perguntas intermediárias.</small></span></label>
              <label className={mode === 'research_guided' ? 'is-selected' : ''}><input type="radio" name="query-mode" value="research_guided" checked={mode === 'research_guided'} onChange={() => setMode('research_guided')} disabled={!document || isAsking} /><span><strong>Pesquisa assistida</strong><small>Pode pedir esclarecimentos antes de investigar.</small></span></label>
            </div>
            {mode !== 'question' && <label className="depth-field">Profundidade da pesquisa <select value={depth} onChange={(event) => setDepth(Number(event.target.value))} disabled={!document || isAsking}>{[1, 2, 3].map((value) => <option key={value} value={value}>{value} {value === 1 ? 'rodada' : 'rodadas'}</option>)}</select></label>}
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} disabled={!document || isAsking} placeholder={mode !== 'question' ? 'Ex.: Compare os principais argumentos e suas evidências.' : 'Ex.: Quais são os pontos principais deste documento?'} rows={4} maxLength={2000} />
            <button className="primary-button" type="submit" disabled={!document || question.trim().length < 3 || isAsking}>{isAsking ? (mode === 'question' ? 'Buscando resposta…' : 'Pesquisando…') : mode === 'question' ? 'Perguntar →' : mode === 'research_direct' ? 'Pesquisar diretamente →' : 'Iniciar pesquisa assistida →'}</button>
          </form>
        </div>
      </section>

      {answer && <section className="answer-card" aria-live="polite"><p className="answer-label">RESPOSTA</p><p className="answer-text">{answer.answer}</p>{renderSources(answer.sources)}</section>}
      {directResearch && renderResearch({ label: 'PESQUISA DIRETA', answer: directResearch.answer, findings: directResearch.findings, sources: directResearch.sources, rounds: directResearch.rounds_completed, followUps: directResearch.review.follow_up_questions, sufficiency: directResearch.sufficiency_check })}
      {researchSession?.status === 'awaiting_clarification' && currentClarification && <section className="answer-card clarification-card" aria-live="polite"><p className="answer-label">ANTES DE PESQUISAR</p><h2>Ajude a delimitar a pesquisa</h2><p className="clarification-progress">Pergunta {clarificationIndex + 1} de {clarificationQuestions.length}</p><p className="clarification-question">{currentClarification}</p><form onSubmit={submitClarification}><textarea value={clarificationAnswer} onChange={(event) => setClarificationAnswer(event.target.value)} disabled={isAsking} placeholder="Digite seu esclarecimento…" rows={3} maxLength={1000} autoFocus /><button className="primary-button" type="submit" disabled={!clarificationAnswer.trim() || isAsking}>{isAsking ? 'Continuando…' : clarificationIndex + 1 === clarificationQuestions.length ? 'Responder e pesquisar →' : 'Responder →'}</button></form></section>}
      {researchSession?.status === 'researching' && <section className="answer-card research-status" aria-live="polite"><p className="answer-label">PESQUISA EM ANDAMENTO</p><p>Planejando consultas, verificando evidências e preparando o relatório…</p></section>}
      {researchSession?.status === 'completed' && researchSession.report_data && renderResearch({ label: 'PESQUISA ASSISTIDA', answer: researchSession.report_data.markdown_report, findings: researchSession.findings, sources: researchSession.sources, rounds: researchSession.rounds_completed, followUps: researchSession.report_data.follow_up_questions, sufficiency: researchSession.sufficiency_check })}
      <footer>Seus arquivos ficam disponíveis somente enquanto a API estiver em execução.</footer>
    </main>
  )
}

export default App
