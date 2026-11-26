import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Badge,
  Box,
  Button,
  Callout,
  Card,
  Flex,
  Heading,
  Spinner,
  Text,
  TextField,
} from '@radix-ui/themes'
import {
  CheckCircledIcon,
  ExclamationTriangleIcon,
  Cross2Icon,
} from '@radix-ui/react-icons'
import { api } from '../api'
import GeoSelect from '../components/GeoSelect.jsx'
import OfferSelect from '../components/OfferSelect.jsx'

const PREFIX = 'test_negimatjanov_'

export default function CampaignCreate() {
  const [name, setName] = useState('')
  const [geoCode, setGeoCode] = useState('')
  const [offers, setOffers] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [created, setCreated] = useState(null)

  const canSubmit = name.trim() && geoCode && offers.length > 0 && !busy

  // Смена гео: офферы не под это гео убираем из выбора
  const changeGeo = (code) => {
    setGeoCode(code)
    setOffers((list) => list.filter((o) => o.country.includes(code)))
  }

  // Тоггл оффера в мультивыборе; если гео ещё не выбрано — берём из первого оффера
  const toggleOffer = (o) => {
    setOffers((list) =>
      list.some((x) => x.id === o.id) ? list.filter((x) => x.id !== o.id) : [...list, o],
    )
    if (!geoCode && o.country.length > 0) setGeoCode(o.country[0])
  }

  const removeOffer = (id) => setOffers((list) => list.filter((o) => o.id !== id))

  // Предварительные доли: поровну, остаток первым (как делает backend)
  const shareOf = (index) =>
    Math.floor(100 / offers.length) + (index < 100 % offers.length ? 1 : 0)

  const submit = async (e) => {
    e.preventDefault()
    if (!canSubmit) return
    setBusy(true)
    setError('')
    setCreated(null)
    try {
      const campaign = await api.createCampaign({
        name: name.trim(),
        geo_code: geoCode.toUpperCase(),
        offer_ids: offers.map((o) => o.id),
      })
      setCreated(campaign)
      setName('')
      setGeoCode('')
      setOffers([])
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Box className="content__inner page-enter">
      <Box>
        <Heading size="6" mb="1">
          Новая кампания
        </Heading>
        <Text color="gray" size="2">
          Два потока: первый ловит трафик из указанной страны и уводит на Google,
          второй отправляет остальных на выбранный оффер. Домен, группа и источник
          подставляются автоматически.
        </Text>
      </Box>

      <Card size="3">
        <form onSubmit={submit}>
          <Flex direction="column" gap="4" style={{ maxWidth: 480 }}>
            <Box>
              <Text as="div" size="2" weight="medium" mb="1">
                Название кампании
              </Text>
              <TextField.Root
                size="3"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="campaign1"
              >
                <TextField.Slot>
                  <Text size="2" color="gray">
                    {PREFIX}
                  </Text>
                </TextField.Slot>
              </TextField.Root>
            </Box>

            <Box>
              <Text as="div" size="2" weight="medium" mb="1">
                Гео (страна)
              </Text>
              <GeoSelect value={geoCode} onChange={changeGeo} />
            </Box>

            <Box>
              <Text as="div" size="2" weight="medium" mb="1">
                Офферы
              </Text>
              <OfferSelect
                multiple
                onSelect={toggleOffer}
                selectedIds={offers.map((o) => o.id)}
                geo={geoCode || null}
                placeholder="Добавить офферы — название или ID…"
              />
              {offers.length > 0 && (
                <Flex direction="column" gap="2" mt="2">
                  {offers.map((o, i) => (
                    <div key={o.id} className="picked-offer">
                      <Badge color="grass" variant="soft">
                        #{o.id}
                      </Badge>
                      <Text size="2" className="picked-offer__name">
                        {o.name.startsWith(`${o.id} `) ? o.name.slice(String(o.id).length + 1) : o.name}
                      </Text>
                      <Badge color="gray" variant="soft">
                        {o.country.join(', ')}
                      </Badge>
                      <Text size="2" color="gray" className="picked-offer__share">
                        {shareOf(i)}%
                      </Text>
                      <button
                        type="button"
                        className="picked-offer__remove"
                        aria-label={`Убрать оффер ${o.id}`}
                        onClick={() => removeOffer(o.id)}
                      >
                        <Cross2Icon />
                      </button>
                    </div>
                  ))}
                  {offers.length > 1 && (
                    <Text size="1" color="gray">
                      Доли распределятся поровну, потом их можно изменить в редакторе.
                    </Text>
                  )}
                </Flex>
              )}
            </Box>

            {error && (
              <Callout.Root color="red" className="callout-enter">
                <Callout.Icon>
                  <ExclamationTriangleIcon />
                </Callout.Icon>
                <Callout.Text>{error}</Callout.Text>
              </Callout.Root>
            )}

            <Box>
              <Button type="submit" size="3" disabled={!canSubmit}>
                {busy && <Spinner size="2" />}
                {busy ? 'Создаю…' : 'Создать кампанию'}
              </Button>
            </Box>
          </Flex>
        </form>
      </Card>

      {created && (
        <Callout.Root color="green" className="callout-enter">
          <Callout.Icon>
            <CheckCircledIcon />
          </Callout.Icon>
          <Callout.Text>
            Кампания <Text weight="bold">{created.name}</Text> создана (id в Keitaro:{' '}
            {created.keitaro_id}). Гео-поток: {created.geo_code} → Google · поток
            офферов: #{created.offer_stream_id}.{' '}
            <Link to={`/campaigns/${created.id}`}>Открыть в редакторе →</Link>
          </Callout.Text>
        </Callout.Root>
      )}
    </Box>
  )
}
