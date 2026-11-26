import { useEffect, useState } from 'react'
import { AlertDialog, Badge, Button, Card, Flex, Heading, Spinner, Text } from '@radix-ui/themes'
import {
  CounterClockwiseClockIcon,
  DrawingPinFilledIcon,
  DrawingPinIcon,
  ResetIcon,
  TrashIcon,
  UploadIcon,
} from '@radix-ui/react-icons'
import { api } from '../api'
import OfferSelect from './OfferSelect.jsx'

/** Название оффера без дублирующего ID в начале. */
const shortName = (o) =>
  o.name && o.name.startsWith(`${o.offer_id} `) ? o.name.slice(String(o.offer_id).length + 1) : o.name

/** Поле веса: Enter / потеря фокуса применяет значение и пинит оффер. */
function ShareInput({ offer, disabled, onCommit }) {
  const [value, setValue] = useState(String(offer.share))
  useEffect(() => setValue(String(offer.share)), [offer.share])

  const commit = () => {
    const num = Number(value)
    if (value === '' || Number.isNaN(num) || num === offer.share) {
      setValue(String(offer.share))
      return
    }
    onCommit(Math.round(num))
  }

  return (
    <label className="share-field" data-pinned={offer.pinned ? '' : undefined}>
      <input
        type="number"
        min="0"
        max="100"
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
      />
      <span>%</span>
    </label>
  )
}

/**
 * Карточка одного потока кампании.
 * Поток без офферов показываем как есть (без содержимого редиректа и фильтров).
 * Поток с неопубликованными изменениями подсвечен жёлтым.
 */
export default function StreamCard({ stream, busy, onAction }) {
  const [toRemove, setToRemove] = useState(null)

  if (!stream.editable) {
    return (
      <Card size="2" className="stream-card stream-card--plain">
        <Flex align="center" justify="between" gap="3">
          <Flex align="center" gap="3">
            <Badge color="gray" variant="soft">
              #{stream.position}
            </Badge>
            <Text weight="medium">{stream.name}</Text>
          </Flex>
          <Text size="2" color="gray">
            Поток без офферов — содержимое не отображается
          </Text>
        </Flex>
      </Card>
    )
  }

  const active = stream.offers.filter((o) => o.status === 'active')
  const removed = stream.offers.filter((o) => o.status === 'removed')
  const total = active.reduce((sum, o) => sum + o.share, 0)
  const act = (fn, text) => onAction(fn, text)

  return (
    <Card size="2" className="stream-card" data-dirty={stream.dirty ? '' : undefined}>
      <Flex align="center" justify="between" gap="3" mb="3" wrap="wrap">
        <Flex align="center" gap="3">
          <Heading size="4">{stream.name}</Heading>
          <Badge color="gray" variant="soft">
            Keitaro #{stream.keitaro_stream_id}
          </Badge>
          {stream.dirty && (
            <Badge color="amber" variant="solid">
              Не опубликован
            </Badge>
          )}
        </Flex>
        <Text size="2" color={total === 100 || active.length === 0 ? 'gray' : 'red'}>
          Сумма весов: {total}%
        </Text>
      </Flex>

      {active.length === 0 && (
        <Text color="gray" size="2" as="p" mb="3">
          В потоке нет офферов — добавьте первый ниже.
        </Text>
      )}

      <div className="offer-rows">
        {active.map((o) => (
          <div key={o.offer_id} className="offer-row" data-new={!o.in_keitaro ? '' : undefined}>
            <span className="id-chip">#{o.offer_id}</span>
            <span className="offer-row__name">
              {shortName(o) ?? '—'}
              {!o.in_keitaro && (
                <Badge ml="2" size="1" color="amber" variant="soft">
                  новый
                </Badge>
              )}
            </span>
            <span className="code-chip code-chip--muted">{o.country?.join(', ') || '—'}</span>
            <ShareInput
              offer={o}
              disabled={busy}
              onCommit={(share) =>
                act(() => api.patchOffer(stream.id, o.offer_id, { share }))
              }
            />
            <button
              type="button"
              className="icon-btn"
              data-active={o.pinned ? '' : undefined}
              disabled={busy}
              title={o.pinned ? 'Вес запинен — снять пин' : 'Запинить вес'}
              aria-label={o.pinned ? 'Снять пин' : 'Запинить вес'}
              onClick={() =>
                act(() => api.patchOffer(stream.id, o.offer_id, { pinned: !o.pinned }))
              }
            >
              {o.pinned ? <DrawingPinFilledIcon /> : <DrawingPinIcon />}
            </button>
            <button
              type="button"
              className="icon-btn icon-btn--danger"
              disabled={busy}
              title="Удалить из потока"
              aria-label="Удалить из потока"
              onClick={() => setToRemove(o)}
            >
              <TrashIcon />
            </button>
          </div>
        ))}

        {removed.map((o) => (
          <div key={o.offer_id} className="offer-row offer-row--removed">
            <span className="id-chip">#{o.offer_id}</span>
            <span className="offer-row__name">
              {shortName(o) ?? '—'}
              <Badge ml="2" size="1" color="gray" variant="soft">
                removed
              </Badge>
            </span>
            <span className="code-chip code-chip--muted">{o.country?.join(', ') || '—'}</span>
            <span className="share-field share-field--zero">0%</span>
            <Button
              size="1"
              variant="soft"
              color="gray"
              disabled={busy}
              onClick={() => act(() => api.restoreOffer(stream.id, o.offer_id))}
            >
              <CounterClockwiseClockIcon /> Bring back
            </Button>
          </div>
        ))}
      </div>

      <Flex direction="column" gap="1" mt="4">
        <Text size="2" weight="medium">
          Добавить оффер
        </Text>
        <div className="stream-card__add">
          <OfferSelect
            onSelect={(offer) => act(() => api.addOffer(stream.id, offer.id))}
            excludeIds={active.map((o) => o.offer_id)}
            placeholder="Название или ID оффера…"
          />
        </div>
      </Flex>

      <Flex justify="end" gap="3" mt="4" className="stream-card__footer">
        <Button
          variant="soft"
          color="gray"
          disabled={busy || !stream.dirty}
          onClick={() => act(() => api.cancelStream(stream.id), 'Изменения отменены')}
        >
          <ResetIcon /> Cancel
        </Button>
        <Button
          disabled={busy || !stream.dirty}
          onClick={() =>
            act(() => api.pushStream(stream.id), 'Поток опубликован в Keitaro')
          }
        >
          {busy ? <Spinner size="2" /> : <UploadIcon />} Push to Keitaro
        </Button>
      </Flex>

      <AlertDialog.Root open={toRemove !== null} onOpenChange={(o) => !o && setToRemove(null)}>
        <AlertDialog.Content maxWidth="420px">
          <AlertDialog.Title>Удалить оффер #{toRemove?.offer_id}?</AlertDialog.Title>
          <AlertDialog.Description size="2">
            Оффер получит вес 0% и серым уйдёт в архив потока, остальные веса пересчитаются.
            Из Keitaro он исчезнет после Push, а вернуть его можно кнопкой Bring back.
          </AlertDialog.Description>
          <Flex gap="3" mt="4" justify="end">
            <AlertDialog.Cancel>
              <Button variant="soft" color="gray">
                Отмена
              </Button>
            </AlertDialog.Cancel>
            <AlertDialog.Action>
              <Button
                color="red"
                onClick={() => act(() => api.removeOffer(stream.id, toRemove.offer_id))}
              >
                <TrashIcon /> Удалить
              </Button>
            </AlertDialog.Action>
          </Flex>
        </AlertDialog.Content>
      </AlertDialog.Root>
    </Card>
  )
}
