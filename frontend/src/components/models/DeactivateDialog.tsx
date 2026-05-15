import { useState } from 'react'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useDeactivateModel } from '@/hooks/useModels'
import type { ModelRole } from '@/types/api'

interface DeactivateDialogProps {
  open: boolean
  onClose: () => void
  modelId: string
  modelName: string
  role: ModelRole
}

export function DeactivateDialog({ open, onClose, modelId, modelName, role }: DeactivateDialogProps) {
  const [reason, setReason] = useState('')
  const [replacementModelId, setReplacementModelId] = useState('')
  const deactivate = useDeactivateModel()
  const isChampion = role === 'champion'

  async function handleConfirm() {
    if (!reason.trim()) return
    await deactivate.mutateAsync({
      modelId,
      payload: {
        reason: reason.trim(),
        replacement_model_id: isChampion && replacementModelId.trim()
          ? replacementModelId.trim()
          : undefined,
      },
    })
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isChampion ? 'Substituir Champion' : 'Remover Challenger'}
          </DialogTitle>
          <DialogDescription>
            {isChampion
              ? `O modelo champion ${modelName} será desativado. Informe um modelo substituto.`
              : `O challenger ${modelName} será removido da produção.`}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label>Motivo <span className="text-destructive">*</span></Label>
            <Input
              placeholder="ex: Desempenho abaixo do esperado"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>

          {isChampion && (
            <div className="space-y-1.5">
              <Label>Model ID substituto (UUID) <span className="text-destructive">*</span></Label>
              <Input
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                value={replacementModelId}
                onChange={(e) => setReplacementModelId(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                O champion não pode ser desativado sem um modelo substituto.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={
              deactivate.isPending ||
              !reason.trim() ||
              (isChampion && !replacementModelId.trim())
            }
          >
            {deactivate.isPending ? 'Desativando...' : 'Confirmar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
