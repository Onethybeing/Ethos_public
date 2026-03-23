import { useState } from 'react'
import { Search, Database, FileText, Zap } from 'lucide-react'
import NarrativeAnalyzer from './components/NarrativeAnalyzer'
import SystemDashboard from './components/SystemDashboard'
import IntelligenceReports from './components/IntelligenceReports'
import './App.css'

/**
 * GOLDRET - Narrative Intelligence Platform
 * 
 * Core Use Cases:
 * 1. ANALYZE: Search narratives, detect mutations, trace outcomes
 * 2. MONITOR: System health, memory stats, ingestion controls
 * 3. REPORT: Generate strategic intelligence briefings
 */
function App() {
  const [activeView, setActiveView] = useState('analyze')

  const views = [
    { id: 'analyze', label: 'Analyze', icon: Search, description: 'Search & track narrative patterns' },
    { id: 'reports', label: 'Reports', icon: FileText, description: 'Generate intelligence briefings' },
    { id: 'system', label: 'System', icon: Database, description: 'Memory status & controls' },
  ]

  return (
    <div className="app">
      {/* Navigation */}
      <nav className="nav">
        <div className="container nav-content">
          <div className="nav-brand">
            <Zap size={20} />
            <span>GOLDRET</span>
          </div>

          <div className="nav-links">
            {views.map(view => (
              <button
                key={view.id}
                className={`nav-link ${activeView === view.id ? 'active' : ''}`}
                onClick={() => setActiveView(view.id)}
                title={view.description}
              >
                <view.icon size={16} />
                <span>{view.label}</span>
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="page">
        <div className="container">
          {activeView === 'analyze' && <NarrativeAnalyzer />}
          {activeView === 'reports' && <IntelligenceReports />}
          {activeView === 'system' && <SystemDashboard />}
        </div>
      </main>
    </div>
  )
}

export default App
