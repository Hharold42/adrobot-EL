import { Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import CampaignCreate from './pages/CampaignCreate.jsx'
import CampaignList from './pages/CampaignList.jsx'
import CampaignEditor from './pages/CampaignEditor.jsx'
import Settings from './pages/Settings.jsx'

export default function App() {
  return (
    <div className="layout">
      <Sidebar />
      <main className="content">
        <Routes>
          <Route path="/" element={<CampaignCreate />} />
          <Route path="/campaigns" element={<CampaignList />} />
          <Route path="/campaigns/:id" element={<CampaignEditor />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
