
import os
import io
import re
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "Consulta de Existencias y Ventas"
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "app.db"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "cambiar-esta-clave")

st.set_page_config(page_title=APP_TITLE, page_icon="📦", layout="wide")

COLUMN_ALIASES = {
    "codigo": ["CODIGO", "CODAMA", "COD_ARTICULO", "CODPRODUCTO", "SKU", "ITEM"],
    "tienda": ["TIENDA", "TIENAT", "COD_TIENDA", "SUCURSAL"],
    "existencia": ["EXIST", "EXISTENCIA", "STOCK", "CANT_EXISTENCIA", "INVENTARIO"],
    "nombre": ["NOMBRE", "DESCRIPCION", "DESC_ARTICULO", "PRODUCTO"],
    "categoria": ["CATEGORIA", "DEPARTAMENTO", "DEPTO"],
    "linea": ["LINEA", "SUBCATEGORIA"],
    "monto_venta": ["MONTO_VENTA", "VENTA", "VENTA_NETA", "MONTO"],
    "monto_devolucion": ["MONTO_DEVOLUCION", "DEVOLUCION"],
    "monto_anulacion": ["MONTO_ANULACION", "ANULACION"],
    "cantidad_venta": ["CANTIDAD_VENTA_UNIDADES", "CANTIDAD", "UNIDADES_VENDIDAS"],
    "cantidad_devolucion": ["CANTIDAD_DEVOLUCION_UNIDADES", "UNIDADES_DEVUELTAS"],
    "cantidad_anulacion": ["CANTIDAD_ANULACION_UNIDADES", "UNIDADES_ANULADAS"],
}

def normalize_col(value):
    value = str(value).strip().upper()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^A-Z0-9_]", "", value)
    return value

def find_column(df, logical_name, required=False):
    normalized = {normalize_col(c): c for c in df.columns}
    for alias in COLUMN_ALIASES[logical_name]:
        if normalize_col(alias) in normalized:
            return normalized[normalize_col(alias)]
    if required:
        raise ValueError(
            f"No se encontró la columna requerida '{logical_name}'. "
            f"Columnas disponibles: {', '.join(map(str, df.columns))}"
        )
    return None

def normalize_code(series):
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    return s.str.upper()

def parse_number(series):
    s = series.astype(str).str.strip()
    s = s.str.replace(r"[^\d,\.\-]", "", regex=True)

    def convert(v):
        if v in ("", "-", "nan", "None"):
            return 0.0
        if "," in v and "." in v:
            # El último separador se considera decimal.
            if v.rfind(",") > v.rfind("."):
                v = v.replace(".", "").replace(",", ".")
            else:
                v = v.replace(",", "")
        elif "," in v:
            parts = v.split(",")
            if len(parts[-1]) in (1, 2):
                v = v.replace(".", "").replace(",", ".")
            else:
                v = v.replace(",", "")
        try:
            return float(v)
        except ValueError:
            return 0.0

    return s.map(convert)

def read_csv_flexible(uploaded_file):
    raw = uploaded_file.getvalue()
    errors = []
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        for sep in (None, ";", ",", "\t"):
            try:
                return pd.read_csv(
                    io.BytesIO(raw),
                    encoding=enc,
                    sep=sep,
                    engine="python",
                    dtype=str,
                    keep_default_na=False,
                )
            except Exception as exc:
                errors.append(str(exc))
    raise ValueError("No fue posible leer el CSV.")

def read_excel_flexible(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".xls"):
        raise ValueError(
            "El archivo de existencias está en formato .xls antiguo. "
            "Expórtelo como .xlsx antes de cargarlo."
        )
    return pd.read_excel(io.BytesIO(uploaded_file.getvalue()), dtype=str)

def prepare_sales(df):
    codigo = find_column(df, "codigo", True)
    tienda = find_column(df, "tienda", False)
    nombre = find_column(df, "nombre", False)
    categoria = find_column(df, "categoria", False)
    linea = find_column(df, "linea", False)
    monto_venta = find_column(df, "monto_venta", True)
    monto_dev = find_column(df, "monto_devolucion", False)
    monto_anu = find_column(df, "monto_anulacion", False)
    cant_venta = find_column(df, "cantidad_venta", False)
    cant_dev = find_column(df, "cantidad_devolucion", False)
    cant_anu = find_column(df, "cantidad_anulacion", False)

    out = pd.DataFrame()
    out["codigo"] = normalize_code(df[codigo])
    out["tienda"] = normalize_code(df[tienda]) if tienda else ""
    out["nombre"] = df[nombre].astype(str).str.strip() if nombre else ""
    out["categoria"] = df[categoria].astype(str).str.strip() if categoria else ""
    out["linea"] = df[linea].astype(str).str.strip() if linea else ""
    out["venta_bruta"] = parse_number(df[monto_venta])
    out["devolucion"] = parse_number(df[monto_dev]) if monto_dev else 0.0
    out["anulacion"] = parse_number(df[monto_anu]) if monto_anu else 0.0
    # En el archivo fuente, devoluciones y anulaciones ya vienen con signo negativo.
    # Por eso deben sumarse a la venta, no restarse.
    out["venta_neta"] = out["venta_bruta"] + out["devolucion"] + out["anulacion"]
    out["unidades_venta"] = parse_number(df[cant_venta]) if cant_venta else 0.0
    out["unidades_devolucion"] = parse_number(df[cant_dev]) if cant_dev else 0.0
    out["unidades_anulacion"] = parse_number(df[cant_anu]) if cant_anu else 0.0
    out["unidades_netas"] = (
        out["unidades_venta"] - out["unidades_devolucion"] - out["unidades_anulacion"]
    )
    return out[out["codigo"] != ""]

def prepare_inventory(df, ignore_negatives=True):
    codigo = find_column(df, "codigo", True)
    tienda = find_column(df, "tienda", True)
    existencia = find_column(df, "existencia", True)
    nombre = find_column(df, "nombre", False)

    out = pd.DataFrame()
    out["codigo"] = normalize_code(df[codigo])
    out["tienda"] = normalize_code(df[tienda])
    out["existencia"] = parse_number(df[existencia])
    out["nombre_inventario"] = df[nombre].astype(str).str.strip() if nombre else ""
    if ignore_negatives:
        out = out[out["existencia"] >= 0]
    return out[out["codigo"] != ""]

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    return conn

def save_data(sales, inventory, sales_name, inventory_name):
    conn = get_conn()
    sales.to_sql("sales", conn, if_exists="replace", index=False)
    inventory.to_sql("inventory", conn, if_exists="replace", index=False)
    metadata = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "sales_file": sales_name,
        "inventory_file": inventory_name,
        "sales_rows": str(len(sales)),
        "inventory_rows": str(len(inventory)),
    }
    for key, value in metadata.items():
        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
            (key, value),
        )
    conn.commit()
    conn.close()

def load_metadata():
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM metadata").fetchall()
    conn.close()
    return dict(rows)

def table_exists(name):
    conn = get_conn()
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    conn.close()
    return row is not None

def load_tables():
    conn = get_conn()
    sales = pd.read_sql_query("SELECT * FROM sales", conn)
    inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    return sales, inventory

def query_codes(codes, sales, inventory):
    selected_sales = sales[sales["codigo"].isin(codes)].copy()
    selected_inv = inventory[inventory["codigo"].isin(codes)].copy()

    total_sales = float(sales["venta_neta"].sum())
    sales_summary = (
        selected_sales.groupby("codigo", as_index=False)
        .agg(
            nombre=("nombre", lambda x: next((v for v in x if str(v).strip()), "")),
            categoria=("categoria", lambda x: next((v for v in x if str(v).strip()), "")),
            linea=("linea", lambda x: next((v for v in x if str(v).strip()), "")),
            venta_neta=("venta_neta", "sum"),
            unidades_netas=("unidades_netas", "sum"),
        )
    )
    inv_summary = (
        selected_inv.groupby("codigo", as_index=False)
        .agg(
            existencia_total=("existencia", "sum"),
            tiendas_sin_existencia=("existencia", lambda x: int((x == 0).sum())),
            tiendas_con_una_unidad=("existencia", lambda x: int((x == 1).sum())),
        )
    )

    summary = pd.DataFrame({"codigo": codes})
    summary = summary.merge(sales_summary, on="codigo", how="left")
    summary = summary.merge(inv_summary, on="codigo", how="left")
    summary["venta_neta"] = summary["venta_neta"].fillna(0.0)
    summary["unidades_netas"] = summary["unidades_netas"].fillna(0.0)
    summary["existencia_total"] = summary["existencia_total"].fillna(0.0)
    summary["tiendas_sin_existencia"] = summary["tiendas_sin_existencia"].fillna(0).astype(int)
    summary["tiendas_con_una_unidad"] = summary["tiendas_con_una_unidad"].fillna(0).astype(int)
    summary["porcentaje_venta_total"] = (
        summary["venta_neta"] / total_sales * 100 if total_sales else 0.0
    )
    summary["estado"] = summary.apply(
        lambda r: "Sin datos"
        if r["venta_neta"] == 0 and r["existencia_total"] == 0
        else ("Agotado" if r["existencia_total"] == 0 else "Disponible"),
        axis=1,
    )

    detail = (
        selected_inv.groupby(["codigo", "tienda"], as_index=False)["existencia"].sum()
        .sort_values(["codigo", "tienda"])
    )
    return summary, detail, total_sales

def csv_download(df):
    return df.to_csv(index=False).encode("utf-8-sig")

st.title(APP_TITLE)

metadata = load_metadata()
if metadata:
    st.caption(
        f"Última actualización: {metadata.get('updated_at', '—')} · "
        f"Ventas: {metadata.get('sales_file', '—')} · "
        f"Existencias: {metadata.get('inventory_file', '—')}"
    )
else:
    st.warning("Todavía no se han cargado datos.")

tab_query, tab_admin = st.tabs(["Consulta", "Administración"])

with tab_query:
    if not (table_exists("sales") and table_exists("inventory")):
        st.info("Un administrador debe cargar primero los archivos diarios.")
    else:
        sales, inventory = load_tables()

        with st.form("consulta_form", clear_on_submit=False):
            query_text = st.text_input(
                "Ingrese uno o varios códigos",
                placeholder="Ejemplo: 3027003 o 3027003, 3027004, 3027005",
                help="Escriba o pegue los códigos separados por espacio, coma o punto y coma. Presione Enter para consultar.",
            )
            submitted = st.form_submit_button("Consultar", type="primary")

        codes = []
        for token in re.split(r"[\s,;]+", query_text.strip()):
            token = re.sub(r"\.0$", "", token.strip()).upper()
            if token and token not in codes:
                codes.append(token)

        if submitted:
            if not codes:
                st.warning("Ingrese al menos un código.")
            else:
                summary, detail, total_sales = query_codes(codes, sales, inventory)
                st.session_state["summary"] = summary
                st.session_state["detail"] = detail
                st.session_state["total_sales"] = total_sales

        if "summary" in st.session_state:
            summary = st.session_state["summary"].copy()
            detail = st.session_state["detail"].copy()
            total_sales = st.session_state["total_sales"]

            if len(summary) == 1:
                row = summary.iloc[0]
                product_name = row.get("nombre", "") or "Producto sin descripción"
                st.subheader(f"{row['codigo']} · {product_name}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Existencia total", f"{row['existencia_total']:,.0f}")
                m2.metric("% de la venta total", f"{row['porcentaje_venta_total']:.4f} %")
                m3.metric("Venta neta del código", f"Q {row['venta_neta']:,.2f}")
                m4.metric("Unidades netas", f"{row['unidades_netas']:,.0f}")
                st.caption(
                    f"Venta total utilizada como base: Q {total_sales:,.2f} · "
                    f"Estado: {row['estado']} · "
                    f"Tiendas en 0: {row['tiendas_sin_existencia']} · "
                    f"Tiendas en 1: {row['tiendas_con_una_unidad']}"
                )
            else:
                m1, m2, m3 = st.columns(3)
                m1.metric("Existencia combinada", f"{summary['existencia_total'].sum():,.0f}")
                m2.metric("Venta neta consultada", f"Q {summary['venta_neta'].sum():,.2f}")
                pct = (summary['venta_neta'].sum() / total_sales * 100) if total_sales else 0
                m3.metric("% conjunto de la venta", f"{pct:.4f} %")
                st.caption(
                    f"{len(summary)} códigos consultados · Venta total utilizada como base: Q {total_sales:,.2f}"
                )

            display = summary.rename(columns={
                "codigo": "Código",
                "nombre": "Producto",
                "categoria": "Categoría",
                "linea": "Línea",
                "venta_neta": "Venta neta",
                "unidades_netas": "Unidades netas",
                "existencia_total": "Existencia total",
                "tiendas_sin_existencia": "Tiendas en 0",
                "tiendas_con_una_unidad": "Tiendas en 1",
                "porcentaje_venta_total": "% venta total",
                "estado": "Estado",
            })
            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Venta neta": st.column_config.NumberColumn(format="Q %.2f"),
                    "% venta total": st.column_config.NumberColumn(format="%.4f %%"),
                    "Existencia total": st.column_config.NumberColumn(format="%.0f"),
                },
            )
            st.download_button(
                "Descargar resumen CSV",
                csv_download(display),
                "resultado_consulta.csv",
                "text/csv",
            )

            st.subheader("Existencia por tienda")
            if detail.empty:
                st.info("No hay detalle de existencias para los códigos consultados.")
            else:
                pivot = detail.pivot_table(
                    index="codigo", columns="tienda", values="existencia",
                    aggfunc="sum", fill_value=0
                ).reset_index()
                st.dataframe(pivot, use_container_width=True, hide_index=True)
                st.download_button(
                    "Descargar detalle CSV",
                    csv_download(detail),
                    "existencia_por_tienda.csv",
                    "text/csv",
                )

with tab_admin:
    st.subheader("Actualización diaria")
    password = st.text_input("Clave de administrador", type="password")
    if password:
        if password != ADMIN_PASSWORD:
            st.error("Clave incorrecta.")
        else:
            st.success("Acceso autorizado.")
            sales_file = st.file_uploader(
                "Archivo de ventas (.csv)", type=["csv"], key="sales_upload"
            )
            inventory_file = st.file_uploader(
                "Archivo de existencias (.xlsx)", type=["xlsx", "xls"], key="inventory_upload"
            )
            ignore_negatives = st.checkbox(
                "Excluir existencias negativas", value=True
            )

            if st.button(
                "Validar y publicar datos",
                type="primary",
                disabled=not (sales_file and inventory_file),
            ):
                try:
                    raw_sales = read_csv_flexible(sales_file)
                    raw_inventory = read_excel_flexible(inventory_file)
                    sales_data = prepare_sales(raw_sales)
                    inventory_data = prepare_inventory(raw_inventory, ignore_negatives)

                    if sales_data.empty:
                        raise ValueError("El archivo de ventas no contiene registros válidos.")
                    if inventory_data.empty:
                        raise ValueError("El archivo de existencias no contiene registros válidos.")

                    save_data(
                        sales_data,
                        inventory_data,
                        sales_file.name,
                        inventory_file.name,
                    )
                    st.success(
                        f"Datos publicados: {len(sales_data):,} registros de ventas y "
                        f"{len(inventory_data):,} registros de existencias."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"No se publicaron los datos: {exc}")

            with st.expander("Columnas reconocidas"):
                st.write(
                    "Ventas: CODIGO, TIENDA, MONTO_VENTA, MONTO_DEVOLUCION, "
                    "MONTO_ANULACION, CANTIDAD_VENTA_UNIDADES, NOMBRE, CATEGORIA y LINEA."
                )
                st.write(
                    "Existencias: CODAMA o CODIGO, TIENAT o TIENDA y EXIST o EXISTENCIA."
                )
