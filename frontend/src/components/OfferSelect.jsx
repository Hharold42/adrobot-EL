import { useEffect, useState } from 'react'
import { Flex, Popover, SegmentedControl, Spinner, Text, TextField } from '@radix-ui/themes'
// В @radix-ui/themes 3.3.0 Popover.Anchor теряет children (баг в сборке),
// поэтому якорь берём напрямую из примитива radix-ui
import { Popover as PopoverPrimitive } from 'radix-ui'
import { CheckIcon, MagnifyingGlassIcon } from '@radix-ui/react-icons'
import { api } from '../api'

/** Название без дублирующего ID в начале («18004 Hepatix…» → «Hepatix…»). */
const shortName = (o) => o.name.startsWith(`${o.id} `) ? o.name.slice(String(o.id).length + 1) : o.name

/**
 * Поисковый селект оффера Keitaro.
 * onSelect(offer) вызывается при выборе, поле очищается.
 * excludeIds — офферы, которые не показываем в выдаче (уже в кампании).
 * multiple — режим мультивыбора: список не закрывается, выбранные (selectedIds)
 *            помечаются галочкой, повторный клик вызывает onSelect снова (снять).
 * geo — если задан, в шапке выпадашки появляется тогл «гео / все».
 *
 * Выпадающий список — Popover: рендерится в портале и поэтому
 * не обрезается карточкой формы (у Radix Card overflow: hidden).
 */
export default function OfferSelect({
  onSelect,
  excludeIds = [],
  selectedIds = [],
  multiple = false,
  placeholder,
  geo = null,
}) {
  const [query, setQuery] = useState('')
  const [options, setOptions] = useState([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [scope, setScope] = useState('geo') // 'geo' | 'all'

  // При смене гео возвращаем фильтр на место
  useEffect(() => setScope('geo'), [geo])

  useEffect(() => {
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        setOptions(await api.offers(query))
      } catch {
        setOptions([])
      } finally {
        setLoading(false)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  const available = options.filter((o) => !excludeIds.includes(o.id))
  const byGeo = geo && scope === 'geo'
  const list = byGeo ? available.filter((o) => o.country.includes(geo)) : available

  return (
    <div className="offer-select">
      <Popover.Root open={open} onOpenChange={setOpen}>
        <PopoverPrimitive.Anchor>
          <TextField.Root
            size="3"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setOpen(true)
            }}
            onFocus={() => setOpen(true)}
            onClick={() => setOpen(true)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') setOpen(true)
              if (e.key === 'Escape') setOpen(false)
            }}
            placeholder={placeholder ?? 'Название или ID оффера…'}
          >
            <TextField.Slot>
              <MagnifyingGlassIcon />
            </TextField.Slot>
          </TextField.Root>
        </PopoverPrimitive.Anchor>

        <Popover.Content
          side="bottom"
          align="start"
          sideOffset={6}
          collisionPadding={12}
          onOpenAutoFocus={(e) => e.preventDefault()}
          onInteractOutside={(e) => {
            // клик по самому полю поиска не должен закрывать список
            if (e.target.closest('.offer-select')) e.preventDefault()
          }}
          className="dropdown dropdown--offers"
        >
          {geo && (
            <div className="dropdown__head dropdown__head--row">
              <SegmentedControl.Root
                size="1"
                value={scope}
                onValueChange={setScope}
                className="scope-toggle"
              >
                <SegmentedControl.Item value="geo">Только {geo}</SegmentedControl.Item>
                <SegmentedControl.Item value="all">Все гео</SegmentedControl.Item>
              </SegmentedControl.Root>
              <Text size="1" color="gray">
                {loading ? 'поиск…' : `найдено: ${list.length}`}
              </Text>
            </div>
          )}

          <div className="dropdown__list">
            {loading && list.length === 0 && (
              <Flex align="center" gap="2" className="dropdown__empty">
                <Spinner size="1" />
                <Text size="2" color="gray">
                  Загрузка…
                </Text>
              </Flex>
            )}
            {!loading && list.length === 0 && (
              <Text size="2" color="gray" as="p" className="dropdown__empty">
                {byGeo ? `Нет офферов под гео ${geo}` : 'Ничего не найдено'}
              </Text>
            )}
            {list.map((o) => (
                <button
                  key={o.id}
                  type="button"
                  className="option"
                  data-selected={selectedIds.includes(o.id) ? '' : undefined}
                  onClick={() => {
                    onSelect(o)
                    if (!multiple) {
                      setQuery('')
                      setOpen(false)
                    }
                  }}
                >
                  <span className="id-chip">#{o.id}</span>
                  <span className="option__title">{shortName(o)}</span>
                  <span className="code-chip code-chip--muted">
                    {o.country.join(', ') || '—'}
                  </span>
                  <span className="option__meta option__meta--payout">
                    {o.payout_value} {o.payout_currency}
                  </span>
                  <CheckIcon className="option__check" />
                </button>
            ))}
          </div>
        </Popover.Content>
      </Popover.Root>
    </div>
  )
}
