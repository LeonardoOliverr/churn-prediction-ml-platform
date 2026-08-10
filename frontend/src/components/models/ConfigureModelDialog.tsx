import { useState } from 'react'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useConfigureChampion, useConfigureChallenger } from '@/hooks/useModels'

interface ConfigureModelDialogProps {
  open: boolean
  onClose: () => void
  role: 'champion' | 'challenger'
}

export function ConfigureModelDialog({ open, onClose, role }: ConfigureModelDialogProps) {
  const [modelId, setModelId] = useState('')
  const [threshold, setThreshold] = useState('0.5')
  const [trafficSplit, setTrafficSplit] = useState('0.2')
  const [reason, setReason] = useState('')
  const [description, setDescription] = useState('')

  const configChampion = useConfigureChampion()
  const configChallenger = useConfigureChallenger()

  const isPending = configChampion.isPending || configChallenger.isPending

  async function handleSubmit() {
    if (!modelId.trim()) return
    const payload = {
      model_id: modelId.trim(),
      threshold: parseFloat(threshold),
      activation_reason: reason || undefined,
      description: description || undefined,
    }

    if (role === 'champion') {
      await configChampion.mutateAsync(payload)
    } else {
      await configChallenger.mutateAsync({ ...payload, traffic_split: parseFloat(trafficSplit) })
    }
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            Configurar {role === 'champion' ? 'Champion' : 'Challenger'}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label>Model ID (UUID)</Label>
            <Input
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Threshold (0–1)</Label>
              <Input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
              />
            </div>
            {role === 'challenger' && (
              <div className="space-y-1.5">
                <Label>Traffic split (0–0.5)</Label>
                <Input
                  type="number"
                  min="0.01"
                  max="0.5"
                  step="0.01"
                  value={trafficSplit}
                  onChange={(e) => setTrafficSplit(e.target.value)}
                />
              </div>
            )}
          </div>
          <div className="space-y-1.5">
            <Label>Motivo (opcional)</Label>
            <Input
              placeholder="ex: Random Forest v2 com F1 superior"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Descrição (opcional)</Label>
            <Input
              placeholder="ex: Modelo treinado com dados 2023-Q4"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isPending || !modelId.trim()}>
            {isPending ? 'Salvando...' : 'Confirmar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
