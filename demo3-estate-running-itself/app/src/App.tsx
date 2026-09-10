import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ChevronDown, Clock3, Database, FileText, Receipt, Search } from 'lucide-react'
import './App.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

type Invoice = {
  InvoiceId: number
  InvoiceNumber: string
  CustomerName: string
  Region: string
  InvoiceDate: string
  DueDate: string
  Status: string
  TotalAmount: number
}

type LookupResponse = {
  parameterMode: 'nvarchar' | 'varchar'
  databaseMs: number
  found: number
  invoices: Invoice[]
}

const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

function App() {
  const [invoiceNumber, setInvoiceNumber] = useState('INV-0004821993')
  const [result, setResult] = useState<LookupResponse | null>(null)
  const [queue, setQueue] = useState<Invoice[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [notice, setNotice] = useState('Look up an invoice to begin.')

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/invoices?status=Overdue&pageSize=12`)
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error('unavailable'))))
      .then((payload: { invoices: Invoice[] }) => setQueue(payload.invoices))
      .catch(() => setQueue([]))
  }, [])

  const lookup = async (event: FormEvent) => {
    event.preventDefault()
    const trimmed = invoiceNumber.trim()
    if (!trimmed) return

    setIsLoading(true)
    setNotice('Looking up invoice…')
    try {
      const response = await fetch(`${API_BASE_URL}/api/invoices/${encodeURIComponent(trimmed)}`)
      if (!response.ok) throw new Error(`Lookup returned ${response.status}`)
      const payload = (await response.json()) as LookupResponse
      setResult(payload)
      setNotice(payload.found > 0 ? 'Invoice found.' : 'No invoice with that number.')
    } catch (error) {
      setResult(null)
      setNotice(error instanceof Error ? error.message : 'Lookup failed.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#main">
          <span className="brand-mark"><Receipt size={19} /></span>
          Caldova
        </a>
        <nav className="primary-nav" aria-label="Primary navigation">
          <a href="#main">Evidence</a>
          <a className="active" href="#main">Operations</a>
          <a href="#main">Billing</a>
        </nav>
        <div className="profile">
          <span>Finance workspace</span>
          <span className="avatar">PL</span>
          <ChevronDown size={15} aria-hidden="true" />
        </div>
      </header>

      <main id="main" className="workspace">
        <p className="eyebrow">Accounts receivable</p>
        <h1>Invoice lookup</h1>
        <p>Find an invoice by number, then review the customer and payment status.</p>

        <form className="lookup-form" onSubmit={lookup}>
          <Search size={20} aria-hidden="true" />
          <input
            aria-label="Invoice number"
            value={invoiceNumber}
            onChange={(event) => setInvoiceNumber(event.target.value)}
            placeholder="INV-0000000001"
          />
          <button className="button" type="submit" disabled={isLoading}>
            {isLoading ? 'Searching' : 'Find invoice'}
          </button>
        </form>

        <dl className="metric-band">
          <div>
            <dt>Database time</dt>
            <dd>{result ? `${result.databaseMs.toFixed(0)} ms` : '--'}</dd>
          </div>
          <div>
            <dt>Parameter type</dt>
            <dd>{result ? result.parameterMode.toUpperCase() : '--'}</dd>
          </div>
          <div>
            <dt>Matches</dt>
            <dd>{result ? result.found : '--'}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd className="mono">{notice}</dd>
          </div>
        </dl>

        {result && result.invoices.length > 0 && (
          <section className="card invoice-detail">
            <h2>{result.invoices[0].InvoiceNumber}</h2>
            <div className="invoice-grid">
              <div><span>Customer</span><strong>{result.invoices[0].CustomerName}</strong></div>
              <div><span>Region</span><strong>{result.invoices[0].Region}</strong></div>
              <div><span>Status</span><strong>{result.invoices[0].Status}</strong></div>
              <div><span>Total</span><strong>{currency.format(result.invoices[0].TotalAmount)}</strong></div>
            </div>
          </section>
        )}

        <section className="card">
          <h2><FileText size={18} /> Overdue queue</h2>
          {queue.length === 0 ? (
            <p>No overdue invoices loaded.</p>
          ) : (
            <table className="invoice-table">
              <thead>
                <tr><th>Invoice</th><th>Customer</th><th>Due</th><th>Total</th></tr>
              </thead>
              <tbody>
                {queue.map((invoice) => (
                  <tr key={invoice.InvoiceId}>
                    <td className="mono">{invoice.InvoiceNumber}</td>
                    <td>{invoice.CustomerName}</td>
                    <td>{new Date(invoice.DueDate).toLocaleDateString()}</td>
                    <td>{currency.format(invoice.TotalAmount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </main>

      <footer className="workspace">
        <span><Database size={14} /> Caldova operations</span>
        <span><Clock3 size={14} /> Azure SQL</span>
      </footer>
    </div>
  )
}

export default App
