# Power Automate — Outlook → FacturIA (docs/spec.md §2, §10 Fase 5)

Flujo en la nube: cuando llega un correo con una factura en PDF adjunta, la
sube a `POST /api/invoices` para que el pipeline la procese.

No pude construir ni probar este flujo contra un tenant real (no tengo
acceso a Power Automate ni a una cuenta de Microsoft 365) — esta es una guía
paso a paso para armarlo en el portal, más el único fragmento de JSON que
hace falta pegar a mano (Power Automate no tiene un constructor visual para
`multipart/form-data`). Si algo no calza exactamente con lo que ves en el
portal, decime y lo ajustamos.

## Prerrequisitos

- El backend desplegado y accesible por HTTPS (`infra/main.bicep` + `deploy.yml`,
  tareas 5.3/5.4) — necesitás su URL pública (`<container-app-fqdn>`).
- La `API_KEY` del backend (la misma que protege `POST /api/invoices`, tarea 5.1).
- Una conexión de Outlook 365 autorizada en Power Automate (la cuenta que
  recibe las facturas de los proveedores).

## Límites del endpoint a tener en cuenta

- Solo acepta `Content-Type: application/pdf` en la parte del archivo — un
  adjunto que no sea PDF, o sin ese content-type, responde `422`.
- Tamaño máximo 5 MB (`MAX_UPLOAD_BYTES` en `app/api/invoices.py`) — un
  adjunto más pesado también responde `422`.
- Requiere el header `X-API-Key` con el valor correcto, o responde `401`.

## Pasos en el portal (make.powerautomate.com)

1. **Crear un flujo de nube automatizado**, nombre sugerido
   `FacturIA - Outlook a API`.
2. **Desencadenador:** `Cuando llega un nuevo correo electrónico (V3)`
   (conector Outlook 365).
   - Carpeta: `Bandeja de entrada` (o la que uses para facturas).
   - `Solo con datos adjuntos`: **Sí**.
   - Opcional, para no procesar todo lo que llega: filtrar por `Asunto
     contiene` (ej. "factura") o por dominio del remitente.
3. **Agregar una acción `Aplicar a cada uno`** sobre
   `Datos adjuntos` (`triggerOutputs()?['body/attachments']`).
4. Dentro del bucle, **agregar una `Condición`**:
   `termina con` → `Nombre de datos adjuntos actual` → `.pdf`
   (esto filtra adjuntos que no son la factura, ej. logos embebidos en la
   firma del correo).
5. En la rama **Si es verdadero**, **agregar una acción `HTTP`** (el
   conector premium `HTTP`, no `HTTP con Azure AD`):
   - **Método:** `POST`
   - **URI:** `https://<container-app-fqdn>/api/invoices`
   - **Encabezados:**
     - `X-API-Key`: tu API key (pegala directo, o referenciá una variable de
       entorno del entorno de Power Platform si ya usás ese patrón).
   - **Cuerpo:** acá es donde el diseñador visual no alcanza — armá la
     acción con cualquier URI/header temporal primero, después hacé clic en
     los `...` de esa acción → **`Ver en modo código` (Peek code)** y
     reemplazá toda la definición de la acción por el contenido de
     `http-action-body.json` de esta carpeta. Ajustá:
     - `<container-app-fqdn>` y `<api-key>` con los valores reales.
     - `"runAfter": {}` — dejalo vacío solo si esta es la primera (única)
       acción dentro de la rama "Si es verdadero"; si agregaste algo antes,
       Power Automate espera que referencie el nombre de esa acción previa
       (podés confirmarlo comparando con el `runAfter` que ya tenía la
       acción antes de reemplazarla).

   Este `$multipart` es una construcción del *Workflow Definition Language*
   que Logic Apps/Power Automate soportan para armar `multipart/form-data`
   sin tener que concatenar bytes a mano — el runtime arma el boundary y
   decodifica `contentBytes` (que ya viene en base64 desde el trigger) por
   vos.

6. **Guardar y probar** el flujo con un correo real de prueba (con un PDF
   pequeño adjunto) usando el botón "Probar" del diseñador.

## Qué falta que el usuario haga

- Reemplazar `<container-app-fqdn>` por la URL real una vez desplegada la
  5.3/5.4.
- Pegar la API key real (no commitear el flujo exportado con la key en
  texto plano — si exportás el flujo como solución, revisá que no quede
  ahí antes de compartirlo).
- Probar contra el backend real y ajustar el filtro de asunto/remitente
  según cómo lleguen las facturas reales.
- Una vez probado, exportar el flujo (`...` → `Exportar` → `Paquete (.zip)`)
  y guardarlo en esta carpeta junto con capturas del diseñador, tal como
  pide la estructura de `AGENTS.md`.
