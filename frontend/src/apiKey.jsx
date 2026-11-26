import { createContext, useContext, useMemo, useState } from 'react'

const STORAGE_KEY = 'keitaro_api_key'

const ApiKeyContext = createContext(null)

/**
 * Ключ Keitaro API, введённый пользователем на странице настроек.
 * Хранится только в localStorage браузера; пустое значение =
 * backend возьмёт ключ из своего .env.
 */
export function ApiKeyProvider({ children }) {
  const [apiKey, setApiKeyState] = useState(
    () => localStorage.getItem(STORAGE_KEY) ?? '',
  )

  const value = useMemo(
    () => ({
      apiKey,
      setApiKey: (key) => {
        const trimmed = (key ?? '').trim()
        if (trimmed) localStorage.setItem(STORAGE_KEY, trimmed)
        else localStorage.removeItem(STORAGE_KEY)
        setApiKeyState(trimmed)
      },
    }),
    [apiKey],
  )

  return <ApiKeyContext.Provider value={value}>{children}</ApiKeyContext.Provider>
}

export function useApiKey() {
  return useContext(ApiKeyContext)
}
