
import io
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

APP_NAME = "Consulta de Inventario y Participación de Venta"
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "inventario.db"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Cambiar123")

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; max-width: 1450px;}
    [data-testid="stMetricValue"] {font-size: 2.3rem;}
    div[data-testid="stForm"] {border: 0; padding: 0;}
    .small-reference {
        color: #6b7280;
        font-size: 0.9rem;
        margin-top: -0.4rem;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

ALIASES = {
    "codigo": [
        "CODIGO", "CODAMA", "COD_ARTICULO", "CODPRODUCTO", "SKU", "ITEM",
        "COD_ART", "COD"
    ],
    "tienda": [
        "TIENDA", "TIENAT", "COD_TIENDA", "SUCURSAL", "ALMACEN",
        "CODALMACEN"
    ],
    "existencia": [
        "EXIST", "EXISTENCIA", "STOCK", "INVENTARIO", "EXIST_ACTUAL",
        "CANT_EXISTENCIA", "EXACAT"
    ],
    "nombre": [
        "NOMBRE", "DESCRIPCION", "DESC_ARTICULO", "PRODUCTO",
        "DESCRIPCION_ARTICULO"
    ],
    "categoria": ["CATEGORIA", "DEPARTAMENTO", "DEPTO"],
    "linea": ["LINEA", "SUBCATEGORIA"],
    "fecha": ["FECHA", "DATE", "FECHA_VENTA"],
    "dia": ["DIA"],
    "mes": ["MES"],
    "anno": ["ANNO", "ANO", "AÑO"],
    "monto_venta": ["MONTO_VENTA", "VENTA", "VENTA_BRUTA"],
    "monto_devolucion": ["MONTO_DEVOLUCION", "DEVOLUCION"],
    "monto_anulacion": ["MONTO_ANULACION", "ANULACION"],
    "cantidad_venta": [
        "CANTIDAD_VENTA_UNIDADES", "CANTIDAD_VENTA", "UNIDADES_VENDIDAS",
        "CANTIDAD"
    ],
    "cantidad_devolucion": [
        "CANTIDAD_DEVOLUCION_UNIDADES", "UNIDADES_DEVUELTAS"
    ],
    "cantidad_anulacion": [
        "CANTIDAD_ANULACION_UNIDADES", "UNIDADES_ANULADAS"
    ],
}


def normalize_header(value):
    value = str(value).strip().upper()
    replacements = str.maketrans("ÁÉÍÓÚÜÑ", "AEIOUUN")
    value = value.translate(replacements)
    value = re.sub(r"[\s\-./]+", "_", value)
    value = re.sub(r"[^A-Z0-9_]", "", value)
    return value.strip("_")


def find_column(df, logical_name, required=False):
    normalized = {normalize_header(col): col for col in df.columns}
    for alias in ALIASES[logical_name]:
        key = normalize_header(alias)
        if key in normalized:
            return normalized[key]
    if required:
        available = ", ".join(map(str, df.columns[:30]))
        raise ValueError(
            f"No se encontró la columna requerida '{logical_name}'. "
            f"Columnas detectadas: {available}"
        )
    return None


def clean_code(series):
    result = series.astype(str).str.strip()
    result = result.str.replace(r"\.0$", "", regex=True)
    result = result.str.replace(r"\s+", "", regex=True)
    return result.str.upper()


def clean_store(series):
    result = series.astype(str).str.strip()
    result = result.str.replace(r"\.0$", "", regex=True)
    return result.str.upper()


def parse_number(series):
    def convert(value):
        text = str(value).strip()
        if text.lower() in {"", "nan", "none", "null", "-"}:
            return 0.0

        text = re.sub(r"[^\d,.\-]", "", text)
        if not text or text == "-":
            return 0.0

        # En MovimientoDeVentas la coma es siempre separador decimal,
        # incluso cuando el reporte entrega 3 o 4 decimales (ej. 5804,9448).
        if "," in text and "." in text:
            # Si aparecen ambos separadores, el último se toma como decimal.
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(",", ".")

        try:
            return float(text)
        except ValueError:
            return 0.0

    return series.map(convert)


def read_csv_file(uploaded):
    raw = uploaded.getvalue()
    attempts = []
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        for separator in (",", ";", "\t"):
            try:
                df = pd.read_csv(
                    io.BytesIO(raw),
                    dtype=str,
                    encoding=encoding,
                    sep=separator,
                    keep_default_na=False,
                    low_memory=False,
                )
                if len(df.columns) >= 3:
                    return df
            except Exception as exc:
                attempts.append(str(exc))
    raise ValueError("No se pudo leer el archivo CSV de ventas.")


def detect_header_and_read_excel(uploaded):
    raw = uploaded.getvalue()
    extension = Path(uploaded.name).suffix.lower()
    engine = "xlrd" if extension == ".xls" else "openpyxl"

    book = pd.ExcelFile(io.BytesIO(raw), engine=engine)
    best = None

    for sheet in book.sheet_names:
        preview = pd.read_excel(
            io.BytesIO(raw),
            sheet_name=sheet,
            header=None,
            nrows=20,
            dtype=str,
            engine=engine,
        )

        for header_row in range(min(15, len(preview))):
            values = [normalize_header(v) for v in preview.iloc[header_row].tolist()]
            score = 0
            for logical in ("codigo", "tienda", "existencia"):
                alias_set = {normalize_header(a) for a in ALIASES[logical]}
                if any(v in alias_set for v in values):
                    score += 1

            if best is None or score > best["score"]:
                best = {
                    "sheet": sheet,
                    "header_row": header_row,
                    "score": score,
                }

    if not best or best["score"] < 2:
        raise ValueError(
            "No se identificó una hoja con columnas de código, tienda y existencia."
        )

    return pd.read_excel(
        io.BytesIO(raw),
        sheet_name=best["sheet"],
        header=best["header_row"],
        dtype=str,
        engine=engine,
    )


def build_dates(df):
    date_col = find_column(df, "fecha")
    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
        if dates.notna().any():
            return dates

    day_col = find_column(df, "dia")
    month_col = find_column(df, "mes")
    year_col = find_column(df, "anno")
    if day_col and month_col and year_col:
        values = (
            df[year_col].astype(str).str.strip()
            + "-"
            + df[month_col].astype(str).str.strip()
            + "-"
            + df[day_col].astype(str).str.strip()
        )
        return pd.to_datetime(values, errors="coerce")

    return pd.Series(pd.NaT, index=df.index)


def prepare_sales(df):
    codigo_col = find_column(df, "codigo", True)
    tienda_col = find_column(df, "tienda")
    nombre_col = find_column(df, "nombre")
    categoria_col = find_column(df, "categoria")
    linea_col = find_column(df, "linea")
    venta_col = find_column(df, "monto_venta", True)
    devolucion_col = find_column(df, "monto_devolucion")
    anulacion_col = find_column(df, "monto_anulacion")
    cant_venta_col = find_column(df, "cantidad_venta")
    cant_dev_col = find_column(df, "cantidad_devolucion")
    cant_anu_col = find_column(df, "cantidad_anulacion")

    out = pd.DataFrame(index=df.index)
    out["codigo"] = clean_code(df[codigo_col])
    out["tienda"] = clean_store(df[tienda_col]) if tienda_col else ""
    out["nombre"] = df[nombre_col].astype(str).str.strip() if nombre_col else ""
    out["categoria"] = (
        df[categoria_col].astype(str).str.strip() if categoria_col else ""
    )
    out["linea"] = df[linea_col].astype(str).str.strip() if linea_col else ""
    out["fecha"] = build_dates(df)

    out["venta"] = parse_number(df[venta_col])
    out["devolucion"] = (
        parse_number(df[devolucion_col]) if devolucion_col else 0.0
    )
    out["anulacion"] = (
        parse_number(df[anulacion_col]) if anulacion_col else 0.0
    )

    # El archivo fuente ya trae devoluciones y anulaciones con signo negativo.
    out["venta_neta"] = out["venta"] + out["devolucion"] + out["anulacion"]

    out["unidades_venta"] = (
        parse_number(df[cant_venta_col]) if cant_venta_col else 0.0
    )
    out["unidades_devolucion"] = (
        parse_number(df[cant_dev_col]) if cant_dev_col else 0.0
    )
    out["unidades_anulacion"] = (
        parse_number(df[cant_anu_col]) if cant_anu_col else 0.0
    )
    out["unidades_netas"] = (
        out["unidades_venta"]
        + out["unidades_devolucion"]
        + out["unidades_anulacion"]
    )

    out = out[out["codigo"].ne("")]
    out = out[out["codigo"].str.lower().ne("nan")]
    return out.reset_index(drop=True)


def prepare_inventory(df, exclude_negatives=True):
    codigo_col = find_column(df, "codigo", True)
    tienda_col = find_column(df, "tienda", True)
    existencia_col = find_column(df, "existencia", True)
    nombre_col = find_column(df, "nombre")

    out = pd.DataFrame(index=df.index)
    out["codigo"] = clean_code(df[codigo_col])
    out["tienda"] = clean_store(df[tienda_col])
    out["existencia"] = parse_number(df[existencia_col])
    out["nombre_inventario"] = (
        df[nombre_col].astype(str).str.strip() if nombre_col else ""
    )

    out = out[out["codigo"].ne("")]
    out = out[out["codigo"].str.lower().ne("nan")]
    if exclude_negatives:
        out = out[out["existencia"] >= 0]

    return out.reset_index(drop=True)


def connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    return conn


def table_exists(name):
    conn = connection()
    result = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    conn.close()
    return result is not None


def save_database(sales, inventory, sales_name, inventory_name):
    conn = connection()
    sales.to_sql("sales", conn, if_exists="replace", index=False)
    inventory.to_sql("inventory", conn, if_exists="replace", index=False)

    valid_dates = sales["fecha"].dropna()
    metadata = {
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "sales_file": sales_name,
        "inventory_file": inventory_name,
        "sales_rows": str(len(sales)),
        "inventory_rows": str(len(inventory)),
        "date_min": valid_dates.min().strftime("%d/%m/%Y") if len(valid_dates) else "No detectada",
        "date_max": valid_dates.max().strftime("%d/%m/%Y") if len(valid_dates) else "No detectada",
        "days": str(valid_dates.dt.normalize().nunique()) if len(valid_dates) else "0",
        "total_sales": str(float(sales["venta"].sum())),
    }

    for key, value in metadata.items():
        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
            (key, value),
        )

    conn.commit()
    conn.close()


def get_metadata():
    conn = connection()
    rows = conn.execute("SELECT key, value FROM metadata").fetchall()
    conn.close()
    return dict(rows)


@st.cache_data(show_spinner=False)
def load_database(updated_at):
    conn = connection()
    sales = pd.read_sql_query("SELECT * FROM sales", conn)
    inventory = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    sales["fecha"] = pd.to_datetime(sales["fecha"], errors="coerce")
    return sales, inventory


def first_nonempty(series):
    for value in series:
        value = str(value).strip()
        if value and value.lower() not in {"nan", "none"}:
            return value
    return ""


def calculate_results(codes, sales, inventory):
    total_sales = float(sales["venta"].sum())

    sales_selected = sales[sales["codigo"].isin(codes)].copy()
    inventory_selected = inventory[inventory["codigo"].isin(codes)].copy()

    sales_summary = (
        sales_selected.groupby("codigo", as_index=False)
        .agg(
            nombre=("nombre", first_nonempty),
            categoria=("categoria", first_nonempty),
            linea=("linea", first_nonempty),
            venta_neta=("venta_neta", "sum"),
            unidades_netas=("unidades_netas", "sum"),
        )
    )

    inventory_summary = (
        inventory_selected.groupby("codigo", as_index=False)
        .agg(
            existencia_total=("existencia", "sum"),
            tiendas_en_0=("existencia", lambda x: int((x == 0).sum())),
            tiendas_en_1=("existencia", lambda x: int((x == 1).sum())),
            tiendas_con_existencia=("existencia", lambda x: int((x > 0).sum())),
        )
    )

    result = pd.DataFrame({"codigo": codes})
    result = result.merge(sales_summary, on="codigo", how="left")
    result = result.merge(inventory_summary, on="codigo", how="left")

    numeric_cols = [
        "venta_neta", "unidades_netas", "existencia_total",
        "tiendas_en_0", "tiendas_en_1", "tiendas_con_existencia"
    ]
    for col in numeric_cols:
        result[col] = result[col].fillna(0)

    for col in ("nombre", "categoria", "linea"):
        result[col] = result[col].fillna("")

    result["porcentaje_venta_total"] = (
        result["venta_neta"] / total_sales * 100 if total_sales else 0
    )

    result["estado"] = result.apply(
        lambda row: (
            "Sin registros"
            if row["venta_neta"] == 0 and row["existencia_total"] == 0
            else "Agotado"
            if row["existencia_total"] == 0
            else "Disponible"
        ),
        axis=1,
    )

    detail = (
        inventory_selected.groupby(["codigo", "tienda"], as_index=False)
        .agg(existencia=("existencia", "sum"))
        .sort_values(["codigo", "tienda"])
    )

    return result, detail, total_sales


def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


metadata = get_metadata()

st.title(APP_NAME)

if metadata:
    st.caption(
        f"Datos actualizados: {metadata.get('updated_at', '—')} · "
        f"Período: {metadata.get('date_min', '—')} al "
        f"{metadata.get('date_max', '—')} · "
        f"{metadata.get('days', '0')} días"
    )
else:
    st.warning("Aún no se han publicado datos.")

query_tab, admin_tab = st.tabs(["Consulta", "Administración"])

with query_tab:
    if not (table_exists("sales") and table_exists("inventory")):
        st.info("Primero debe publicarse la información desde Administración.")
    else:
        sales, inventory = load_database(metadata.get("updated_at", ""))

        with st.form("query_form", clear_on_submit=False):
            query_text = st.text_input(
                "Código o códigos",
                placeholder="Escriba un código y presione Enter",
                help="Para varios códigos, sepárelos con coma, espacio o punto y coma.",
            )
            submitted = st.form_submit_button("Consultar", type="primary")

        if submitted:
            codes = []
            for token in re.split(r"[\s,;]+", query_text.strip()):
                token = re.sub(r"\.0$", "", token.strip()).upper()
                if token and token not in codes:
                    codes.append(token)

            if not codes:
                st.warning("Ingrese al menos un código.")
            else:
                result, detail, total_sales = calculate_results(
                    codes, sales, inventory
                )
                st.session_state["result"] = result
                st.session_state["detail"] = detail
                st.session_state["total_sales"] = total_sales

        if "result" in st.session_state:
            result = st.session_state["result"]
            detail = st.session_state["detail"]
            total_sales = st.session_state["total_sales"]

            if len(result) == 1:
                row = result.iloc[0]

                st.subheader(
                    f"{row['codigo']} — {row['nombre'] or 'Producto sin descripción'}"
                )

                main_1, main_2 = st.columns(2)
                main_1.metric(
                    "Existencia total",
                    f"{row['existencia_total']:,.0f}",
                )
                main_2.metric(
                    "% de la venta bruta total",
                    f"{row['porcentaje_venta_total']:.4f}%",
                )

                sec_1, sec_2, sec_3, sec_4 = st.columns(4)
                sec_1.metric("Venta neta del código", f"Q {row['venta_neta']:,.2f}")
                sec_2.metric("Unidades netas", f"{row['unidades_netas']:,.0f}")
                sec_3.metric("Tiendas en 0", f"{int(row['tiendas_en_0'])}")
                sec_4.metric("Tiendas en 1", f"{int(row['tiendas_en_1'])}")

                st.markdown(
                    f'<div class="small-reference">'
                    f'Venta bruta total usada como base: Q {total_sales:,.2f} · '
                    f'Estado: {row["estado"]} · '
                    f'Categoría: {row["categoria"] or "—"} · '
                    f'Línea: {row["linea"] or "—"}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.subheader("Resumen de códigos consultados")

            display = result.rename(
                columns={
                    "codigo": "Código",
                    "nombre": "Producto",
                    "categoria": "Categoría",
                    "linea": "Línea",
                    "existencia_total": "Existencia total",
                    "porcentaje_venta_total": "% venta bruta",
                    "venta_neta": "Venta neta",
                    "unidades_netas": "Unidades netas",
                    "tiendas_en_0": "Tiendas en 0",
                    "tiendas_en_1": "Tiendas en 1",
                    "tiendas_con_existencia": "Tiendas con existencia",
                    "estado": "Estado",
                }
            )

            columns = [
                "Código", "Producto", "Existencia total", "% venta bruta",
                "Venta neta", "Unidades netas", "Tiendas en 0",
                "Tiendas en 1", "Estado"
            ]

            st.dataframe(
                display[columns],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Existencia total": st.column_config.NumberColumn(format="%.0f"),
                    "% venta bruta": st.column_config.NumberColumn(format="%.4f %%"),
                    "Venta neta": st.column_config.NumberColumn(format="Q %.2f"),
                    "Unidades netas": st.column_config.NumberColumn(format="%.0f"),
                },
            )

            st.download_button(
                "Descargar resumen",
                data=to_csv_bytes(display),
                file_name="consulta_codigos.csv",
                mime="text/csv",
            )

            st.subheader("Existencia por tienda")
            if detail.empty:
                st.info("No hay registros de existencia para los códigos consultados.")
            else:
                pivot = detail.pivot_table(
                    index="codigo",
                    columns="tienda",
                    values="existencia",
                    aggfunc="sum",
                    fill_value=0,
                ).reset_index()

                st.dataframe(
                    pivot,
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    "Descargar existencia por tienda",
                    data=to_csv_bytes(detail),
                    file_name="existencia_por_tienda.csv",
                    mime="text/csv",
                )

with admin_tab:
    st.subheader("Publicación diaria")

    password = st.text_input("Clave de administrador", type="password")

    if password:
        if password != ADMIN_PASSWORD:
            st.error("Clave incorrecta.")
        else:
            st.success("Acceso autorizado.")

            sales_file = st.file_uploader(
                "Archivo de ventas",
                type=["csv"],
                help="Archivo CSV generado por el reporte de movimiento de ventas.",
            )
            inventory_file = st.file_uploader(
                "Archivo de existencias",
                type=["xls", "xlsx"],
                help="Se aceptan archivos Excel .xls y .xlsx.",
            )
            exclude_negatives = st.checkbox(
                "Excluir existencias negativas",
                value=True,
            )

            if sales_file and inventory_file:
                try:
                    raw_sales = read_csv_file(sales_file)
                    raw_inventory = detect_header_and_read_excel(inventory_file)
                    sales_ready = prepare_sales(raw_sales)
                    inventory_ready = prepare_inventory(
                        raw_inventory,
                        exclude_negatives=exclude_negatives,
                    )

                    valid_dates = sales_ready["fecha"].dropna()
                    total_sales_preview = float(sales_ready["venta"].sum())

                    st.markdown("#### Validación previa")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Registros de ventas", f"{len(sales_ready):,}")
                    col2.metric("Registros de existencias", f"{len(inventory_ready):,}")
                    col3.metric("Venta bruta total (base %)", f"Q {total_sales_preview:,.2f}")
                    col4.metric(
                        "Días detectados",
                        f"{valid_dates.dt.normalize().nunique() if len(valid_dates) else 0}",
                    )

                    if len(valid_dates):
                        st.caption(
                            f"Período detectado: "
                            f"{valid_dates.min().strftime('%d/%m/%Y')} al "
                            f"{valid_dates.max().strftime('%d/%m/%Y')}"
                        )

                    with st.expander("Ver comprobación de importes"):
                        checks = pd.DataFrame(
                            {
                                "Concepto": [
                                    "Ventas",
                                    "Devoluciones",
                                    "Anulaciones",
                                    "Venta neta",
                                ],
                                "Monto": [
                                    sales_ready["venta"].sum(),
                                    sales_ready["devolucion"].sum(),
                                    sales_ready["anulacion"].sum(),
                                    sales_ready["venta_neta"].sum(),
                                ],
                            }
                        )
                        st.dataframe(
                            checks,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Monto": st.column_config.NumberColumn(format="Q %.2f")
                            },
                        )
                        st.caption(
                            "Venta neta = ventas + devoluciones + anulaciones. "
                            "El reporte ya trae devoluciones y anulaciones con signo negativo."
                        )

                    if st.button("Publicar datos", type="primary"):
                        if sales_ready.empty:
                            st.error("El archivo de ventas quedó sin registros válidos.")
                        elif inventory_ready.empty:
                            st.error(
                                "El archivo de existencias quedó sin registros válidos."
                            )
                        else:
                            save_database(
                                sales_ready,
                                inventory_ready,
                                sales_file.name,
                                inventory_file.name,
                            )
                            st.cache_data.clear()
                            for key in ("result", "detail", "total_sales"):
                                st.session_state.pop(key, None)
                            st.success("Datos publicados correctamente.")
                            st.rerun()

                except Exception as exc:
                    st.error(f"No se pudo validar la carga: {exc}")
            else:
                st.info("Seleccione los dos archivos para validar la información.")
