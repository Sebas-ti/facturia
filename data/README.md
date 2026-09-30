# Datos de prueba de FacturIA

Todo es **ficticio**: empresas, NITs, cuentas bancarias, CUFEs y la autorización DIAN. Los NITs de los proveedores tienen dígito de verificación válido según el algoritmo real.

Empresa compradora: **Distribuciones Andinas Demo S.A.S.** (NIT 901555321-1).

## Archivos

| Archivo | Contenido |
|---|---|
| `facturas/` | 15 facturas PDF en 3 diseños distintos (A, B, C) y 1 escaneada (F15: imagen rotada con ruido, prueba el OCR). |
| `proveedores.csv` | Maestro de 6 proveedores con NIT, DV y cuenta bancaria registrada. |
| `ordenes_compra.json` | 11 órdenes de compra con sus líneas (SKU, cantidad, precio, % IVA). |
| `recepciones.csv` | Cantidades recibidas en almacén por OC y SKU. |
| `ground_truth.json` | Lo que el sistema debe extraer de cada factura, más la decisión y los hallazgos esperados. Es la base de los evals. |

## Casos de prueba

| Factura | Caso | Decisión esperada |
|---|---|---|
| F01–F06 | Limpias, cuadran con OC y recepción | APROBAR |
| F07 | Precio del switch 5 % por encima de la OC | REVISION · `PRICE_MISMATCH` |
| F08 | Factura 10 tóners, solo se recibieron 6 | REVISION · `QTY_EXCEEDS_RECEIPT` |
| F09 | Duplicado de F01 (mismo número y proveedor, otro archivo); acumula la misma cantidad de F01 contra la misma OC | RECHAZAR · `DUPLICATE_INVOICE`, `QTY_EXCEEDS_RECEIPT` |
| F10 | IVA impreso mal calculado, el total no cuadra | RECHAZAR · `ARITHMETIC_ERROR` |
| F11 | DV del NIT impreso incorrecto | REVISION · `INVALID_NIT_DV` |
| F12 | Proveedor que no existe en el maestro y sin OC | REVISION · `UNKNOWN_SUPPLIER`, `MISSING_PO` |
| F13 | Cuenta bancaria distinta a la registrada (posible fraude) | REVISION · `BANK_ACCOUNT_CHANGED` |
| F14 | Servicio facturado sin orden de compra | REVISION · `MISSING_PO` |
| F15 | Factura limpia pero escaneada | APROBAR |

**Procesar en orden F01 → F15**: F09 solo es duplicado si F01 ya existe, y las cantidades se validan acumuladas por OC.

## Retos de extracción a propósito

- El número de factura aparece como `FEPC 1045`, `No. TRS-20871` o `LTV11502`; debe normalizarse a `PREFIJO-NUMERO`.
- Montos en formato colombiano: `$ 1.425.620,00` → `1425620.00`.
- El diseño C usa etiquetas abreviadas ("F. Vence", "Su pedido", "Ref", "Valor").
- Líneas con IVA de 5 % y de 19 % en la misma factura (F03, F15).

`scripts/generate_data.py` regenera todo; puedes agregar casos nuevos editándolo.
