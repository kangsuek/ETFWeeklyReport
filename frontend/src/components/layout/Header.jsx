import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="bg-white shadow-sm">
      <nav className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-2xl font-bold text-primary">
            ETF Weekly Report
          </Link>
          <div className="flex gap-6">
            <Link to="/" className="hover:text-primary">Dashboard</Link>
            <Link to="/compare" className="hover:text-primary">Compare</Link>
          </div>
        </div>
      </nav>
    </header>
  )
}
