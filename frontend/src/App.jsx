import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import SplashScreen from './components/SplashScreen/SplashScreen'
import TeamDashboard from './pages/TeamDashboard'
import AboutModal from './components/AboutModal'

export default function App() {
  const [showAbout, setShowAbout] = useState(false)

  // Show about modal on first visit
  useEffect(() => {
    if (!localStorage.getItem('lineup-lab-visited')) {
      setShowAbout(true)
      localStorage.setItem('lineup-lab-visited', '1')
    }
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SplashScreen onAbout={() => setShowAbout(true)} />} />
        <Route path="/team/:teamId" element={<TeamDashboard onAbout={() => setShowAbout(true)} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {showAbout && <AboutModal onClose={() => setShowAbout(false)} />}
    </BrowserRouter>
  )
}
