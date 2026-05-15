import { useState } from 'react'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { usePromoteChallenger } from '@/hooks/useModels'

interface PromoteDialogProps {
  open: boolean
  onClose: () => void
  modelId: string
  modelName: string
}

export function PromoteDialog({ open, onClose, modelId, modelName }: PromoteDialogProps) {
  const [reason, setReason] = useState('')
  const promote = usePromoteChallenger()

  async function handleConfirm() {
    await promote.mutateAsync({ modelId, payload: { activation_reason: reason || undefined } })
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Promover Challenger a Champion</DialogTitle>
          <DialogDescription>
            O modelo <strong>{modelName}</strong> será promovido a champion. O champion atual será desativado.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5 py-2">
          <Label>Motivo da promoção (opcional)</Label>
          <Input
            placeholder="ex: F1-score superior em produção por 7 dias"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={handleConfirm} disabled={promote.isPending}>
            {promote.isPending ? 'Promovendo...' : 'Confirmar Promoção'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
