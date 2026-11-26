import { useState } from 'react'
import {
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
  EyeClosedIcon,
  EyeOpenIcon,
  InfoCircledIcon,
  LockClosedIcon,
} from '@radix-ui/react-icons'
import { api } from '../api'
import { useApiKey } from '../apiKey.jsx'

export default function Settings() {
  const { apiKey, setApiKey } = useApiKey()
  const [value, setValue] = useState(apiKey)
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null) // { ok, text }

  const save = async () => {
    setBusy(true)
    setResult(null)
    setApiKey(value)
    // Пингуем Keitaro уже с новым ключом
    try {
      const status = await api.keitaroStatus()
      setResult(
        status.ok
          ? { ok: true, text: 'Ключ сохранён, Keitaro API отвечает.' }
          : { ok: false, text: `Ключ сохранён, но Keitaro не принимает его: ${status.detail}` },
      )
    } catch (err) {
      setResult({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  const reset = () => {
    setValue('')
    setApiKey('')
    setResult({ ok: true, text: 'Ключ убран из браузера — используется ключ из .env backend.' })
  }

  return (
    <Box className="content__inner page-enter">
      <Box>
        <Heading size="6" mb="1">
          Настройки
        </Heading>
        <Text color="gray" size="2">
          Ключ Keitaro API хранится только в localStorage вашего браузера и
          отправляется на backend заголовком X-Keitaro-Key.
        </Text>
      </Box>

      <Card size="3">
        <Flex direction="column" gap="4">
          <Box>
            <Text as="div" size="2" weight="medium" mb="1">
              Api-Key
            </Text>
            <TextField.Root
              type={visible ? 'text' : 'password'}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Оставьте пустым — будет использован ключ из .env"
              autoComplete="off"
            >
              <TextField.Slot>
                <LockClosedIcon />
              </TextField.Slot>
              <TextField.Slot side="right">
                <Button
                  type="button"
                  variant="ghost"
                  size="1"
                  onClick={() => setVisible((v) => !v)}
                  aria-label={visible ? 'Скрыть ключ' : 'Показать ключ'}
                >
                  {visible ? <EyeClosedIcon /> : <EyeOpenIcon />}
                </Button>
              </TextField.Slot>
            </TextField.Root>
          </Box>

          <Callout.Root color="gray" variant="soft">
            <Callout.Icon>
              <InfoCircledIcon />
            </Callout.Icon>
            <Callout.Text size="1">
              {apiKey
                ? 'Сейчас используется ключ из браузера.'
                : 'Сейчас используется ключ из .env backend.'}{' '}
              Ключ из админки Keitaro: раздел «API».
            </Callout.Text>
          </Callout.Root>

          {result && (
            <Callout.Root color={result.ok ? 'green' : 'red'} className="callout-enter">
              <Callout.Icon>
                {result.ok ? <CheckCircledIcon /> : <ExclamationTriangleIcon />}
              </Callout.Icon>
              <Callout.Text>{result.text}</Callout.Text>
            </Callout.Root>
          )}

          <Flex gap="3">
            <Button onClick={save} disabled={busy}>
              {busy && <Spinner size="2" />}
              Сохранить и проверить
            </Button>
            <Button variant="soft" color="gray" onClick={reset} disabled={busy}>
              Сбросить на .env
            </Button>
          </Flex>
        </Flex>
      </Card>
    </Box>
  )
}
