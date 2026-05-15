import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { formatDate, formatPercent } from '@/lib/utils'
import type { PredictionRecord, RiskLevel } from '@/types/api'

function getRisk(p: number): { label: RiskLevel; bar: string; variant: 'success' | 'warning' | 'destructive' } {
  if (p >= 0.7) return { label: 'high',   bar: 'fill-crit', variant: 'destructive' }
  if (p >= 0.4) return { label: 'medium', bar: 'fill-warn', variant: 'warning' }
  return           { label: 'low',    bar: 'fill-ok',  variant: 'success' }
}

export function PredictionTable({ records }: { records: PredictionRecord[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Cliente</TableHead>
          <TableHead>Probabilidade</TableHead>
          <TableHead>Risco</TableHead>
          <TableHead>Churn</TableHead>
          <TableHead>Threshold</TableHead>
          <TableHead>Latência</TableHead>
          <TableHead>Data</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {records.map((r) => {
          const risk = getRisk(r.churn_probability)
          return (
          <TableRow key={r.id}>
            <TableCell className="font-metric text-[12px] text-fg-2">{r.customer_id}</TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-20 rounded-full bg-bg-4 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-[width] ${risk.bar}`}
                    style={{ width: `${r.churn_probability * 100}%` }}
                  />
                </div>
                <span className="font-metric text-[12px] text-fg-1 tabular-nums w-10">
                  {formatPercent(r.churn_probability)}
                </span>
              </div>
            </TableCell>
            <TableCell>
              <Badge variant={risk.variant}>{risk.label}</Badge>
            </TableCell>
            <TableCell>
              <Badge variant={r.churn_pred ? 'destructive' : 'success'}>
                {r.churn_pred ? 'Sim' : 'Não'}
              </Badge>
            </TableCell>
            <TableCell className="font-metric text-[12px] text-fg-4">
              {formatPercent(r.threshold_used)}
            </TableCell>
            <TableCell className="font-metric text-[12px] text-fg-4">
              {r.latency_ms != null ? `${r.latency_ms} ms` : '—'}
            </TableCell>
            <TableCell className="font-metric text-[12px] text-fg-4">
              {formatDate(r.requested_at)}
            </TableCell>
          </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
