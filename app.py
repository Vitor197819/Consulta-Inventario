
import io
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, inspect, text as sql_text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

APP_NAME = "Consulta de Inventario y Participación de Venta"
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "inventario.db"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Cambiar123")
FIXED_STORE = "6"

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

DB_HOST = os.getenv("DB_HOST", "").strip()
DB_PORT = os.getenv("DB_PORT", "5432").strip()
DB_NAME = os.getenv("DB_NAME", "postgres").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

USE_SEPARATE_DB_VARS = all([DB_HOST, DB_USER, DB_PASSWORD])

if USE_SEPARATE_DB_VARS:
    DB_URL = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
    )
elif DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    DB_URL = DATABASE_URL
else:
    DB_URL = f"sqlite:///{DB_PATH}"

@st.cache_resource
def get_engine():
    # Using URL.create avoids password parsing problems with @, #, %, :, etc.
    return create_engine(DB_URL, pool_pre_ping=True, poolclass=NullPool)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --app-blue: #0b2f5b;
        --app-blue-2: #1268dc;
        --app-green: #079455;
        --app-red: #d92d20;
        --app-muted: #667085;
        --app-border: #e4e7ec;
        --app-bg: #f8fafc;
    }

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .stApp {
        background: var(--app-bg);
    }

    .block-container {
        max-width: 760px;
        padding-top: 0.8rem;
        padding-bottom: 5rem;
    }

    h1 {
        font-size: 1.55rem !important;
        color: var(--app-blue);
        margin-bottom: 0.3rem !important;
    }

    h2, h3 {
        color: #101828;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    footer {
        visibility: hidden;
    }

    div[data-testid="stForm"] {
        border: 0;
        padding: 0;
    }

    .updated-box {
        background: #eaf4ff;
        border: 1px solid #cfe5ff;
        color: #175cd3;
        padding: 0.8rem 0.95rem;
        border-radius: 14px;
        margin: 0.6rem 0 1rem 0;
        font-size: 0.92rem;
        font-weight: 600;
    }

    .product-card {
        background: white;
        border: 1px solid var(--app-border);
        border-radius: 18px;
        padding: 1rem;
        margin-top: 0.75rem;
        box-shadow: 0 1px 3px rgba(16,24,40,.05);
    }

    .product-code {
        font-size: 1.25rem;
        font-weight: 800;
        color: #101828;
    }

    .product-name {
        font-size: 1rem;
        font-weight: 650;
        color: #344054;
        margin-top: 0.25rem;
        margin-bottom: 0.7rem;
    }

    .badge-ok, .badge-zero {
        display: inline-block;
        padding: 0.25rem 0.55rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
    }

    .badge-ok {
        background: #dcfae6;
        color: #067647;
    }

    .badge-zero {
        background: #fee4e2;
        color: #b42318;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.7rem;
        margin: 0.8rem 0;
    }

    .metric-card {
        background: white;
        border: 1px solid var(--app-border);
        border-radius: 16px;
        padding: 0.9rem;
        min-height: 94px;
    }

    .metric-card.primary-green {
        background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
        border-color: #bbf7d0;
    }

    .metric-card.primary-blue {
        background: linear-gradient(180deg, #eff8ff 0%, #ffffff 100%);
        border-color: #b2ddff;
    }

    .metric-value {
        font-size: 1.65rem;
        line-height: 1.05;
        font-weight: 800;
        color: #101828;
        word-break: break-word;
    }

    .primary-green .metric-value {
        color: var(--app-green);
    }

    .primary-blue .metric-value {
        color: var(--app-blue-2);
    }

    .metric-label {
        margin-top: 0.35rem;
        color: var(--app-muted);
        font-size: 0.82rem;
        font-weight: 600;
    }

    .store-list {
        background: white;
        border: 1px solid var(--app-border);
        border-radius: 18px;
        padding: 0.2rem 0.9rem;
        margin-top: 0.5rem;
    }

    .store-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.9rem 0.15rem;
        border-bottom: 1px solid #f0f1f3;
    }

    .store-row:last-child {
        border-bottom: 0;
    }

    .store-name {
        color: #344054;
        font-weight: 650;
    }

    .store-stock-ok {
        color: var(--app-green);
        font-weight: 800;
    }

    .store-stock-zero {
        color: var(--app-red);
        font-weight: 800;
    }

    .reference-box {
        background: white;
        border: 1px solid var(--app-border);
        border-radius: 14px;
        padding: 0.8rem;
        color: var(--app-muted);
        font-size: 0.82rem;
        margin-top: 0.5rem;
    }

    .multi-card {
        background: white;
        border: 1px solid var(--app-border);
        border-radius: 14px;
        padding: 0.85rem;
        margin-bottom: 0.55rem;
    }

    .multi-top {
        display: flex;
        justify-content: space-between;
        gap: 0.6rem;
        font-weight: 750;
        color: #101828;
    }

    .multi-sub {
        display: flex;
        justify-content: space-between;
        margin-top: 0.4rem;
        color: var(--app-muted);
        font-size: 0.85rem;
    }

    div.stButton > button,
    div.stDownloadButton > button,
    div[data-testid="stFormSubmitButton"] > button {
        width: 100%;
        min-height: 48px;
        border-radius: 12px;
        font-weight: 700;
    }

    div[data-baseweb="input"] > div {
        min-height: 50px;
        border-radius: 12px;
    }

    [data-testid="stFileUploaderDropzone"] {
        border-radius: 14px;
    }

    [data-testid="stTabs"] [role="tablist"] {
        gap: 0.35rem;
    }

    [data-testid="stTabs"] button[role="tab"] {
        flex: 1;
        min-height: 44px;
        font-weight: 700;
    }

    @media (max-width: 600px) {
        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            padding-top: 0.45rem;
        }

        h1 {
            font-size: 1.3rem !important;
        }

        .metric-grid {
            gap: 0.55rem;
        }

        .metric-card {
            padding: 0.75rem;
            min-height: 86px;
        }

        .metric-value {
            font-size: 1.45rem;
        }

        [data-testid="stDataFrame"] {
            font-size: 0.82rem;
        }
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
    """
    Crea una clave canónica para cruzar ventas y existencias.
    Para códigos numéricos elimina ceros a la izquierda:
    0123456, 00123456 y 123456 -> 123456.
    """
    result = series.astype(str).str.strip()
    result = result.str.replace(r"^'+", "", regex=True)
    result = result.str.replace(r"\.0+$", "", regex=True)
    result = result.str.replace(r"\s+", "", regex=True)
    result = result.str.upper()

    def normalize_one(value):
        value = str(value).strip().upper()
        if value.lower() in {"", "nan", "none"}:
            return ""
        if re.fullmatch(r"\d+", value):
            return value.lstrip("0") or "0"
        return value

    return result.map(normalize_one)

def display_code(value):
    """Muestra códigos numéricos a 7 dígitos sin afectar la clave de cruce."""
    value = str(value).strip()
    if re.fullmatch(r"\d+", value):
        return value.zfill(7)
    return value


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


def prepare_inventory(df, exclude_negatives=True, default_store=""):
    codigo_col = find_column(df, "codigo", True)
    tienda_col = find_column(df, "tienda", False)
    existencia_col = find_column(df, "existencia", True)
    nombre_col = find_column(df, "nombre")

    out = pd.DataFrame(index=df.index)
    out["codigo"] = clean_code(df[codigo_col])

    if tienda_col:
        out["tienda"] = clean_store(df[tienda_col])
    else:
        # Algunos reportes de existencias son específicos de una sola tienda
        # y no incluyen columna TIENDA/TIENAT. En ese caso usamos la tienda
        # detectada en el archivo de ventas.
        out["tienda"] = str(default_store).strip()

    out["existencia"] = parse_number(df[existencia_col])
    out["nombre_inventario"] = (
        df[nombre_col].astype(str).str.strip() if nombre_col else ""
    )

    out = out[out["codigo"].ne("")]
    out = out[out["codigo"].str.lower().ne("nan")]

    if exclude_negatives:
        out = out[out["existencia"] >= 0]

    return out.reset_index(drop=True)


def initialize_database():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sql_text(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT
                )
                """
            )
        )


def table_exists(name):
    initialize_database()
    return inspect(get_engine()).has_table(name)


def aggregate_sales_for_storage(sales):
    sales = sales[sales["tienda"].astype(str) == FIXED_STORE].copy()
    if sales.empty:
        raise ValueError("El archivo de ventas no contiene registros de la Tienda 6.")

    return (
        sales.groupby("codigo", as_index=False)
        .agg(
            tienda=("tienda", "first"),
            nombre=("nombre", first_nonempty),
            categoria=("categoria", first_nonempty),
            linea=("linea", first_nonempty),
            venta=("venta", "sum"),
            devolucion=("devolucion", "sum"),
            anulacion=("anulacion", "sum"),
            venta_neta=("venta_neta", "sum"),
            unidades_venta=("unidades_venta", "sum"),
            unidades_devolucion=("unidades_devolucion", "sum"),
            unidades_anulacion=("unidades_anulacion", "sum"),
            unidades_netas=("unidades_netas", "sum"),
        )
    )


def aggregate_inventory_for_storage(inventory):
    inventory = inventory.copy()
    inventory["tienda"] = FIXED_STORE
    return (
        inventory.groupby("codigo", as_index=False)
        .agg(
            tienda=("tienda", "first"),
            existencia=("existencia", "sum"),
            nombre_inventario=("nombre_inventario", first_nonempty),
        )
    )


def save_database(sales, inventory, sales_name, inventory_name):
    initialize_database()
    engine = get_engine()

    sales_t6 = sales[sales["tienda"].astype(str) == FIXED_STORE].copy()
    if sales_t6.empty:
        raise ValueError("No se encontraron ventas de la Tienda 6.")

    valid_dates = sales_t6["fecha"].dropna()
    total_gross = float(sales_t6["venta"].sum())

    sales_db = aggregate_sales_for_storage(sales_t6)
    inventory_db = aggregate_inventory_for_storage(inventory)

    sales_tmp = "sales_upload_tmp"
    inventory_tmp = "inventory_upload_tmp"

    sales_db.to_sql(sales_tmp, engine, if_exists="replace", index=False, method="multi", chunksize=1000)
    inventory_db.to_sql(inventory_tmp, engine, if_exists="replace", index=False, method="multi", chunksize=1000)

    valid_dates = sales_t6["fecha"].dropna()
    metadata = {
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "sales_file": sales_name,
        "inventory_file": inventory_name,
        "sales_rows": str(len(sales_db)),
        "inventory_rows": str(len(inventory_db)),
        "date_min": valid_dates.min().strftime("%d/%m/%Y") if len(valid_dates) else "No detectada",
        "date_max": valid_dates.max().strftime("%d/%m/%Y") if len(valid_dates) else "No detectada",
        "days": str(valid_dates.dt.normalize().nunique()) if len(valid_dates) else "0",
        "total_sales": str(total_gross),
    }

    with engine.begin() as conn:
        conn.execute(sql_text("DROP TABLE IF EXISTS sales"))
        conn.execute(sql_text("ALTER TABLE sales_upload_tmp RENAME TO sales"))
        conn.execute(sql_text("DROP TABLE IF EXISTS inventory"))
        conn.execute(sql_text("ALTER TABLE inventory_upload_tmp RENAME TO inventory"))

        for key, value in metadata.items():
            conn.execute(
                sql_text(
                    """
                    INSERT INTO metadata(key, value)
                    VALUES (:key, :value)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                    """
                ),
                {"key": key, "value": value},
            )


def get_metadata():
    initialize_database()
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sql_text("SELECT key, value FROM metadata")).fetchall()
    return dict(rows)


@st.cache_data(show_spinner=False)
def load_database(updated_at):
    engine = get_engine()
    sales = pd.read_sql_query(sql_text("SELECT * FROM sales"), engine)
    inventory = pd.read_sql_query(sql_text("SELECT * FROM inventory"), engine)
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

st.title("📦 Inventario Tienda 6")

if metadata:
    st.markdown(
        f"""
        <div class="updated-box">
            Datos actualizados: {metadata.get('updated_at', '—')}<br>
            Período: {metadata.get('date_min', '—')} al {metadata.get('date_max', '—')}
            · {metadata.get('days', '0')} días
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.warning("Aún no se han publicado datos.")

query_tab, admin_tab = st.tabs(["🔎 Consulta", "⚙️ Administración"])

with query_tab:
    if not (table_exists("sales") and table_exists("inventory")):
        st.info("Primero debe publicarse la información desde Administración.")
    else:
        sales, inventory = load_database(metadata.get("updated_at", ""))

        with st.form("query_form", clear_on_submit=False):
            query_text = st.text_input(
                "Consultar código",
                placeholder="Escribe un código y presiona Enter",
                help="También puedes pegar varios códigos separados por coma, espacio o punto y coma.",
            )
            submitted = st.form_submit_button("🔎 Consultar", type="primary")

        if submitted:
            codes = []
            for token in re.split(r"[\s,;]+", query_text.strip()):
                token = re.sub(r"\.0+$", "", token.strip()).upper()
                token = re.sub(r"^'+", "", token)
                token = re.sub(r"\s+", "", token)
                if re.fullmatch(r"\d+", token):
                    token = token.lstrip("0") or "0"
                if token and token not in codes:
                    codes.append(token)

            if not codes:
                st.warning("Ingresa al menos un código.")
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
                badge_class = "badge-zero" if row["existencia_total"] == 0 else "badge-ok"
                badge_text = "Agotado" if row["existencia_total"] == 0 else "Disponible"

                product_html = (
                    f'<div class="product-card">'
                    f'<div><span class="product-code">{display_code(row["codigo"])}</span>'
                    f'<span class="{badge_class}" style="float:right">{badge_text}</span></div>'
                    f'<div class="product-name">{row["nombre"] or "Producto sin descripción"}</div>'
                    f'<div class="metric-grid">'
                    f'<div class="metric-card primary-green"><div class="metric-value">{row["existencia_total"]:,.0f}</div><div class="metric-label">Existencia total</div></div>'
                    f'<div class="metric-card primary-blue"><div class="metric-value">{row["porcentaje_venta_total"]:.4f}%</div><div class="metric-label">% participación en venta</div></div>'
                    f'<div class="metric-card"><div class="metric-value" style="font-size:1.25rem">Q {row["venta_neta"]:,.2f}</div><div class="metric-label">Venta del código</div></div>'
                    f'<div class="metric-card"><div class="metric-value" style="font-size:1.25rem">{row["unidades_netas"]:,.0f}</div><div class="metric-label">Unidades vendidas</div></div>'
                    f'<div class="metric-card"><div class="metric-value" style="font-size:1.25rem;color:#d92d20">{int(row["tiendas_en_0"])}</div><div class="metric-label">Tiendas en 0</div></div>'
                    f'<div class="metric-card"><div class="metric-value" style="font-size:1.25rem;color:#b54708">{int(row["tiendas_en_1"])}</div><div class="metric-label">Tiendas en 1</div></div>'
                    f'</div></div>'
                )
                st.markdown(product_html, unsafe_allow_html=True)

                st.markdown("### Existencia por tienda")
                code_detail = detail[detail["codigo"] == row["codigo"]].copy()
                if code_detail.empty:
                    st.info("No hay registros de existencia para este código.")
                else:
                    rows_html = []
                    for _, store_row in code_detail.iterrows():
                        stock = float(store_row["existencia"])
                        stock_class = "store-stock-zero" if stock <= 0 else "store-stock-ok"
                        rows_html.append(
                            f'<div class="store-row"><span class="store-name">Tienda {store_row["tienda"]}</span>'
                            f'<span class="{stock_class}">{stock:,.0f} uds.</span></div>'
                        )
                    st.markdown(
                        '<div class="store-list">' + "".join(rows_html) + "</div>",
                        unsafe_allow_html=True,
                    )

                with st.expander("Ver detalles"):
                    detail_html = (
                        f'<div class="reference-box">'
                        f'<b>Venta bruta total usada como base:</b> Q {total_sales:,.2f}<br>'
                        f'<b>Categoría:</b> {row["categoria"] or "—"}<br>'
                        f'<b>Línea:</b> {row["linea"] or "—"}<br>'
                        f'<b>Estado:</b> {row["estado"]}'
                        f'</div>'
                    )
                    st.markdown(detail_html, unsafe_allow_html=True)

            else:
                st.markdown(f"### {len(result)} códigos encontrados")
                for _, row in result.iterrows():
                    stock_color = "#d92d20" if row["existencia_total"] <= 0 else "#079455"
                    multi_html = (
                        f'<div class="multi-card">'
                        f'<div class="multi-top"><span>{display_code(row["codigo"])}</span>'
                        f'<span style="color:{stock_color}">{row["existencia_total"]:,.0f} uds.</span></div>'
                        f'<div style="color:#475467;margin-top:.25rem">{row["nombre"] or "Sin descripción"}</div>'
                        f'<div class="multi-sub"><span>% venta: {row["porcentaje_venta_total"]:.4f}%</span>'
                        f'<span>Q {row["venta_neta"]:,.2f}</span></div>'
                        f'</div>'
                    )
                    st.markdown(multi_html, unsafe_allow_html=True)

                with st.expander("Ver tabla completa"):
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
                    st.dataframe(
                        display[
                            ["Código", "Producto", "Existencia total", "% venta bruta", "Venta neta"]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                display_download = result.rename(
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
                if "Código" in display_download.columns:
                    display_download["Código"] = display_download["Código"].map(display_code)

                st.download_button(
                    "⬇️ Descargar resultados",
                    data=to_csv_bytes(display_download),
                    file_name="consulta_codigos.csv",
                    mime="text/csv",
                )

with admin_tab:
    st.subheader("Actualización de datos")
    st.caption("Carga los archivos. La app usa únicamente Tienda 6 y guarda los datos consolidados en Supabase.")

    password = st.text_input("Clave de administrador", type="password")

    if password:
        if password != ADMIN_PASSWORD:
            st.error("Clave incorrecta.")
        else:
            st.success("Acceso autorizado.")

            sales_file = st.file_uploader(
                "1. Archivo de ventas (.csv)",
                type=["csv"],
                help="Archivo CSV de movimiento de ventas.",
            )
            inventory_file = st.file_uploader(
                "2. Archivo de existencias (.xls o .xlsx)",
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
                    sales_ready = sales_ready[sales_ready["tienda"].astype(str) == FIXED_STORE].copy()

                    if sales_ready.empty:
                        raise ValueError("El archivo de ventas no contiene datos de la Tienda 6.")

                    stores = [FIXED_STORE]

                    inventory_ready = prepare_inventory(
                        raw_inventory,
                        exclude_negatives=exclude_negatives,
                        default_store=FIXED_STORE,
                    )
                    inventory_ready["tienda"] = FIXED_STORE

                    valid_dates = sales_ready["fecha"].dropna()
                    total_sales_preview = float(sales_ready["venta"].sum())

                    st.success(
                        "Modo Tienda 6: ventas filtradas automáticamente a Tienda 6 "
                        "y existencias asignadas a Tienda 6."
                    )

                    st.markdown("### Validación previa")
                    c1, c2 = st.columns(2)
                    c1.metric("Venta bruta base %", f"Q {total_sales_preview:,.2f}")
                    c2.metric("Días detectados", f"{valid_dates.dt.normalize().nunique() if len(valid_dates) else 0}")

                    c3, c4 = st.columns(2)
                    c3.metric("Códigos con venta", f"{sales_ready['codigo'].nunique():,}")
                    c4.metric("Códigos en existencia", f"{inventory_ready['codigo'].nunique():,}")

                    if len(valid_dates):
                        st.info(
                            f"Período: {valid_dates.min().strftime('%d/%m/%Y')} al "
                            f"{valid_dates.max().strftime('%d/%m/%Y')} · "
                            f"Tiendas detectadas: {', '.join(stores) if stores else 'No detectadas'}"
                        )

                    with st.expander("Comprobación de importes"):
                        checks = pd.DataFrame(
                            {
                                "Concepto": [
                                    "Venta bruta (base %)",
                                    "Devoluciones",
                                    "Anulaciones",
                                    "Venta neta informativa",
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

                    sales_code_set = set(sales_ready["codigo"].dropna().astype(str))
                    inv_code_set = set(inventory_ready["codigo"].dropna().astype(str))
                    common_codes = len(sales_code_set & inv_code_set)

                    st.caption(
                        f"Cruce de códigos: {common_codes:,} códigos de ventas "
                        f"también aparecen en existencias."
                    )

                    if st.button("✅ Publicar datos", type="primary"):
                        if sales_ready.empty:
                            st.error("El archivo de ventas no contiene registros válidos.")
                        elif inventory_ready.empty:
                            st.error("El archivo de existencias no contiene registros válidos.")
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
                st.info("Selecciona ambos archivos para validar la información.")
