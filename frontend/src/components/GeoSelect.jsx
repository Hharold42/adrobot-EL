import { useEffect, useMemo, useState } from 'react'
import { Popover, Skeleton, Text, TextField } from '@radix-ui/themes'
import { CheckIcon, ChevronDownIcon, MagnifyingGlassIcon } from '@radix-ui/react-icons'
import { api } from '../api'

/** Русские названия для ISO-кодов стран, встречающихся в офферах. */
export const COUNTRY_NAMES = {
  BR: 'Бразилия',
  CL: 'Чили',
  CO: 'Колумбия',
  DE: 'Германия',
  ES: 'Испания',
  FR: 'Франция',
  IN: 'Индия',
  IT: 'Италия',
  MX: 'Мексика',
  PE: 'Перу',
  PH: 'Филиппины',
  PL: 'Польша',
  PT: 'Португалия',
  RO: 'Румыния',
  TH: 'Таиланд',
  TR: 'Турция',
}

/** Склонение «оффер» по числу. */
const offersWord = (n) => {
  const m10 = n % 10
  const m100 = n % 100
  if (m10 === 1 && m100 !== 11) return 'оффер'
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return 'оффера'
  return 'офферов'
}

/**
 * Селект гео-кода страны. Список собирается на backend из офферов
 * (в Keitaro нет справочника стран), группируется по регионам,
 * внутри — быстрый поиск по коду и названию.
 */
export default function GeoSelect({ value, onChange }) {
  const [countries, setCountries] = useState(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

  useEffect(() => {
    api
      .countries()
      .then(setCountries)
      .catch(() => setCountries([]))
  }, [])

  const regions = useMemo(() => {
    const q = query.trim().toLowerCase()
    const map = new Map()
    for (const c of countries ?? []) {
      const name = (COUNTRY_NAMES[c.code] ?? '').toLowerCase()
      if (q && !c.code.toLowerCase().includes(q) && !name.includes(q)) continue
      if (!map.has(c.region)) map.set(c.region, [])
      map.get(c.region).push(c)
    }
    return [...map.entries()]
  }, [countries, query])

  if (countries === null) return <Skeleton height="36px" />

  const pick = (code) => {
    onChange(code)
    setOpen(false)
  }

  return (
    <Popover.Root
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        if (!o) setQuery('')
      }}
    >
      <Popover.Trigger>
        <button type="button" className="field-trigger" data-filled={value ? '' : undefined}>
          {value ? (
            <span className="field-trigger__value">
              <span className="code-chip">{value}</span>
              {COUNTRY_NAMES[value] ?? value}
            </span>
          ) : (
            <span className="field-trigger__placeholder">Выберите страну…</span>
          )}
          <ChevronDownIcon className="field-trigger__chevron" />
        </button>
      </Popover.Trigger>

      <Popover.Content
        side="bottom"
        align="start"
        sideOffset={6}
        collisionPadding={12}
        className="dropdown dropdown--geo"
      >
        <div className="dropdown__head">
          <TextField.Root
            size="2"
            variant="soft"
            color="gray"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск страны…"
            autoFocus
          >
            <TextField.Slot>
              <MagnifyingGlassIcon />
            </TextField.Slot>
          </TextField.Root>
        </div>

        <div className="dropdown__list">
          {regions.length === 0 && (
            <Text size="2" color="gray" as="p" className="dropdown__empty">
              Ничего не найдено
            </Text>
          )}
          {regions.map(([region, list]) => (
            <div key={region}>
              <div className="dropdown__group">{region}</div>
              {list.map((c) => (
                <button
                  key={c.code}
                  type="button"
                  className="option"
                  data-selected={c.code === value ? '' : undefined}
                  onClick={() => pick(c.code)}
                >
                  <span className="code-chip">{c.code}</span>
                  <span className="option__title">{COUNTRY_NAMES[c.code] ?? c.code}</span>
                  <span className="option__meta">
                    {c.offers_count} {offersWord(c.offers_count)}
                  </span>
                  <CheckIcon className="option__check" />
                </button>
              ))}
            </div>
          ))}
        </div>
      </Popover.Content>
    </Popover.Root>
  )
}
