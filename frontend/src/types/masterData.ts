export interface SupplierItem {
  id: string
  nit: string
  dv: number
  name: string
  email: string
  bank: string
  account_type: string
  account_number: string
  status: string
  purchase_orders_count: number
  invoices_count: number
}

export interface PoLineDetail {
  id: string
  sku: string
  description: string
  quantity: number | string
  unit_price: number | string
  vat_rate: number | string
  line_subtotal: number | string
  quantity_received: number | string
}

export interface PurchaseOrderItem {
  id: string
  number: string
  supplier_id: string
  supplier_name: string
  supplier_nit: string
  date: string
  status: string
  total: number | string
  lines_count: number
  lines: PoLineDetail[]
}
