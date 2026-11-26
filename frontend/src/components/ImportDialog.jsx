import { useEffect, useState } from 'react'
import { Badge, Button, Callout, Checkbox, Dialog, Flex, Skeleton, Spinner, Text } from '@radix-ui/themes'
import { DownloadIcon, ExclamationTriangleIcon } from '@radix-ui/react-icons'
import { api } from '../api'

/**
 * Импорт (бэкфилл) кампаний, созданных прямо в Keitaro.
 * Показывает кампании Keitaro; уже импортированные отмечены и недоступны для выбора.
 */
export default function ImportDialog({ open, onOpenChange, onImported }) {
  const [items, setItems] = useState(null)
  const [selected, setSelected] = useState(new Set())
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setItems(null)
    setSelected(new Set())
    setError('')
    api
      .keitaroCampaigns()
      .then(setItems)
      .catch((err) => setError(err.message))
  }, [open])

  const fresh = (items ?? []).filter((c) => !c.imported)
  const allSelected = fresh.length > 0 && fresh.every((c) => selected.has(c.id))

  const toggle = (id) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const submit = async () => {
    setBusy(true)
    setError('')
    try {
      await api.importCampaigns([...selected])
      onImported()
      onOpenChange(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Content maxWidth="520px">
        <Dialog.Title>Импорт кампаний из Keitaro</Dialog.Title>
        <Dialog.Description size="2" color="gray" mb="3">
          Кампании, созданные прямо в Keitaro, появятся в списке вместе со своими потоками
          и офферами — их можно будет редактировать так же, как созданные здесь.
        </Dialog.Description>

        {error && (
          <Callout.Root color="red" mb="3">
            <Callout.Icon>
              <ExclamationTriangleIcon />
            </Callout.Icon>
            <Callout.Text>{error}</Callout.Text>
          </Callout.Root>
        )}

        {items === null && !error && <Skeleton height="120px" />}

        {items && (
          <>
            <label className="import-row import-row--all">
              <Checkbox
                checked={allSelected}
                disabled={fresh.length === 0}
                onCheckedChange={(v) =>
                  setSelected(v ? new Set(fresh.map((c) => c.id)) : new Set())
                }
              />
              <Text size="2" weight="medium">
                {fresh.length === 0 ? 'Все кампании Keitaro уже импортированы' : `Выбрать все (${fresh.length})`}
              </Text>
            </label>
            <div className="import-list">
              {items.map((c) => (
                <label key={c.id} className="import-row" data-disabled={c.imported ? '' : undefined}>
                  <Checkbox
                    checked={c.imported || selected.has(c.id)}
                    disabled={c.imported}
                    onCheckedChange={() => toggle(c.id)}
                  />
                  <Text size="2" className="import-row__name">
                    {c.name}
                  </Text>
                  <Badge color="gray" variant="soft" size="1">
                    #{c.id}
                  </Badge>
                  {c.imported && (
                    <Badge color="grass" variant="soft" size="1">
                      уже есть
                    </Badge>
                  )}
                </label>
              ))}
            </div>
          </>
        )}

        <Flex justify="end" gap="3" mt="4">
          <Dialog.Close>
            <Button variant="soft" color="gray">
              Закрыть
            </Button>
          </Dialog.Close>
          <Button disabled={busy || selected.size === 0} onClick={submit}>
            {busy ? <Spinner size="2" /> : <DownloadIcon />} Импортировать
            {selected.size > 0 ? ` (${selected.size})` : ''}
          </Button>
        </Flex>
      </Dialog.Content>
    </Dialog.Root>
  )
}
