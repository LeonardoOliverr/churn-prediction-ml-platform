import { Crown, FlaskConical, TrendingUp, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDate, formatPercent } from '@/lib/utils'
import type { ProjectModelConfigRecord } from '@/types/api'

interface ModelRoleCardProps {
  config: ProjectModelConfigRecord
  onPromote?: () => void
  onDeactivate?: () => void
}

export function ModelRoleCard({ config, onPromote, onDeactivate }: ModelRoleCardProps) {
  const isChampion = config.role === 'champion'

  return (
    <div className={`rounded-md border bg-bg-2 overflow-hidden ${isChampion ? 'border-amber-500/25' : 'border-blue-500/25'}`}>
      {/* Header strip */}
      <div className={`flex items-center justify-between px-4 py-3 border-b ${isChampion ? 'border-amber-500/20 bg-amber-500/5' : 'border-blue-500/20 bg-blue-500/5'}`}>
        <div className="flex items-center gap-2.5">
          {isChampion
            ? <Crown className="h-4 w-4 text-amber-400" />
            : <FlaskConical className="h-4 w-4 text-blue-400" />
          }
          <span className="text-[14px] font-semibold text-fg-1">{config.model_name}</span>
        </div>
        <Badge variant={isChampion ? 'champion' : 'challenger'}>
          {isChampion ? 'Champion' : 'Challenger'}
        </Badge>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-px bg-border p-px m-4 rounded overflow-hidden">
        <KV label="Versão"        value={`v${config.model_version}`} mono />
        <KV label="Threshold"     value={formatPercent(config.threshold)} mono />
        {!isChampion && config.traffic_split != null && (
          <KV label="Traffic split" value={formatPercent(config.traffic_split)} mono />
        )}
        <KV label="Status"        value={config.model_status} />
        <KV label="Configurado por" value={config.configured_by ?? '—'} />
        <KV label="Desde"         value={formatDate(config.configured_at)} />
      </div>

      {config.activation_reason && (
        <p className="mx-4 mb-3 rounded bg-bg-3 px-3 py-2 text-[12px] text-fg-3 italic">
          {config.activation_reason}
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-2 px-4 pb-4">
        {!isChampion && onPromote && (
          <Button size="sm" onClick={onPromote} className="gap-1.5">
            <TrendingUp className="h-3.5 w-3.5" />
            Promover a Champion
          </Button>
        )}
        {onDeactivate && (
          <Button
            size="sm"
            variant={isChampion ? 'outline' : 'destructive'}
            onClick={onDeactivate}
            className="gap-1.5"
          >
            <X className="h-3.5 w-3.5" />
            {isChampion ? 'Substituir' : 'Remover'}
          </Button>
        )}
      </div>
    </div>
  )
}

function KV({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-bg-2 px-3 py-2">
      <p className="text-[10px] uppercase tracking-wider text-fg-4 mb-0.5">{label}</p>
      <p className={`text-[13px] font-medium text-fg-1 ${mono ? 'font-metric' : ''}`}>{value}</p>
    </div>
  )
}
