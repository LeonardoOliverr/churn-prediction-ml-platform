import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-1 border px-2 py-0.5 text-[11px] font-medium tracking-wide transition-colors select-none',
  {
    variants: {
      variant: {
        default:     'border-transparent bg-primary/15 text-primary',
        secondary:   'border-transparent bg-secondary text-secondary-foreground',
        destructive: 'border-crit-line bg-crit-soft text-crit',
        outline:     'border-border text-foreground',
        success:     'border-ok-line bg-ok-soft text-ok',
        warning:     'border-warn-line bg-warn-soft text-warn',
        champion:    'border-amber-500/30 bg-amber-500/10 text-amber-400',
        challenger:  'border-blue-500/30 bg-blue-500/10 text-blue-400',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
