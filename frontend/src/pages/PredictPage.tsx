import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Icon, SectionCard, Donut, CodeBlock, Pill,
  Table, Th, Td, Tr, StatusBadge,
} from '@/components/primitives'
import { useAuthStore } from '@/store/authStore'
import { predictSingle } from '@/services/predict'
import type { CustomerFeatures, PredictResponse } from '@/types/api'

const SAMPLE: CustomerFeatures = {
  customer_id:       'DEMO-001',
  tenure_months:     12,
  monthly_charges:   70.5,
  total_charges:     846.0,
  senior_citizen:    0,
  partner:           0,
  dependents:        0,
  phone_service:     1,
  paperless_billing: 1,
  gender:            'Male',
  multiple_lines:    'No',
  internet_service:  'Fiber optic',
  online_security:   'No',
  online_backup:     'No',
  device_protection: 'No',
  tech_support:      'No',
  streaming_tv:      'No',
  streaming_movies:  'No',
  contract:          'Month-to-month',
  payment_method:    'Electronic check',
}

const SHAP_TELCO = [
  { feature: 'tenure_months',          weight: -0.28 },
  { feature: 'monthly_charges',        weight: +0.22 },
  { feature: 'contract=Month-to-month',weight: +0.19 },
  { feature: 'internet=Fiber optic',   weight: +0.14 },
  { feature: 'payment=Elec.check',     weight: +0.11 },
  { feature: 'online_security=No',     weight: +0.08 },
]

type HistoryItem = PredictResponse & { ts: string; payload: CustomerFeatures }

export function PredictPage() {
  const { selectedTenantId, selectedProjectId, apiKey, setApiKey } = useAuthStore()
  const [mode, setMode]       = useState<'single' | 'batch'>('single')
  const [payload, setPayload] = useState(JSON.stringify(SAMPLE, null, 2))
  const [payloadError, setPayloadError] = useState<string | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])

  const predict = useMutation({
    mutationFn: (f: CustomerFeatures) => predictSingle(f),
    onSuccess: (data) => {
      setHistory(h => [{ ...data, ts: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC', payload: JSON.parse(payload) }, ...h].slice(0, 6))
    },
  })

  function handleSend() {
    setPayloadError(null)
    let parsed: CustomerFeatures
    try {
      parsed = JSON.parse(payload)
    } catch (e) {
      setPayloadError('Invalid JSON')
      return
    }
    if (!apiKey) {
      const key = window.prompt('Enter your API key (scope: predict):')
      if (key) setApiKey(key.trim())
      else return
    }
    predict.mutate(parsed)
  }

  const result = predict.data ?? null
  const decision = result ? (result.churn_pred ? 'POSITIVE' : 'NEGATIVE') : null

  return (
    <div style={{ padding: 'var(--pad-section)', display: 'flex', flexDirection: 'column', gap: 'var(--gap-grid)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <div>
          <div style={{ fontSize: 14, color: 'var(--fg-1)', fontWeight: 500 }}>Endpoint simulator</div>
          <div style={{ fontSize: 12, color: 'var(--fg-3)', marginTop: 2 }}>Test predictions against the live champion. All calls are real — results are persisted.</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Pill tone="ghost" icon="lock">live</Pill>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 'var(--gap-grid)' }}>
        {/* Request */}
        <SectionCard title="Request" pad={false}
          action={
            <div style={{ display: 'flex', gap: 4, padding: 2, background: 'var(--bg-inset)', borderRadius: 4 }}>
              {(['single', 'batch'] as const).map(m => (
                <button key={m} onClick={() => setMode(m)} className="btn btn-sm" style={{
                  background: mode === m ? 'var(--bg-3)' : 'transparent',
                  borderColor: mode === m ? 'var(--border-2)' : 'transparent',
                  color: mode === m ? 'var(--fg-1)' : 'var(--fg-3)',
                  textTransform: 'capitalize',
                }}>{m}</button>
              ))}
            </div>
          }
        >
          {/* Method + endpoint */}
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--divider)', display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 12, alignItems: 'center' }}>
            <div style={{ padding: '4px 8px', background: 'var(--bg-inset)', border: '1px solid var(--border-1)', borderRadius: 4, fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent-fg)', fontWeight: 600 }}>POST</div>
            <div className="input mono" style={{ fontSize: 12, color: 'var(--fg-2)', cursor: 'default' }}>
              {mode === 'single' ? '/predict' : '/predict/batch'}
            </div>
          </div>

          {/* Headers */}
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--divider)' }}>
            <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>Headers</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
              <span style={{ color: 'var(--fg-4)' }}>x-tenant-id</span>
              <span style={{ color: 'var(--fg-2)' }}>{selectedTenantId ?? '—'}</span>
              <span style={{ color: 'var(--fg-4)' }}>x-project</span>
              <span style={{ color: 'var(--fg-2)' }}>{selectedProjectId ?? '(all)'}</span>
              <span style={{ color: 'var(--fg-4)' }}>x-api-key</span>
              <span style={{ color: 'var(--fg-2)' }}>
                {apiKey ? `${apiKey.slice(0, 8)}••••••••` : <span style={{ color: 'var(--crit-fg)' }}>not set</span>}
              </span>
            </div>
          </div>

          {/* Payload */}
          <div style={{ padding: '12px 16px' }}>
            <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
              <span>Payload · application/json</span>
              <span style={{ fontFamily: 'var(--font-mono)', textTransform: 'none' }}>{payload.length}b</span>
            </div>
            <textarea
              value={payload}
              onChange={e => { setPayload(e.target.value); setPayloadError(null) }}
              spellCheck={false}
              style={{
                width: '100%', minHeight: 280, padding: 12,
                background: 'var(--bg-inset)', border: `1px solid ${payloadError ? 'var(--crit-fg)' : 'var(--border-1)'}`, borderRadius: 4,
                color: 'var(--fg-1)', fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.55,
                resize: 'vertical', outline: 'none', boxSizing: 'border-box',
              }}
            />
            {payloadError && <div style={{ fontSize: 11, color: 'var(--crit-fg)', marginTop: 4 }}>{payloadError}</div>}
          </div>

          {/* Action bar */}
          <div style={{ padding: '10px 16px', borderTop: '1px solid var(--divider)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ fontSize: 11, color: 'var(--fg-4)', display: 'flex', gap: 8, alignItems: 'center' }}>
              <Icon name="info" size={11}/> Requires API key with <span className="mono" style={{ color: 'var(--fg-2)' }}>predict</span> scope.
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn" onClick={() => setPayload(JSON.stringify(SAMPLE, null, 2))}>
                <Icon name="download" size={12}/> Sample
              </button>
              <button className="btn btn-primary" onClick={handleSend} disabled={predict.isPending}>
                {predict.isPending
                  ? <><Icon name="refresh" size={12}/> Calling…</>
                  : <><Icon name="play" size={11}/> Send request</>}
                <span className="kbd" style={{ marginLeft: 4 }}>⌘↵</span>
              </button>
            </div>
          </div>
        </SectionCard>

        {/* Response */}
        <SectionCard title="Response" pad={false}
          action={result && (
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <Pill tone="ok">200</Pill>
              <span className="num" style={{ fontSize: 11, color: 'var(--fg-3)' }}>OK</span>
            </div>
          )}
        >
          {predict.isError && (
            <div style={{ padding: '14px 16px', display: 'flex', gap: 8, color: 'var(--crit-fg)', fontSize: 12 }}>
              <Icon name="alert" size={13}/> Prediction failed — check API key and champion configuration.
            </div>
          )}
          {!result && !predict.isPending && !predict.isError && (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--fg-4)' }}>
              <Icon name="predict" size={20}/>
              <div style={{ fontSize: 12, marginTop: 8 }}>No response yet. Send a request to see the prediction.</div>
            </div>
          )}
          {predict.isPending && (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--fg-3)' }}>
              <Icon name="refresh" size={16}/>
              <div style={{ fontSize: 12, marginTop: 8 }}>Calling endpoint…</div>
            </div>
          )}
          {result && decision && <PredictResultPanel result={result} decision={decision}/>}
        </SectionCard>
      </div>

      {/* Session history */}
      {history.length > 0 && (
        <SectionCard title="Session history" pad={false}>
          <Table>
            <thead>
              <tr>
                <Th>Time</Th>
                <Th>Prediction ID</Th>
                <Th>Customer</Th>
                <Th align="right">Score</Th>
                <Th align="right">Decision</Th>
                <Th>Model</Th>
              </tr>
            </thead>
            <tbody>
              {history.map(h => (
                <Tr key={h.prediction_id}>
                  <Td mono style={{ color: 'var(--fg-3)', fontSize: 11 }}>{h.ts}</Td>
                  <Td mono style={{ color: 'var(--fg-2)', fontSize: 11 }}>{h.prediction_id.slice(0, 13)}…</Td>
                  <Td mono style={{ color: 'var(--fg-1)', fontSize: 11 }}>{h.customer_id}</Td>
                  <Td mono align="right">{h.churn_probability.toFixed(4)}</Td>
                  <Td align="right">
                    <StatusBadge status={h.churn_pred ? 'warning' : 'ok'} label={h.churn_pred ? 'POSITIVE' : 'NEGATIVE'} size="xs" dot={false}/>
                  </Td>
                  <Td mono style={{ color: 'var(--fg-3)', fontSize: 11 }}>{h.model_name}@{h.model_version}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        </SectionCard>
      )}
    </div>
  )
}

function PredictResultPanel({ result, decision }: { result: PredictResponse; decision: string }) {
  const isPos = decision === 'POSITIVE'
  const score = result.churn_probability
  const threshold = result.threshold_used
  const color = isPos ? 'var(--warn-fg)' : 'var(--ok-fg)'

  const json = JSON.stringify({
    prediction_id:     result.prediction_id,
    customer_id:       result.customer_id,
    model:             `${result.model_name}@${result.model_version}`,
    churn_probability: result.churn_probability,
    threshold_used:    result.threshold_used,
    churn_pred:        result.churn_pred,
    risk_level:        result.risk_level,
  }, null, 2)

  return (
    <div>
      {/* Decision banner */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--divider)', display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: 12 }}>
        <div>
          <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Decision</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 4 }}>
            <span className="num" style={{ fontSize: 24, fontWeight: 500, color, letterSpacing: '-0.01em' }}>{decision}</span>
            <span className="num" style={{ fontSize: 13, color: 'var(--fg-3)' }}>
              score {score.toFixed(4)} · threshold {threshold.toFixed(2)}
            </span>
          </div>
        </div>
        <Donut value={score * 100} size={48} stroke={5} color={color} track="var(--bg-3)" label={`${(score * 100).toFixed(0)}`}/>
      </div>

      {/* Score gauge */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--divider)' }}>
        <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>Score distribution</div>
        <div style={{ position: 'relative', height: 8, background: 'var(--bg-3)', borderRadius: 999 }}>
          <div style={{ position: 'absolute', left: 0, top: 0, height: '100%', width: `${threshold * 100}%`, background: 'var(--ok-soft)', borderTopLeftRadius: 999, borderBottomLeftRadius: 999 }}/>
          <div style={{ position: 'absolute', right: 0, top: 0, height: '100%', width: `${(1 - threshold) * 100}%`, background: 'var(--warn-soft)', borderTopRightRadius: 999, borderBottomRightRadius: 999 }}/>
          <div style={{ position: 'absolute', left: `${threshold * 100}%`, top: -3, width: 2, height: 14, background: 'var(--fg-2)' }}/>
          <div style={{ position: 'absolute', left: `calc(${score * 100}% - 6px)`, top: -3, width: 12, height: 14, background: color, borderRadius: 2, border: '2px solid var(--bg-2)' }}/>
        </div>
        <div className="num" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--fg-4)', marginTop: 4 }}>
          <span>0.00</span>
          <span>{threshold.toFixed(2)}</span>
          <span>1.00</span>
        </div>
      </div>

      {/* SHAP attribution */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--divider)' }}>
        <div style={{ fontSize: 10, color: 'var(--fg-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
          Top feature attribution <span style={{ textTransform: 'none', marginLeft: 6 }}>(simulated · SHAP-style)</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          {SHAP_TELCO.map((r, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 110px 50px', gap: 10, alignItems: 'center', fontSize: 11 }}>
              <span className="mono" style={{ color: 'var(--fg-2)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.feature}</span>
              <div style={{ position: 'relative', height: 6, background: 'var(--bg-3)', borderRadius: 999 }}>
                <div style={{
                  position: 'absolute',
                  left: r.weight >= 0 ? '50%' : `${50 + r.weight * 50}%`,
                  width: `${Math.abs(r.weight) * 50}%`,
                  top: 0, height: '100%',
                  background: r.weight >= 0 ? 'var(--warn-fg)' : 'var(--ok-fg)',
                  borderRadius: 999,
                }}/>
                <div style={{ position: 'absolute', left: '50%', top: -2, width: 1, height: 10, background: 'var(--border-3)' }}/>
              </div>
              <span className="num" style={{ textAlign: 'right', color: r.weight >= 0 ? 'var(--warn-fg)' : 'var(--ok-fg)' }}>
                {r.weight >= 0 ? '+' : ''}{r.weight.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Response JSON */}
      <div style={{ padding: '12px 16px' }}>
        <CodeBlock lang="response · application/json" height={200}>{json}</CodeBlock>
      </div>
    </div>
  )
}
