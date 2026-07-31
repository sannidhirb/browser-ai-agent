import { useState, useEffect } from 'react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [view, setView] = useState('new') // 'new' or 'history'
  const [task, setTask] = useState('')
  const [startUrl, setStartUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [selectedReport, setSelectedReport] = useState(null)

  const runTask = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(`${API_URL}/run-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          start_url: startUrl,
        }),
      })

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError('Could not reach the agent server. Is it running?')
    } finally {
      setLoading(false)
    }
  }

  const loadHistory = async () => {
    setHistoryLoading(true)

    try {
      const response = await fetch(`${API_URL}/reports`)
      const data = await response.json()
      setHistory(data.reports)
    } catch (err) {
      setError(err.message)
    } finally {
      setHistoryLoading(false)
    }
  }

  const loadSingleReport = async (runId) => {
    const response = await fetch(`${API_URL}/reports/${runId}`)
    const data = await response.json()
    setSelectedReport(data)
  }

  useEffect(() => {
    if (view === 'history') {
      loadHistory()
      setSelectedReport(null)
    }
  }, [view])

  return (
    <>
      <div className="bg-blobs">
      </div>

      <div className="app-container">
        <div className="app-header">
          <span className="eyebrow">AI-Powered Browser Automation</span>
          <h1>Browser AI Agent</h1>
          <p>Give it a task and a starting URL, and watch it work.</p>
        </div>

        <div className="tabs">
          <button
            className={`tab-button ${view === 'new' ? 'active' : ''}`}
            onClick={() => setView('new')}
          >
            New Task
          </button>

          <button
            className={`tab-button ${view === 'history' ? 'active' : ''}`}
            onClick={() => setView('history')}
          >
            History
          </button>
        </div>

        {view === 'new' && (
          <>
            <div className="card">
              <div className="field">
                <label>Task</label>
                <input
                  type="text"
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  placeholder="e.g. Summarize what this website is about"
                />
              </div>

              <div className="field">
                <label>Starting URL</label>
                <input
                  type="text"
                  value={startUrl}
                  onChange={(e) => setStartUrl(e.target.value)}
                  placeholder="e.g. https://en.wikipedia.org/wiki/Web_scraping"
                />
              </div>

              <button
                className="run-button"
                onClick={runTask}
                disabled={loading || !task || !startUrl}
              >
                {loading ? 'Running...' : 'Run Task'}
              </button>

              {loading && (
                <div className="thinking-orb-row">
                  <div className="thinking-orb"></div>
                  <span>
                    Agent is working — this can take 15-40 seconds...
                  </span>
                </div>
              )}

              {error && (
                <p className="status-message error">{error}</p>
              )}
            </div>

            {result && (
              <div className="result-card">
                <h2>Result</h2>

                <p>
                  <span className={`status-badge ${result.status}`}>
                    {result.status === 'success'
                      ? 'Success'
                      : result.status.replace('_', ' ')}
                  </span>
                </p>

                <p>
                  <strong>Final Answer:</strong>{' '}
                  {result.final_answer || 'No answer reached.'}
                </p>

                <h3>Steps</h3>

                <ol className="steps-list">
                  {result.steps.map((step) => (
                    <li key={step.step}>
                      <strong>{step.action}</strong> — {step.reasoning}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </>
        )}

        {view === 'history' && (
          <div>
            {historyLoading && <p>Loading history...</p>}

            {!historyLoading && history.length === 0 && (
              <p>No tasks run yet.</p>
            )}

            {!selectedReport &&
              history.map((r) => (
                <div
                  key={r.run_id}
                  className="history-item"
                  onClick={() => loadSingleReport(r.run_id)}
                >
                  <p className="task-title">{r.task}</p>

                  <p className="task-meta">
                    <span className={`status-badge ${r.status}`}>
                      {r.status.replace('_', ' ')}
                    </span>{' '}
                    · {r.run_id}
                  </p>
                </div>
              ))}

            {selectedReport && (
              <div>
                <button
                  className="back-link"
                  onClick={() => setSelectedReport(null)}
                >
                  ← Back to list
                </button>

                <div className="history-detail">
                  <p>
                    <strong>Task:</strong> {selectedReport.task}
                  </p>

                  <p>
                    <span
                      className={`status-badge ${selectedReport.status}`}
                    >
                      {selectedReport.status.replace('_', ' ')}
                    </span>
                  </p>

                  <p>
                    <strong>Final Answer:</strong>{' '}
                    {selectedReport.final_answer || 'No answer reached.'}
                  </p>

                  <h3>Steps</h3>

                  <ol className="steps-list">
                    {selectedReport.steps.map((step) => (
                      <li key={step.step}>
                        <strong>{step.action}</strong> — {step.reasoning}
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}

export default App