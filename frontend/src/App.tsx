import { Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Evals } from './pages/Evals'
import { InvoiceDetail } from './pages/InvoiceDetail'
import { Invoices } from './pages/Invoices'
import { Landing } from './pages/Landing'
import { Review } from './pages/Review'
import { Upload } from './pages/Upload'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Landing />} />
        <Route path="upload" element={<Upload />} />
        <Route path="invoices" element={<Invoices />} />
        <Route path="invoices/:id" element={<InvoiceDetail />} />
        <Route path="review" element={<Review />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="evals" element={<Evals />} />
      </Route>
    </Routes>
  )
}
