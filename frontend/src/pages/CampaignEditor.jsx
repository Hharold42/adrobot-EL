import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Badge, Box, Button, Callout, Flex, Heading, Skeleton, Spinner } from '@radix-ui/themes'
import {
  ArrowLeftIcon,
  CheckCircledIcon,
  ExclamationTriangleIcon,
  UpdateIcon,
} from '@radix-ui/react-icons'
import { api } from '../api'
import StreamCard from '../components/StreamCard.jsx'

const NOTICE_TTL_MS = 4000

export default function CampaignEditor() {
  const { id } = useParams()
  const [campaign, setCampaign] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api
      .campaign(id)
      .then(setCampaign)
      .catch((err) => setError(err.message))
  }, [id])

  // Success-уведомления гасим сами через несколько секунд
  useEffect(() => {
    if (!notice) return
    const timer = setTimeout(() => setNotice(''), NOTICE_TTL_MS)
    return () => clearTimeout(timer)
  }, [notice])

  // Действие над потоком: ответ — обновлённый поток, подменяем его в кампании
  const onStreamAction = useCallback(async (fn, successText) => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const updated = await fn()
      setCampaign((prev) => ({
        ...prev,
        streams: prev.streams.map((s) => (s.id === updated.id ? updated : s)),
      }))
      if (successText) setNotice(successText)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }, [])

  const fetchStreams = async () => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      setCampaign(await api.fetchStreams(id))
      setNotice('Потоки обновлены из Keitaro')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Box className="content__inner page-enter">
      <Link to="/campaigns" className="back-link">
        <ArrowLeftIcon /> ко всем кампаниям
      </Link>

      <Flex align="start" justify="between" gap="4" wrap="wrap" className="editor-head">
        <Box className="editor-head__title">
          {campaign ? (
            <>
              <Heading size="6" mb="1">
                {campaign.name}
              </Heading>
              <Flex gap="2" align="center">
                {campaign.geo_code && (
                  <Badge color="grass" variant="soft">
                    Гео {campaign.geo_code}
                  </Badge>
                )}
                {campaign.imported && (
                  <Badge color="gray" variant="soft">
                    импорт
                  </Badge>
                )}
                <Badge color="gray" variant="soft">
                  Keitaro #{campaign.keitaro_id}
                </Badge>
              </Flex>
            </>
          ) : (
            <Skeleton width="280px" height="28px" />
          )}
        </Box>
        <Button variant="soft" disabled={!campaign || busy} onClick={fetchStreams}>
          {busy ? <Spinner size="2" /> : <UpdateIcon />} Fetch streams
        </Button>
      </Flex>

      {error && (
        <Callout.Root color="red" className="callout-enter">
          <Callout.Icon>
            <ExclamationTriangleIcon />
          </Callout.Icon>
          <Callout.Text>{error}</Callout.Text>
        </Callout.Root>
      )}
      {notice && (
        <Callout.Root color="green" className="callout-enter">
          <Callout.Icon>
            <CheckCircledIcon />
          </Callout.Icon>
          <Callout.Text>{notice}</Callout.Text>
        </Callout.Root>
      )}

      {!campaign && !error && <Skeleton height="180px" />}

      {campaign?.streams.map((stream) => (
        <StreamCard key={stream.id} stream={stream} busy={busy} onAction={onStreamAction} />
      ))}
    </Box>
  )
}
