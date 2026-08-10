import React, { useState, useEffect, useRef, createContext, useContext } from 'react'
import type { CSSProperties } from 'react'

/* ============================================================
   Icon — single-stroke mono set (Lucide-style)
   ============================================================ */
type IconProps = { name: string; size?: number; strokeWidth?: number; className?: string; style?: CSSProperties }
export function Icon({ name, size = 14, strokeWidth = 1.5, className = '', style }: IconProps) {
  const p: React.SVGProps<SVGSVGElement> = {
    width: size, height: size, viewBox: '0 0 24 24',
    fill: 'none', stroke: 'currentColor', strokeWidth,
    strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const,
    className, style,
  }
  switch (name) {
    case 'grid':       return <svg {...p}><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
    case 'models':     return <svg {...p}><circle cx="12" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><path d="M12 8v4M12 12l-5 4M12 12l5 4"/></svg>
    case 'predict':    return <svg {...p}><path d="M5 12h14"/><path d="M13 6l6 6-6 6"/><circle cx="5" cy="12" r="1.4"/></svg>
    case 'logs':       return <svg {...p}><path d="M4 5h16M4 9h16M4 13h10M4 17h12"/></svg>
    case 'key':        return <svg {...p}><circle cx="8" cy="15" r="3.5"/><path d="M10.5 13L20 3.5M16 7l3 3"/></svg>
    case 'tenants':    return <svg {...p}><path d="M3 21V8l9-5 9 5v13"/><path d="M9 21v-7h6v7"/></svg>
    case 'health':     return <svg {...p}><path d="M3 12h4l2-5 4 10 2-5h6"/></svg>
    case 'shield':     return <svg {...p}><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/></svg>
    case 'search':     return <svg {...p}><circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4-4"/></svg>
    case 'filter':     return <svg {...p}><path d="M3 5h18l-7 9v6l-4-2v-4z"/></svg>
    case 'plus':       return <svg {...p}><path d="M12 5v14M5 12h14"/></svg>
    case 'chev-down':  return <svg {...p}><path d="M6 9l6 6 6-6"/></svg>
    case 'chev-right': return <svg {...p}><path d="M9 6l6 6-6 6"/></svg>
    case 'chev-up':    return <svg {...p}><path d="M6 15l6-6 6 6"/></svg>
    case 'x':          return <svg {...p}><path d="M6 6l12 12M18 6L6 18"/></svg>
    case 'check':      return <svg {...p}><path d="M5 12l4 4 10-10"/></svg>
    case 'copy':       return <svg {...p}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 012-2h10"/></svg>
    case 'external':   return <svg {...p}><path d="M14 4h6v6M20 4l-9 9M19 13v6H5V5h6"/></svg>
    case 'more':       return <svg {...p}><circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/></svg>
    case 'play':       return <svg {...p}><path d="M7 4l13 8-13 8z"/></svg>
    case 'promote':    return <svg {...p}><path d="M12 19V6M6 11l6-6 6 6"/></svg>
    case 'swap':       return <svg {...p}><path d="M4 7h13l-3-3M20 17H7l3 3"/></svg>
    case 'shadow':     return <svg {...p}><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="3" strokeDasharray="2 2"/></svg>
    case 'alert':      return <svg {...p}><path d="M12 4l10 17H2z"/><path d="M12 10v5M12 18v.5"/></svg>
    case 'info':       return <svg {...p}><circle cx="12" cy="12" r="9"/><path d="M12 8v.5M11 12h1v5h1"/></svg>
    case 'globe':      return <svg {...p}><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/></svg>
    case 'lock':       return <svg {...p}><rect x="4" y="11" width="16" height="10" rx="1.5"/><path d="M8 11V7a4 4 0 018 0v4"/></svg>
    case 'circle':     return <svg {...p}><circle cx="12" cy="12" r="9"/></svg>
    case 'dot':        return <svg {...p}><circle cx="12" cy="12" r="3" fill="currentColor"/></svg>
    case 'user':       return <svg {...p}><circle cx="12" cy="8" r="3.5"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>
    case 'logout':     return <svg {...p}><path d="M14 5h5v14h-5"/><path d="M3 12h12M11 8l4 4-4 4"/></svg>
    case 'refresh':    return <svg {...p}><path d="M21 12a9 9 0 11-3-6.7L21 8"/><path d="M21 3v5h-5"/></svg>
    case 'git-branch': return <svg {...p}><circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="8" r="2"/><path d="M6 7v10M6 14c0-3 3-6 12-6"/></svg>
    case 'history':    return <svg {...p}><path d="M3 12a9 9 0 109-9"/><path d="M3 3v6h6"/><path d="M12 8v5l3 2"/></svg>
    case 'terminal':   return <svg {...p}><rect x="3" y="4" width="18" height="16" rx="1"/><path d="M7 10l3 2-3 2M13 14h4"/></svg>
    case 'code':       return <svg {...p}><path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/></svg>
    case 'download':   return <svg {...p}><path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 20h16"/></svg>
    case 'trash':      return <svg {...p}><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/></svg>
    case 'briefcase':  return <svg {...p}><rect x="3" y="8" width="18" height="13" rx="1.5"/><path d="M9 8V6a3 3 0 016 0v2"/></svg>
    case 'trend-up':   return <svg {...p}><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>
    case 'pie':        return <svg {...p}><path d="M21.2 15A9 9 0 1 1 9 2.8"/><path d="M22 12a10 10 0 0 0-10-10v10z"/></svg>
    case 'dollar':     return <svg {...p}><path d="M12 2v20M17 5H9a3 3 0 100 6h6a3 3 0 110 6H7"/></svg>
    case 'users':      return <svg {...p}><circle cx="9" cy="7" r="3"/><path d="M3 21c1-4 3-6 6-6s5 2 6 6"/><circle cx="17" cy="8" r="2.5"/><path d="M21 21c-.7-3-2.5-5-4-5"/></svg>
    case 'chev-left':  return <svg {...p}><path d="M15 6l-6 6 6 6"/></svg>
    default:           return <svg {...p}><circle cx="12" cy="12" r="3"/></svg>
  }
}

/* ============================================================
   StatusBadge
   ============================================================ */
const STATUS_MAP: Record<string, { tone: string; label: string }> = {
  healthy:    { tone: 'ok',      label: 'Healthy' },
  stable:     { tone: 'ok',      label: 'Stable' },
  active:     { tone: 'ok',      label: 'Active' },
  ok:         { tone: 'ok',      label: 'OK' },
  passing:    { tone: 'ok',      label: 'Passing' },
  ready:      { tone: 'ok',      label: 'Ready' },
  champion:   { tone: 'accent',  label: 'Champion' },
  challenger: { tone: 'amber',   label: 'Challenger' },
  candidate:  { tone: 'neutral', label: 'Candidate' },
  retired:    { tone: 'muted',   label: 'Retired' },
  shadow:     { tone: 'accent',  label: 'Shadow' },
  watch:      { tone: 'amber',   label: 'Watch' },
  drift:      { tone: 'amber',   label: 'Drift' },
  degraded:   { tone: 'amber',   label: 'Degraded' },
  warning:    { tone: 'amber',   label: 'Warning' },
  stale:      { tone: 'amber',   label: 'Stale' },
  critical:   { tone: 'crit',    label: 'Critical' },
  failed:     { tone: 'crit',    label: 'Failed' },
  revoked:    { tone: 'crit',    label: 'Revoked' },
  unknown:    { tone: 'muted',   label: 'Unknown' },
  POSITIVE:   { tone: 'amber',   label: 'POSITIVE' },
  NEGATIVE:   { tone: 'ok',      label: 'NEGATIVE' },
}
const TONE_STYLES: Record<string, { bg: string; fg: string; line: string; dot: string }> = {
  ok:      { bg: 'var(--ok-soft)',     fg: 'var(--ok-fg)',     line: 'var(--ok-line)',     dot: 'var(--ok)' },
  accent:  { bg: 'var(--accent-soft)', fg: 'var(--accent-fg)', line: 'var(--accent-line)', dot: 'var(--accent)' },
  amber:   { bg: 'var(--warn-soft)',   fg: 'var(--warn-fg)',   line: 'var(--warn-line)',   dot: 'var(--warn)' },
  crit:    { bg: 'var(--crit-soft)',   fg: 'var(--crit-fg)',   line: 'var(--crit-line)',   dot: 'var(--crit)' },
  neutral: { bg: 'var(--bg-3)',        fg: 'var(--fg-2)',      line: 'var(--border-2)',    dot: 'var(--fg-3)' },
  muted:   { bg: 'transparent',        fg: 'var(--fg-4)',      line: 'var(--border-1)',    dot: 'var(--fg-4)' },
}
type StatusBadgeProps = { status: string; label?: string; dot?: boolean; size?: 'sm' | 'xs' }
export function StatusBadge({ status, label, dot = true, size = 'sm' }: StatusBadgeProps) {
  const cfg = STATUS_MAP[status] || { tone: 'muted', label: status }
  const finalLabel = label ?? cfg.label
  const t = TONE_STYLES[cfg.tone] || TONE_STYLES.muted
  const pad = size === 'xs' ? '1px 5px' : '2px 7px'
  const h = size === 'xs' ? 16 : 18
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: pad, height: h, lineHeight: 1,
      fontSize: size === 'xs' ? 10 : 11,
      fontWeight: 500, fontFamily: 'var(--font-mono)',
      letterSpacing: '0.04em', textTransform: 'uppercase',
      borderRadius: 3, background: t.bg, color: t.fg, border: `1px solid ${t.line}`,
    }}>
      {dot && <span style={{ width: 5, height: 5, borderRadius: 999, background: t.dot, boxShadow: cfg.tone === 'ok' ? `0 0 6px ${t.dot}` : 'none' }}/>}
      {finalLabel}
    </span>
  )
}

/* ============================================================
   Sparkline — SVG with gradient fill
   ============================================================ */
type SparklineProps = { data: number[]; width?: number; height?: number; color?: string; fill?: boolean; strokeWidth?: number }
export function Sparkline({ data, width = 120, height = 28, color = 'var(--accent-fg)', fill = true, strokeWidth = 1.25 }: SparklineProps) {
  if (!data || data.length < 2) return null
  const min = Math.min(...data), max = Math.max(...data)
  const range = max - min || 1
  const step = width / (data.length - 1)
  const pts = data.map((v, i) => [i * step, height - ((v - min) / range) * (height - 2) - 1])
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(' ')
  const dFill = d + ` L${width},${height} L0,${height} Z`
  const gradId = `sparkfill-${Math.round(width * 1000 + data[0] * 7)}`
  return (
    <svg width={width} height={height} style={{ display: 'block', overflow: 'visible' }}>
      {fill && (
        <defs>
          <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.22"/>
            <stop offset="100%" stopColor={color} stopOpacity="0"/>
          </linearGradient>
        </defs>
      )}
      {fill && <path d={dFill} fill={`url(#${gradId})`}/>}
      <path d={d} fill="none" stroke={color} strokeWidth={strokeWidth}/>
    </svg>
  )
}

/* ============================================================
   ChartArea — responsive area chart with time labels
   ============================================================ */
type ChartAreaProps = { data: number[]; height?: number; color?: string }
export function ChartArea({ data, height = 140, color = 'var(--accent-fg)' }: ChartAreaProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [w, setW] = useState(600)
  useEffect(() => {
    if (!ref.current) return
    const ro = new ResizeObserver(es => setW(es[0].contentRect.width))
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  const max = Math.max(...data) * 1.1
  const range = max || 1
  const step = w / (data.length - 1)
  const pts = data.map((v, i) => [i * step, height - (v / range) * height])
  const path = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(' ')
  const fillPath = path + ` L${w},${height} L0,${height} Z`
  const gridY = [0.25, 0.5, 0.75].map(p => height * p)
  return (
    <div ref={ref} style={{ width: '100%', position: 'relative' }}>
      <svg width={w} height={height} style={{ display: 'block' }}>
        <defs>
          <linearGradient id="area-grad" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.30"/>
            <stop offset="100%" stopColor={color} stopOpacity="0"/>
          </linearGradient>
        </defs>
        {gridY.map((y, i) => <line key={i} x1={0} x2={w} y1={y} y2={y} stroke="var(--border-1)" strokeDasharray="2 4"/>)}
        <path d={fillPath} fill="url(#area-grad)"/>
        <path d={path} fill="none" stroke={color} strokeWidth={1.5}/>
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', justifyContent: 'space-between', padding: '0 2px', fontSize: 9, color: 'var(--fg-5)', fontFamily: 'var(--font-mono)', pointerEvents: 'none' }}>
        <span style={{ alignSelf: 'flex-end' }}>−24h</span>
        <span style={{ alignSelf: 'flex-end' }}>−12h</span>
        <span style={{ alignSelf: 'flex-end' }}>−6h</span>
        <span style={{ alignSelf: 'flex-end' }}>now</span>
      </div>
    </div>
  )
}

/* ============================================================
   Bars — vertical bar chart (volume histogram)
   ============================================================ */
type BarsProps = { data: number[]; height?: number; color?: string; gap?: number }
export function Bars({ data, height = 60, color = 'var(--accent-fg)', gap = 2 }: BarsProps) {
  if (!data?.length) return null
  const max = Math.max(...data)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap, height }}>
      {data.map((v, i) => (
        <div key={i} style={{ flex: 1, height: `${(v / max) * 100}%`, background: color, opacity: 0.4 + (v / max) * 0.6, borderRadius: 1, minHeight: 1 }}/>
      ))}
    </div>
  )
}

/* ============================================================
   MetricCard — label + value + delta indicator + sparkline
   ============================================================ */
type MetricCardProps = {
  label: string; value: string | number; unit?: string
  delta?: number; deltaSuffix?: string
  sparkData?: number[]; sparkColor?: string
  hint?: string; accent?: string
}
export function MetricCard({ label, value, unit, delta, deltaSuffix = '', sparkData, sparkColor, hint, accent }: MetricCardProps) {
  const positive = typeof delta === 'number' && delta > 0
  const negative = typeof delta === 'number' && delta < 0
  return (
    <div className="card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 6, position: 'relative', overflow: 'hidden' }}>
      {accent && <div style={{ position: 'absolute', top: 0, left: 0, width: 2, height: '100%', background: accent }}/>}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 11, color: 'var(--fg-3)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 500 }}>{label}</div>
        {hint && <span style={{ fontSize: 10, color: 'var(--fg-4)', fontFamily: 'var(--font-mono)' }}>{hint}</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, marginTop: 2 }}>
        <div className="num" style={{ fontSize: 22, fontWeight: 500, color: 'var(--fg-1)', letterSpacing: '-0.01em', lineHeight: 1 }}>{value}</div>
        {unit && <div style={{ fontSize: 12, color: 'var(--fg-3)', fontFamily: 'var(--font-mono)', marginBottom: 2 }}>{unit}</div>}
        {typeof delta === 'number' && (
          <div className="num" style={{ fontSize: 11, marginLeft: 'auto', marginBottom: 2, color: positive ? 'var(--ok-fg)' : negative ? 'var(--crit-fg)' : 'var(--fg-3)' }}>
            {positive ? '▲' : negative ? '▼' : '—'} {Math.abs(delta).toFixed(2)}{deltaSuffix}
          </div>
        )}
      </div>
      {sparkData && (
        <div style={{ marginTop: 4 }}>
          <Sparkline data={sparkData} width={240} height={28} color={sparkColor || 'var(--accent-fg)'}/>
        </div>
      )}
    </div>
  )
}

/* ============================================================
   KV — key/value list
   ============================================================ */
type KVProps = { items: [string, React.ReactNode][]; mono?: boolean; cols?: number }
export function KV({ items, mono = true, cols = 1 }: KVProps) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: '6px 16px' }}>
      {items.map(([k, v], i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 12, padding: '3px 0' }}>
          <span style={{ color: 'var(--fg-3)' }}>{k}</span>
          <span className={mono ? 'num' : ''} style={{ color: 'var(--fg-1)', textAlign: 'right' }}>{v}</span>
        </div>
      ))}
    </div>
  )
}

/* ============================================================
   TenantAvatar — gradient initials
   ============================================================ */
type TenantAvatarProps = { initials: string; color?: string; size?: number }
const AVATAR_PALETTES: Record<string, string[]> = {
  petroleum: ['oklch(0.40 0.06 220)', 'oklch(0.55 0.075 220)'],
  amber:     ['oklch(0.40 0.06 70)',  'oklch(0.60 0.09 75)'],
  green:     ['oklch(0.38 0.05 155)', 'oklch(0.55 0.07 155)'],
}
export function TenantAvatar({ initials, color = 'petroleum', size = 22 }: TenantAvatarProps) {
  const [c1, c2] = AVATAR_PALETTES[color] || AVATAR_PALETTES.petroleum
  return (
    <div style={{
      width: size, height: size, minWidth: size, borderRadius: 4,
      background: `linear-gradient(135deg, ${c1}, ${c2})`,
      color: 'var(--fg-1)', fontSize: size <= 22 ? 10 : 11,
      fontWeight: 600, fontFamily: 'var(--font-mono)', letterSpacing: '0.02em',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      border: '1px solid var(--border-2)',
    }}>
      {initials}
    </div>
  )
}

/* ============================================================
   Donut — SVG donut chart
   ============================================================ */
type DonutProps = { value: number; size?: number; stroke?: number; color?: string; track?: string; label?: string }
export function Donut({ value, size = 44, stroke = 5, color = 'var(--accent-fg)', track = 'var(--bg-4)', label }: DonutProps) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const dash = c * (value / 100)
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none"/>
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none"
          strokeDasharray={`${dash} ${c - dash}`} strokeLinecap="round"/>
      </svg>
      {label !== undefined && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--fg-2)' }}>{label}</div>
      )}
    </div>
  )
}

/* ============================================================
   Heatbar — opacity-scaled squares
   ============================================================ */
type HeatbarProps = { data: number[]; max?: number; color?: string; w?: number; h?: number; gap?: number }
export function Heatbar({ data, max, color = 'var(--accent-fg)', w = 8, h = 14, gap = 2 }: HeatbarProps) {
  const top = max ?? Math.max(...data)
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap }}>
      {data.map((v, i) => (
        <div key={i} style={{ width: w, height: h, background: color, opacity: 0.15 + 0.85 * (v / top), borderRadius: 1 }}/>
      ))}
    </div>
  )
}

/* ============================================================
   Table primitives
   ============================================================ */
type TableProps = { children: React.ReactNode; dense?: boolean }
export function Table({ children, dense = false }: TableProps) {
  return (
    <div style={{ width: '100%', overflow: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0, fontSize: dense ? 12 : 'var(--t-body)' }}>
        {children}
      </table>
    </div>
  )
}
type ThProps = { children?: React.ReactNode; align?: 'left' | 'right' | 'center'; w?: number; sortable?: boolean; sorted?: 'asc' | 'desc' }
export function Th({ children, align = 'left', w, sortable, sorted }: ThProps) {
  return (
    <th style={{
      textAlign: align, padding: '8px var(--row-px)',
      fontSize: 10, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em',
      color: 'var(--fg-3)', background: 'var(--bg-2)', borderBottom: '1px solid var(--border-1)',
      position: 'sticky', top: 0, zIndex: 2, width: w, whiteSpace: 'nowrap',
      cursor: sortable ? 'pointer' : 'default', userSelect: 'none',
    }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        {children}
        {sorted === 'asc' && <Icon name="chev-up" size={11}/>}
        {sorted === 'desc' && <Icon name="chev-down" size={11}/>}
      </span>
    </th>
  )
}
type TdProps = { children?: React.ReactNode; align?: 'left' | 'right' | 'center'; mono?: boolean; style?: CSSProperties; colSpan?: number; onClick?: () => void }
export function Td({ children, align = 'left', mono = false, style, colSpan, onClick }: TdProps) {
  return (
    <td colSpan={colSpan} onClick={onClick} style={{
      padding: 'var(--row-py) var(--row-px)', borderBottom: '1px solid var(--divider)',
      textAlign: align, fontFamily: mono ? 'var(--font-mono)' : 'inherit',
      fontVariantNumeric: mono ? 'tabular-nums' : 'normal',
      whiteSpace: 'nowrap', height: 'var(--row-h)', ...style,
    }}>{children}</td>
  )
}
type TrProps = { children: React.ReactNode; selected?: boolean; onClick?: () => void; style?: CSSProperties }
export function Tr({ children, selected, onClick, style }: TrProps) {
  return (
    <tr onClick={onClick} style={{ background: selected ? 'var(--accent-soft)' : 'transparent', cursor: onClick ? 'pointer' : 'default', ...style }}
      onMouseEnter={e => { if (!selected) (e.currentTarget as HTMLElement).style.background = 'var(--bg-3)' }}
      onMouseLeave={e => { if (!selected) (e.currentTarget as HTMLElement).style.background = 'transparent' }}>
      {children}
    </tr>
  )
}

/* ============================================================
   Pill
   ============================================================ */
type PillProps = { children: React.ReactNode; tone?: string; icon?: string }
const PILL_TONES: Record<string, { bg: string; fg: string; bd: string }> = {
  neutral: { bg: 'var(--bg-3)',        fg: 'var(--fg-2)',      bd: 'var(--border-1)' },
  accent:  { bg: 'var(--accent-soft)', fg: 'var(--accent-fg)', bd: 'var(--accent-line)' },
  ok:      { bg: 'var(--ok-soft)',     fg: 'var(--ok-fg)',     bd: 'var(--ok-line)' },
  amber:   { bg: 'var(--warn-soft)',   fg: 'var(--warn-fg)',   bd: 'var(--warn-line)' },
  crit:    { bg: 'var(--crit-soft)',   fg: 'var(--crit-fg)',   bd: 'var(--crit-line)' },
  ghost:   { bg: 'transparent',        fg: 'var(--fg-3)',      bd: 'var(--border-1)' },
}
export function Pill({ children, tone = 'neutral', icon }: PillProps) {
  const t = PILL_TONES[tone] || PILL_TONES.neutral
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 7px', height: 18, borderRadius: 999, fontSize: 11, background: t.bg, color: t.fg, border: `1px solid ${t.bd}` }}>
      {icon && <Icon name={icon} size={11}/>}
      {children}
    </span>
  )
}

/* ============================================================
   CodeBlock
   ============================================================ */
type CodeBlockProps = { children: string; lang?: string; height?: number; copy?: boolean }
export function CodeBlock({ children, lang = 'json', height, copy = true }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const onCopy = () => {
    try { navigator.clipboard.writeText(children); setCopied(true); setTimeout(() => setCopied(false), 1100) } catch {}
  }
  return (
    <div style={{ background: 'var(--bg-inset)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-2)', position: 'relative', fontFamily: 'var(--font-mono)', fontSize: 12, maxHeight: height, overflow: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', borderBottom: '1px solid var(--border-1)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--fg-4)' }}>
        <span>{lang}</span>
        {copy && (
          <button className="btn btn-ghost btn-sm" onClick={onCopy} style={{ height: 20, padding: '0 6px' }}>
            <Icon name={copied ? 'check' : 'copy'} size={11}/> {copied ? 'copied' : 'copy'}
          </button>
        )}
      </div>
      <pre style={{ margin: 0, padding: 12, color: 'var(--fg-2)', whiteSpace: 'pre', overflowX: 'auto' }}>{children}</pre>
    </div>
  )
}

/* ============================================================
   SectionCard — card with labeled header
   ============================================================ */
type SectionCardProps = { title?: React.ReactNode; subtitle?: string; action?: React.ReactNode; children: React.ReactNode; pad?: boolean; style?: CSSProperties }
export function SectionCard({ title, subtitle, action, children, pad = true, style }: SectionCardProps) {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', ...style }}>
      {(title || action) && (
        <div className="section-head">
          <div>
            <div className="title">{title}</div>
            {subtitle && <div style={{ fontSize: 11, color: 'var(--fg-4)', marginTop: 2 }}>{subtitle}</div>}
          </div>
          {action}
        </div>
      )}
      <div style={{ padding: pad ? 'var(--pad-card)' : 0, flex: 1, minHeight: 0 }}>{children}</div>
    </div>
  )
}

/* ============================================================
   Toast
   ============================================================ */
type ToastFn = (msg: string, tone?: string) => void
const ToastCtx = createContext<ToastFn | null>(null)
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<{ id: string; msg: string; tone: string }[]>([])
  const push: ToastFn = (msg, tone = 'neutral') => {
    const id = Math.random().toString(36).slice(2)
    setToasts(t => [...t, { id, msg, tone }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 2500)
  }
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div style={{ position: 'fixed', top: 60, right: 16, display: 'flex', flexDirection: 'column', gap: 6, zIndex: 2000 }}>
        {toasts.map(t => (
          <div key={t.id} className="card fade-in" style={{ padding: '8px 12px', fontSize: 12, color: 'var(--fg-1)', borderColor: t.tone === 'ok' ? 'var(--ok-line)' : t.tone === 'crit' ? 'var(--crit-line)' : 'var(--border-2)' }}>{t.msg}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}
export function useToast(): ToastFn {
  return useContext(ToastCtx) || ((_msg: string) => {})
}

/* ============================================================
   Format helpers
   ============================================================ */
export const fmt = {
  num: (n: number, d = 0) => Number(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }),
  pct: (n: number, d = 1) => `${(n * 100).toFixed(d)}%`,
  compact: (n: number): string => {
    if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B'
    if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k'
    return String(Math.round(n))
  },
}

/* ============================================================
   Sparkline seed helper (deterministic pseudo-random)
   ============================================================ */
export function sparkline(seed: number, n = 32, base = 50, amp = 18): number[] {
  const out: number[] = []
  let v = base, s = seed
  for (let i = 0; i < n; i++) {
    s = (s * 9301 + 49297) % 233280
    const r = s / 233280
    v = v + (r - 0.5) * amp
    v = Math.max(base - amp * 1.4, Math.min(base + amp * 1.4, v))
    out.push(v)
  }
  return out
}
