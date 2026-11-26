import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Badge, Flex, Text, Tooltip } from '@radix-ui/themes'
import {
  ExternalLinkIcon,
  GearIcon,
  LightningBoltIcon,
  PlusIcon,
  StackIcon,
} from '@radix-ui/react-icons'
import { api } from '../api'
import { useApiKey } from '../apiKey.jsx'

const KEITARO_ADMIN_URL = 'https://keitaro-for-tests.etolegko.com/admin/'
const STATUS_POLL_MS = 30000

export default function Sidebar() {
  const { apiKey } = useApiKey()
  const location = useLocation()
  // null — проверяем, true — API доступен, false — нет
  const [apiOk, setApiOk] = useState(null)
  const [campaignCount, setCampaignCount] = useState(null)

  useEffect(() => {
    let alive = true
    const check = () => {
      api
        .keitaroStatus()
        .then((r) => alive && setApiOk(r.ok))
        .catch(() => alive && setApiOk(false))
    }
    setApiOk(null)
    check()
    const timer = setInterval(check, STATUS_POLL_MS)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [apiKey])

  // Обновляем счётчик кампаний при навигации (после создания/редактирования)
  useEffect(() => {
    api
      .campaigns()
      .then((list) => setCampaignCount(list.length))
      .catch(() => setCampaignCount(null))
  }, [location.pathname])

  const statusClass =
    apiOk === null ? 'status-dot--pending' : apiOk ? 'status-dot--ok' : 'status-dot--bad'
  const statusText =
    apiOk === null ? 'Проверяем API…' : apiOk ? 'Keitaro API online' : 'Keitaro API недоступен'

  return (
    <aside className="sidebar">
      <Flex align="center" gap="2" className="sidebar__brand">
        <span className="sidebar__logo">
          <LightningBoltIcon width={18} height={18} />
        </span>
        <div>
          <Text size="2" weight="bold" as="div">
            Keitaro
          </Text>
          <Text size="1" color="gray" as="div">
            Campaign Manager
          </Text>
        </div>
      </Flex>

      <nav className="sidebar__nav">
        <NavLink to="/" end className="sidebar__link">
          <PlusIcon /> Создать кампанию
        </NavLink>
        <NavLink to="/campaigns" className="sidebar__link">
          <StackIcon /> Кампании
          {campaignCount !== null && (
            <Badge color="grass" variant="soft" radius="full" className="sidebar__badge">
              {campaignCount}
            </Badge>
          )}
        </NavLink>
        <NavLink to="/settings" className="sidebar__link">
          <GearIcon /> Настройки
        </NavLink>
      </nav>

      <div className="sidebar__footer">
        <Tooltip content={apiOk === false ? 'Проверьте Api-Key в настройках' : 'Пинг /api/keitaro/status'}>
          <Flex align="center" gap="2" className="sidebar__status">
            <span className={`status-dot ${statusClass}`} />
            <Text size="1" color="gray">
              {statusText}
            </Text>
          </Flex>
        </Tooltip>
        <a className="sidebar__admin-link" href={KEITARO_ADMIN_URL} target="_blank" rel="noreferrer">
          <ExternalLinkIcon /> Админка Keitaro
        </a>
      </div>
    </aside>
  )
}
