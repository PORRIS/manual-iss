import re
import sqlite3
import unicodedata

DB = "salida/manual_iss.db"
FACTOR = {"art65": 0.60,   # mismo especialista, misma vía de acceso
          "art66": 0.75,   # mismo especialista, distinta vía
          "art67": 0.60}   # distinta especialidad: una llamada por especialista
EXCEPCION_65 = {"468601", "591100", "652901", "667601", "669901"}


def liquidar_acto(items, regla="art65", anestesia=True, ayudante=False,
                  ajuste_pct=0.0, db=DB):
    """items: [(codigo, bilateral_bool), ...]. Devuelve (detalle, total) en pesos."""
    con = sqlite3.connect(db)
    tarifa = dict(con.execute("SELECT codigo_uvr, pesos_por_uvr FROM parametros"))
    filas = []
    for codigo, bilateral in items:
        r = con.execute(
            "SELECT articulo, codigo, descripcion, valor FROM procedimientos "
            "WHERE codigo=? AND articulo<=18 AND tipo='con_valor' AND unidad='UVR'",
            (str(codigo),)).fetchall()
        if len(r) != 1:
            raise ValueError(f"{codigo}: {len(r)} coincidencias en cirugías UVR: {r}")
        a, c, d, u = r[0]
        filas.append(dict(articulo=a, codigo=c, descripcion=d, uvr=u, bilateral=bilateral))
    con.close()

    if regla == "art65" and len(filas) > 1:
        raras = EXCEPCION_65 & {f["codigo"] for f in filas}
        if raras:
            print("AVISO art. 65: códigos con regla especial, revisar a mano:", raras)

    filas.sort(key=lambda f: -f["uvr"])          # el de mayor UVR va al 100%
    ajuste = 1 + ajuste_pct / 100                # p. ej. ISS 2001 +30% -> 30
    detalle, total = [], 0.0
    for n, f in enumerate(filas):
        f_orden = 1.0 if n == 0 else FACTOR[regla]
        # sin tildes: el Manual escribe «UNI Ó BILATERAL» (art. 64: esas no llevan el +75 %)
        desc = unicodedata.normalize("NFKD", f["descripcion"]).encode("ascii", "ignore").decode().upper()
        uni_bi = re.search(r"UNI\s*(?:O|/|Y/O)?\s*BILATERAL", desc)
        f_bil = 1.75 if f["bilateral"] and not uni_bi else 1.0   # art. 64
        base = f["uvr"] * f_orden * f_bil * ajuste
        cir = base * tarifa["S41101"]
        ane = base * tarifa["S41201"] if anestesia else 0.0
        ayu = base * tarifa["S41301"] if ayudante and f["uvr"] >= 50 else 0.0
        sub = round(cir + ane + ayu)
        total += sub
        detalle.append(dict(codigo=f["codigo"], descripcion=f["descripcion"][:50],
                            uvr=f["uvr"], factor=f_orden * f_bil, cirujano=round(cir),
                            anestesia=round(ane), ayudante=round(ayu), subtotal=sub))
    return detalle, total


if __name__ == "__main__":
    # solo para probar el formato: dos códigos reales de tu manual
    det, tot = liquidar_acto([("487702", False), ("386100", False)], regla="art65")
    for d in det:
        print(d)
    print("TOTAL honorarios:", tot)