import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Badge,
  Box,
  Button,
  Callout,
  Card,
  Flex,
  Heading,
  Skeleton,
  Table,
  Text,
} from '@radix-ui/themes'
import { DownloadIcon, ExclamationTriangleIcon, PlusIcon } from '@radix-ui/react-icons'
import { api } from '../api'
import ImportDialog from '../components/ImportDialog.jsx'

export default function CampaignList() {
  const [campaigns, setCampaigns] = useState(null)
  const [error, setError] = useState('')

  const [importOpen, setImportOpen] = useState(false)

  const load = useCallback(() => {
    api
      .campaigns()
      .then(setCampaigns)
      .catch((err) => setError(err.message))
  }, [])

  useEffect(load, [load])

  return (
    <Box className="content__inner page-enter">
      <Flex align="center" justify="between">
        <Heading size="6">Кампании</Heading>
        <Flex gap="3">
          <Button variant="soft" color="gray" onClick={() => setImportOpen(true)}>
            <DownloadIcon /> Импорт из Keitaro
          </Button>
          <Button asChild variant="soft">
            <Link to="/">
              <PlusIcon /> Новая кампания
            </Link>
          </Button>
        </Flex>
      </Flex>

      <ImportDialog open={importOpen} onOpenChange={setImportOpen} onImported={load} />

      {error && (
        <Callout.Root color="red" className="callout-enter">
          <Callout.Icon>
            <ExclamationTriangleIcon />
          </Callout.Icon>
          <Callout.Text>{error}</Callout.Text>
        </Callout.Root>
      )}

      <Card size="2">
        <Table.Root className="campaign-table">
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeaderCell>Название</Table.ColumnHeaderCell>
              <Table.ColumnHeaderCell>Гео</Table.ColumnHeaderCell>
              <Table.ColumnHeaderCell>Keitaro ID</Table.ColumnHeaderCell>
              <Table.ColumnHeaderCell>Создана</Table.ColumnHeaderCell>
              <Table.ColumnHeaderCell />
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {campaigns === null &&
              [0, 1, 2].map((i) => (
                <Table.Row key={i}>
                  {Array.from({ length: 5 }).map((_, j) => (
                    <Table.Cell key={j}>
                      <Skeleton width={j === 0 ? '180px' : '60px'} height="16px" />
                    </Table.Cell>
                  ))}
                </Table.Row>
              ))}
            {campaigns?.map((c) => (
              <Table.Row key={c.id}>
                <Table.RowHeaderCell>
                  <div className="campaign-table__name">
                    <span title={c.name}>{c.name}</span>
                    {c.imported && (
                      <Badge size="1" color="gray" variant="soft">
                        импорт
                      </Badge>
                    )}
                  </div>
                </Table.RowHeaderCell>
                <Table.Cell>
                  {c.geo_code ? (
                    <Badge color="grass" variant="soft">
                      {c.geo_code}
                    </Badge>
                  ) : (
                    <Text color="gray">—</Text>
                  )}
                </Table.Cell>
                <Table.Cell>{c.keitaro_id}</Table.Cell>
                <Table.Cell>
                  <Text size="2" color="gray">
                    {new Date(c.created_at).toLocaleString('ru-RU', {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })}
                  </Text>
                </Table.Cell>
                <Table.Cell align="right">
                  <Button asChild variant="ghost" size="1">
                    <Link to={`/campaigns/${c.id}`}>Редактор</Link>
                  </Button>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>

        {campaigns?.length === 0 && (
          <Flex direction="column" align="center" gap="2" py="6">
            <Text color="gray">Пока пусто.</Text>
            <Button asChild variant="soft">
              <Link to="/">Создайте первую кампанию</Link>
            </Button>
          </Flex>
        )}
      </Card>
    </Box>
  )
}
