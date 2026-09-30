import { Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { ComingSoon } from './pages/ComingSoon'
import { Landing } from './pages/Landing'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Landing />} />
        <Route path="upload" element={<ComingSoon title="Subir factura" />} />
        <Route path="invoices" element={<ComingSoon title="Bandeja de facturas" />} />
        <Route path="invoices/:id" element={<ComingSoon title="Detalle de factura" />} />
        <Route path="review" element={<ComingSoon title="Revisión" />} />
        <Route path="dashboard" element={<ComingSoon title="Dashboard" />} />
        <Route path="evals" element={<ComingSoon title="Evals" />} />
      </Route>
    </Routes>
  )
}
