"""Genera el dataset sintético de facturas para el proyecto AP con IA.
Todas las empresas, NITs, cuentas y CUFEs son FICTICIOS.
"""
import csv, json, hashlib, io, random
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

random.seed(7)
OUT = Path(__file__).resolve().parent.parent / "data"
FACT = OUT / "facturas"
FACT.mkdir(parents=True, exist_ok=True)

# ---------- utilidades ----------
PESOS = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]

def dv_nit(nit: str) -> int:
    s = sum(int(d) * PESOS[i] for i, d in enumerate(reversed(nit)))
    r = s % 11
    return r if r in (0, 1) else 11 - r

def cop(v: float) -> str:
    return "$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def cufe(num, fecha, total, nit_emisor, nit_adq):
    base = f"{num}{fecha}{total:.2f}01{nit_emisor}{nit_adq}DEMO"
    return hashlib.sha384(base.encode()).hexdigest()

# ---------- maestros ----------
COMPRADOR = {"nit": "901555321", "razon_social": "Distribuciones Andinas Demo S.A.S.",
             "direccion": "Cra 7 # 71-21, Bogotá D.C."}
COMPRADOR["dv"] = dv_nit(COMPRADOR["nit"])

PROVEEDORES = [
    dict(id="P001", nit="900482113", razon_social="Papelería El Cóndor S.A.S.", ciudad="Bogotá",
         banco="Bancolombia", tipo_cuenta="Ahorros", cuenta="031-458921-77", email="facturacion@condor-demo.co",
         layout="A", prefijo="FEPC"),
    dict(id="P002", nit="901117654", razon_social="TecnoRed Soluciones S.A.S.", ciudad="Medellín",
         banco="Davivienda", tipo_cuenta="Corriente", cuenta="4569-0012-3381", email="cartera@tecnored-demo.co",
         layout="B", prefijo="TRS"),
    dict(id="P003", nit="800273946", razon_social="Limpieza Total del Valle Ltda.", ciudad="Cali",
         banco="Banco de Bogotá", tipo_cuenta="Corriente", cuenta="187-22451-9", email="fe@limpiezatotal-demo.co",
         layout="C", prefijo="LTV"),
    dict(id="P004", nit="901338820", razon_social="Café Montaña Alta S.A.S.", ciudad="Manizales",
         banco="BBVA", tipo_cuenta="Ahorros", cuenta="0013-0456-7788", email="ventas@montanaalta-demo.co",
         layout="A", prefijo="CMA"),
    dict(id="P005", nit="900915402", razon_social="Transportes Sabana Express S.A.S.", ciudad="Mosquera",
         banco="Banco de Occidente", tipo_cuenta="Corriente", cuenta="220-88314-2", email="facturas@sabanaexp-demo.co",
         layout="B", prefijo="TSE"),
    dict(id="P006", nit="901604587", razon_social="Muebles Nogal Diseño S.A.S.", ciudad="Bogotá",
         banco="Bancolombia", tipo_cuenta="Corriente", cuenta="677-332190-05", email="admin@nogal-demo.co",
         layout="C", prefijo="MND"),
]
for p in PROVEEDORES:
    p["dv"] = dv_nit(p["nit"]); p["estado"] = "ACTIVO"
PROV = {p["id"]: p for p in PROVEEDORES}

# ---------- órdenes de compra y recepciones ----------
OCS = {
 "OC-2026-0101": ("P001", [("PAP-001", "Resma papel carta 75g x500", 40, 18500, 19),
                           ("PAP-014", "Esfero tinta negra caja x12", 15, 14200, 19),
                           ("PAP-022", "Carpeta AZ oficio", 25, 9800, 19)]),
 "OC-2026-0102": ("P002", [("TEC-110", "Portátil 14\" Core i5 16GB RAM", 3, 3150000, 19),
                           ("TEC-205", "Monitor 24\" IPS Full HD", 3, 689000, 19),
                           ("TEC-301", "Base refrigerante para portátil", 3, 85000, 19)]),
 "OC-2026-0103": ("P004", [("CAF-001", "Café tostado molido 500g", 30, 24000, 5),
                           ("CAF-010", "Vasos compostables 9oz x50", 20, 11500, 19),
                           ("CAF-020", "Azúcar en sobres x200", 10, 16800, 19)]),
 "OC-2026-0104": ("P005", [("SRV-TR1", "Flete Bogotá-Medellín carga seca (viaje)", 4, 1850000, 19),
                           ("SRV-TR2", "Seguro de carga (por viaje)", 4, 95000, 19)]),
 "OC-2026-0105": ("P006", [("MUE-007", "Silla ergonómica malla con apoyabrazos", 8, 615000, 19),
                           ("MUE-015", "Escritorio en L 150x120 cm", 4, 1290000, 19)]),
 "OC-2026-0106": ("P003", [("LIM-003", "Desinfectante multiusos galón", 24, 32500, 19),
                           ("LIM-009", "Toallas de papel interfoliadas x150", 60, 7900, 19),
                           ("LIM-012", "Servicio de limpieza profunda oficina (m2)", 180, 4200, 19)]),
 "OC-2026-0107": ("P002", [("TEC-402", "Switch 24 puertos gigabit administrable", 2, 1420000, 19),
                           ("TEC-410", "Patch cord Cat6 2m", 50, 9500, 19)]),
 "OC-2026-0108": ("P001", [("PAP-031", "Tóner compatible impresora láser", 10, 145000, 19),
                           ("PAP-040", "Cuaderno argollado 100 hojas", 30, 8900, 19)]),
 "OC-2026-0109": ("P006", [("MUE-021", "Archivador metálico 4 gavetas", 3, 980000, 19)]),
 "OC-2026-0110": ("P004", [("CAF-030", "Máquina de café espresso semiautomática", 1, 2350000, 19)]),
  "OC-2026-0111": ("P004", [("CAF-001", "Café tostado molido 500g", 20, 24000, 5),
                           ("CAF-040", "Filtros de papel para cafetera x100", 15, 6200, 19)]),
}
# recepciones: por defecto se recibió todo; excepciones abajo
RECIBIDO = {(oc, l[0]): l[2] for oc, (_, lines) in OCS.items() for l in lines}
RECIBIDO[("OC-2026-0108", "PAP-031")] = 6   # solo llegaron 6 tóners

# ---------- definición de facturas ----------
def lineas_de(oc, overrides=None):
    overrides = overrides or {}
    out = []
    for sku, desc, qty, precio, iva in OCS[oc][1]:
        o = overrides.get(sku, {})
        out.append(dict(sku=sku, descripcion=desc, cantidad=o.get("cantidad", qty),
                        precio_unitario=o.get("precio", precio), iva_pct=iva))
    return out

FACTURAS = [
 # id, proveedor, numero, emision, vencimiento, oc, lineas, extras, decision, issues
 ("F01", "P001", "1045", "2026-09-01", "2026-10-01", "OC-2026-0101", lineas_de("OC-2026-0101"), {}, "APROBAR", []),
 ("F02", "P002", "20871", "2026-09-02", "2026-10-02", "OC-2026-0102", lineas_de("OC-2026-0102"), {}, "APROBAR", []),
 ("F03", "P004", "3312", "2026-09-03", "2026-09-18", "OC-2026-0103", lineas_de("OC-2026-0103"), {}, "APROBAR", []),
 ("F04", "P005", "7781", "2026-09-04", "2026-10-04", "OC-2026-0104", lineas_de("OC-2026-0104"), {}, "APROBAR", []),
 ("F05", "P006", "0598", "2026-09-05", "2026-10-20", "OC-2026-0105", lineas_de("OC-2026-0105"), {}, "APROBAR", []),
 ("F06", "P003", "11420", "2026-09-06", "2026-10-06", "OC-2026-0106",
  lineas_de("OC-2026-0106", {"LIM-003": {"cantidad": 12}, "LIM-009": {"cantidad": 30}}), {}, "APROBAR", []),
 ("F07", "P002", "20944", "2026-09-10", "2026-10-10", "OC-2026-0107",
  lineas_de("OC-2026-0107", {"TEC-402": {"precio": 1495000}}), {}, "REVISION", ["PRICE_MISMATCH"]),
 ("F08", "P001", "1071", "2026-09-11", "2026-10-11", "OC-2026-0108", lineas_de("OC-2026-0108"), {},
  "REVISION", ["QTY_EXCEEDS_RECEIPT"]),
 ("F09", "P001", "1045", "2026-09-01", "2026-10-01", "OC-2026-0101", lineas_de("OC-2026-0101"),
  {"archivo_alt": True}, "RECHAZAR", ["DUPLICATE_INVOICE"]),
 ("F10", "P003", "11502", "2026-09-12", "2026-10-12", "OC-2026-0106",
  lineas_de("OC-2026-0106", {"LIM-003": {"cantidad": 12}, "LIM-009": {"cantidad": 30}, "LIM-012": {"cantidad": 0}}),
  {"error_iva": True}, "RECHAZAR", ["ARITHMETIC_ERROR"]),
 ("F11", "P004", "3340", "2026-09-14", "2026-09-29", "OC-2026-0110", lineas_de("OC-2026-0110"),
  {"dv_malo": True}, "REVISION", ["INVALID_NIT_DV"]),
 ("F12", None, "552", "2026-09-15", "2026-10-15", None,
  [dict(sku="", descripcion="Kit de herramientas para mantenimiento", cantidad=5, precio_unitario=389000, iva_pct=19)],
  {"desconocido": True}, "REVISION", ["UNKNOWN_SUPPLIER", "MISSING_PO"]),
 ("F13", "P006", "0612", "2026-09-16", "2026-10-31", "OC-2026-0109", lineas_de("OC-2026-0109"),
  {"cuenta_nueva": ("Nequi Empresas", "Ahorros", "300-555-01-99")}, "REVISION", ["BANK_ACCOUNT_CHANGED"]),
 ("F14", "P005", "7802", "2026-09-18", "2026-10-18", None,
  [dict(sku="", descripcion="Flete urgente Bogotá-Cali (viaje)", cantidad=1, precio_unitario=2100000, iva_pct=19)],
  {}, "REVISION", ["MISSING_PO"]),
 ("F15", "P004", "3355", "2026-09-20", "2026-10-05", "OC-2026-0111", lineas_de("OC-2026-0111"),
  {"escaneada": True}, "APROBAR", []),
]

DESCONOCIDO = dict(nit="901777045", razon_social="Suministros Rápidos XYZ S.A.S.", ciudad="Soacha",
                   banco="Banco Caja Social", tipo_cuenta="Ahorros", cuenta="2400-1188-73",
                   email="ventas@srxyz-demo.co", layout="A", prefijo="SRX")
DESCONOCIDO["dv"] = dv_nit(DESCONOCIDO["nit"])

# ---------- render PDF ----------
def calc(lineas, error_iva=False):
    sub = 0; iva = 0; out = []
    for l in lineas:
        if l["cantidad"] == 0: continue
        s = l["cantidad"] * l["precio_unitario"]; i = round(s * l["iva_pct"] / 100, 2)
        sub += s; iva += i; out.append({**l, "subtotal_linea": s, "iva_linea": i})
    iva_impreso = round(iva * 1.19 if error_iva else iva, 2)  # error: IVA inflado
    total_impreso = sub + iva_impreso if not error_iva else sub + iva  # total no cuadra con IVA impreso
    return out, sub, iva_impreso, total_impreso

def draw(c, prov, fac, lineas, sub, iva, total, cufe_v, cuenta):
    W, H = letter; L = prov["layout"]
    nombre = prov["razon_social"]
    dv = fac["dv_impreso"]
    if L == "B":
        c.setFillColor(colors.HexColor("#1f3a5f")); c.rect(0, H - 110, W, 110, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 18); c.drawString(40, H - 50, nombre)
        c.setFont("Helvetica", 9)
        c.drawString(40, H - 68, f"NIT {prov['nit']}-{dv}  ·  {prov['ciudad']}  ·  {prov['email']}")
        c.setFont("Helvetica-Bold", 13); c.drawRightString(W - 40, H - 50, "FACTURA ELECTRÓNICA DE VENTA")
        c.setFont("Helvetica", 11); c.drawRightString(W - 40, H - 68, f"No. {prov['prefijo']}-{fac['numero']}")
        c.setFillColor(colors.black); y = H - 140
    elif L == "C":
        c.setFont("Helvetica-Bold", 11); c.drawString(40, H - 45, nombre.upper())
        c.setFont("Helvetica", 8)
        c.drawString(40, H - 58, f"Nit: {prov['nit']} - {dv}   Regimen: Responsable de IVA   {prov['ciudad']}")
        c.drawString(40, H - 69, f"Correo: {prov['email']}")
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(W - 40, H - 45, f"Factura Electronica {prov['prefijo']}{fac['numero']}")
        c.setLineWidth(0.5); c.line(40, H - 78, W - 40, H - 78); y = H - 100
    else:  # A
        c.setFont("Helvetica-Bold", 16); c.drawCentredString(W / 2, H - 45, nombre)
        c.setFont("Helvetica", 9)
        c.drawCentredString(W / 2, H - 60, f"NIT: {prov['nit']}-{dv}  |  {prov['ciudad']}, Colombia  |  {prov['email']}")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(W / 2, H - 82, f"FACTURA ELECTRÓNICA DE VENTA N° {prov['prefijo']} {fac['numero']}")
        y = H - 110
    c.setFont("Helvetica", 9)
    info = [f"Cliente: {COMPRADOR['razon_social']}", f"NIT cliente: {COMPRADOR['nit']}-{COMPRADOR['dv']}",
            f"Dirección: {COMPRADOR['direccion']}"]
    info2 = [f"Fecha de emisión: {fac['emision']}", f"Fecha de vencimiento: {fac['vencimiento']}",
             f"Orden de compra: {fac['oc'] or '—'}"]
    if L == "C":
        info2 = [f"F. Emision {fac['emision']}", f"F. Vence {fac['vencimiento']}",
                 f"Su pedido: {fac['oc'] or 'N/A'}"]
    for i, t in enumerate(info): c.drawString(40, y - i * 13, t)
    for i, t in enumerate(info2): c.drawString(330, y - i * 13, t)
    y -= 55
    cols = [40, 95, 330, 380, 470, 540]
    hdr = ["Código", "Descripción", "Cant.", "Vr. Unitario", "IVA %", "Total"] if L != "C" else \
          ["Ref", "Detalle", "Cant", "Precio", "IVA", "Valor"]
    c.setFillColor(colors.HexColor("#e8edf3") if L != "C" else colors.white)
    c.rect(38, y - 4, W - 76, 16, fill=1, stroke=0 if L != "C" else 1); c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8.5)
    for x, h in zip(cols, hdr):
        (c.drawRightString(x + 30, y, h) if h in ("Total", "Valor") else c.drawString(x, y, h))
    c.setFont("Helvetica", 8.5); y -= 18
    for l in lineas:
        c.drawString(cols[0], y, l["sku"] or "-")
        c.drawString(cols[1], y, l["descripcion"][:44])
        c.drawString(cols[2], y, str(l["cantidad"]))
        c.drawString(cols[3], y, cop(l["precio_unitario"]))
        c.drawString(cols[4] + 5, y, f"{l['iva_pct']}%")
        c.drawRightString(cols[5] + 30, y, cop(l["subtotal_linea"]))
        y -= 15
    y -= 10; c.line(330, y + 6, W - 40, y + 6)
    for lab, v in [("Subtotal", sub), ("IVA", iva), ("TOTAL A PAGAR", total)]:
        c.setFont("Helvetica-Bold" if lab.startswith("TOTAL") else "Helvetica", 9.5)
        c.drawString(360, y - 8, lab); c.drawRightString(W - 42, y - 8, cop(v)); y -= 16
    y -= 20; c.setFont("Helvetica", 8.5)
    c.drawString(40, y, f"Forma de pago: Crédito  ·  Medio: Transferencia")
    c.drawString(40, y - 12, f"Consignar a: {cuenta[0]} · Cuenta {cuenta[1]} No. {cuenta[2]} · Titular: {nombre}")
    c.setFont("Helvetica", 7)
    c.drawString(40, 70, "CUFE:"); c.drawString(70, 70, cufe_v[:64]); c.drawString(70, 61, cufe_v[64:])
    c.drawString(40, 48, "Autorización de numeración DIAN No. 18764000000000 (SIMULADA) · Documento ficticio para fines de portafolio")
    c.rect(W - 110, 40, 70, 70)  # recuadro QR
    c.setFont("Helvetica", 6); c.drawCentredString(W - 75, 73, "QR DIAN")

ground = []
for fid, pid, num, em, ve, oc, lineas, ext, decision, issues in FACTURAS:
    prov = DESCONOCIDO if ext.get("desconocido") else PROV[pid]
    lin, sub, iva, total = calc(lineas, ext.get("error_iva"))
    dv_imp = (prov["dv"] + 3) % 10 if ext.get("dv_malo") else prov["dv"]
    cuenta = ext.get("cuenta_nueva", (prov["banco"], prov["tipo_cuenta"], prov["cuenta"]))
    cf = cufe(f"{prov['prefijo']}{num}", em, total, prov["nit"], COMPRADOR["nit"])
    fac = dict(numero=num, emision=em, vencimiento=ve, oc=oc, dv_impreso=dv_imp)
    fname = f"{fid}_{prov['prefijo']}-{num}.pdf"
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=letter)
    c.setTitle(f"Factura {prov['prefijo']}-{num}"); draw(c, prov, fac, lin, sub, iva, total, cf, cuenta); c.save()
    if ext.get("escaneada"):
        import fitz
        from PIL import Image, ImageFilter
        doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
        pix = doc[0].get_pixmap(dpi=110)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
        img = img.rotate(1.4, expand=True, fillcolor=235).filter(ImageFilter.GaussianBlur(0.6))
        noise = Image.effect_noise(img.size, 18).convert("L")
        img = Image.blend(img, noise, 0.08).point(lambda p: min(255, p + 12))
        img.convert("RGB").save(FACT / fname, "PDF", resolution=110)
    else:
        (FACT / fname).write_bytes(buf.getvalue())
    ground.append(dict(
        archivo=fname, id=fid,
        esperado=dict(
            proveedor_nit=prov["nit"], proveedor_dv_impreso=dv_imp, proveedor_razon_social=prov["razon_social"],
            numero_factura=f"{prov['prefijo']}-{num}", fecha_emision=em, fecha_vencimiento=ve,
            orden_compra=oc, moneda="COP",
            lineas=[dict(sku=l["sku"] or None, descripcion=l["descripcion"], cantidad=l["cantidad"],
                         precio_unitario=l["precio_unitario"], iva_pct=l["iva_pct"],
                         subtotal=l["subtotal_linea"]) for l in lin],
            subtotal=sub, iva=iva, total=total, cufe=cf,
            cuenta_bancaria=dict(banco=cuenta[0], tipo=cuenta[1], numero=cuenta[2])),
        decision_esperada=decision, hallazgos_esperados=issues))

# ---------- escribir maestros ----------
with open(OUT / "proveedores.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "nit", "dv", "razon_social", "ciudad", "email", "banco", "tipo_cuenta", "cuenta", "estado"])
    for p in PROVEEDORES:
        w.writerow([p["id"], p["nit"], p["dv"], p["razon_social"], p["ciudad"], p["email"], p["banco"],
                    p["tipo_cuenta"], p["cuenta"], p["estado"]])

ocs_json = []
for oc, (pid, lines) in OCS.items():
    ocs_json.append(dict(numero=oc, proveedor_id=pid, proveedor_nit=PROV[pid]["nit"], fecha="2026-08-25",
                         moneda="COP", estado="ABIERTA",
                         lineas=[dict(sku=s, descripcion=d, cantidad=q, precio_unitario=p, iva_pct=i)
                                 for s, d, q, p, i in lines]))
(OUT / "ordenes_compra.json").write_text(json.dumps(ocs_json, ensure_ascii=False, indent=2), encoding="utf-8")

with open(OUT / "recepciones.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["orden_compra", "sku", "cantidad_recibida", "fecha_recepcion", "recibido_por"])
    for (oc, sku), q in RECIBIDO.items():
        w.writerow([oc, sku, q, "2026-08-30", "Almacén Central"])

(OUT / "ground_truth.json").write_text(json.dumps(dict(
    comprador=COMPRADOR,
    reglas=dict(tolerancia_precio_pct=2.0, tolerancia_total_cop=1.0,
                umbral_aprobacion_automatica_cop=20000000),
    facturas=ground), ensure_ascii=False, indent=2), encoding="utf-8")

print("OK", len(ground), "facturas")
for g in ground:
    print(g["id"], g["archivo"], g["decision_esperada"], g["hallazgos_esperados"], g["esperado"]["total"])
