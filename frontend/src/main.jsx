import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Theme } from '@radix-ui/themes'
import '@radix-ui/themes/styles.css'
import App from './App.jsx'
import { ApiKeyProvider } from './apiKey.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Theme
      appearance="dark"
      accentColor="grass"
      grayColor="slate"
      radius="medium"
    >
      <BrowserRouter>
        <ApiKeyProvider>
          <App />
        </ApiKeyProvider>
      </BrowserRouter>
    </Theme>
  </StrictMode>,
)
