
import io
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, inspect, text as sql_text
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

APP_TITLE = "Inventario Tienda 6"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Cambiar123")

DB_HOST = os.getenv("DB_HOST", "").strip()
DB_PORT = os.getenv("DB_PORT", "5432").strip()
DB_NAME = os.getenv("DB_NAME", "postgres").strip()
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --blue:#175cd3;
        --blue-dark:#0b2f5b;
        --green:#079455;
        --red:#d92d20;
        --text:#101828;
        --muted:#667085;
        --border:#e4e7ec;
        --bg:#f8fafc;
    }

    .stApp { background: var(--bg); }

    .block-container {
        max-width: 720px;
        padding-top: .65rem;
        padding-bottom: 4rem;
    }

    h1 {
        font-size: 1.4rem !important;
        color: var(--blue-dark);
    }

    .updated-box {
        background:#eaf4ff;
        border:1px solid #cfe5ff;
        color:#175cd3;
        padding:.75rem .9rem;
        border-radius:14px;
        margin:.5rem 0 1rem;
        font-size:.9rem;
        font-weight:650;
    }

    .metric-grid {
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:.65rem;
        margin:.75rem 0;
    }

    .metric-card {
        background:#fff;
        border:1px solid var(--border);
        border-radius:16px;
        padding:.85rem;
        min-height:88px;
    }

    .metric-card.green {
        background:linear-gradient(180deg,#f0fdf4,#fff);
        border-color:#bbf7d0;
    }

    .metric-card.blue {
        background:linear-gradient(180deg,#eff8ff,#fff);
        border-color:#b2ddff;
    }

    .metric-value {
        font-size:1.35rem;
        font-weight:800;
        line-height:1.1;
        color:var(--text);
        word-break:break-word;
    }

    .green .metric-value { color:var(--green); }
    .blue .metric-value { color:var(--blue); }

    .metric-label {
        margin-top:.35rem;
        color:var(--muted);
        font-size:.8rem;
        font-weight:650;
    }

    .product-card {
        background:#fff;
        border:1px solid var(--border);
        border-radius:16px;
        padding:.9rem;
        margin:.55rem 0;
    }

    .product-code {
        font-size:1.05rem;
        font-weight:800;
        color:var(--text);
    }

    .product-name {
        color:#475467;
        font-size:.9rem;
        margin:.2rem 0 .55rem;
    }

    .product-row {
        display:flex;
        justify-content:space-between;
        gap:.7rem;
        padding:.26rem 0;
        color:#475467;
        font-size:.88rem;
    }

    .product-row b { color:var(--text); }

    div.stButton > button,
    div.stDownloadButton > button,
    div[data-testid="stFormSubmitButton"] > button {
        width:100%;
        min-height:46px;
        border-radius:12px;
        font-weight:700;
    }

    [data-testid="stTextArea"] textarea,
    [data-testid="stTextInput"] input {
        background:#fff !important;
        color:#101828 !important;
        border:1px solid #d0d5dd !important;
        border-radius:12px !important;
    }

    [data-testid="stTextArea"] label,
    [data-testid="stTextInput"] label,
    [data-testid="stFileUploader"] label {
        color:#101828 !important;
        font-weight:700 !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        background:#fff !important;
        border:1.5px dashed #98a2b3 !important;
        border-radius:14px !important;
        min-height:105px !important;
    }

    [data-testid="stFileUploaderDropzone"] * {
        color:#344054 !important;
    }

    [data-testid="stTabs"] button[role="tab"] {
        flex:1;
        min-height:44px;
        font-weight:700;
    }

    @media(max-width:600px){
        .block-container{
            padding-left:.8rem;
            padding-right:.8rem;
        }
        h1{font-size:1.22rem !important;}
        .metric-value{font-size:1.2rem;}
    }
    
    .location-box {
        margin-top:.55rem;
        padding:.65rem .7rem;
        background:#f9fafb;
        border:1px solid #eaecf0;
        border-radius:12px;
    }
    .location-title {
        color:#344054;
        font-size:.8rem;
        font-weight:800;
        margin-bottom:.35rem;
    }
    .location-line {
        color:#475467;
        font-size:.82rem;
        padding:.28rem 0;
        border-bottom:1px solid #f0f1f3;
    }
    .location-line:last-child { border-bottom:0; }
    .no-location {
        color:#98a2b3;
        font-size:.82rem;
        font-style:italic;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_engine():
    if not all([DB_HOST, DB_USER, DB_PASSWORD]):
        st.error("Falta configurar la conexión a Supabase en Render.")
        st.stop()

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
    )
    return create_engine(url, pool_pre_ping=True, poolclass=NullPool)


def init_db():
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


def normalize_code(value):
    """
    Mantiene el código tal como viene en ambos archivos.
    Solo limpia espacios y un posible .0 agregado por Excel.
    """
    value = str(value).strip()
    return re.sub(r"\.0+$", "", value)


def first_nonempty(series):
    for value in series:
        value = str(value).strip()
        if value and value.lower() not in {"nan", "none"}:
            return value
    return ""


def to_number(series):
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def read_sales(uploaded):
    df = pd.read_excel(
        io.BytesIO(uploaded.getvalue()),
        sheet_name=0,
        dtype=str,
        engine="openpyxl",
    )

    required = {"CODIGO", "DESCRIPCION", "PZAS", "MONTO"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            "Archivo de ventas: faltan columnas "
            + ", ".join(sorted(missing))
        )

    out = pd.DataFrame()
    out["codigo"] = df["CODIGO"].map(normalize_code)
    out["descripcion_venta"] = df["DESCRIPCION"].astype(str).str.strip()
    out["pzas"] = to_number(df["PZAS"])
    out["monto"] = to_number(df["MONTO"])
    out["existencia_venta"] = (
        to_number(df["EXISTENCIA"]) if "EXISTENCIA" in df.columns else 0.0
    )
    out["precio"] = (
        to_number(df["PRECIO"]) if "PRECIO" in df.columns else 0.0
    )

    return out[out["codigo"].ne("")]


def read_inventory(uploaded):
    df = pd.read_excel(
        io.BytesIO(uploaded.getvalue()),
        sheet_name=0,
        dtype=str,
        engine="openpyxl",
    )

    required = {"CODIGO", "DESCRIPCION", "EXIST"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            "Archivo de existencias: faltan columnas "
            + ", ".join(sorted(missing))
        )

    out = pd.DataFrame()
    out["codigo"] = df["CODIGO"].map(normalize_code)
    out["descripcion_inv"] = df["DESCRIPCION"].astype(str).str.strip()
    out["existencia"] = to_number(df["EXIST"])

    return out[out["codigo"].ne("")]



def read_locations(uploaded):
    raw = uploaded.getvalue()
    df = None
    last_error = None

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            candidate = pd.read_csv(
                io.BytesIO(raw),
                dtype=str,
                keep_default_na=False,
                encoding=encoding,
            )
            if "ARTICULO" in candidate.columns:
                df = candidate
                break
        except Exception as exc:
            last_error = exc

    if df is None:
        raise ValueError(
            f"Archivo de ubicaciones: no se pudo leer el CSV. {last_error or ''}"
        )

    required = {
        "ARTICULO", "ZONA", "SUBZONA", "ELEMENTO",
        "VIGA", "POSICION", "TIPO_UBICACION", "CANTIDAD"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            "Archivo de ubicaciones: faltan columnas "
            + ", ".join(sorted(missing))
        )

    out = pd.DataFrame()
    out["codigo"] = df["ARTICULO"].map(normalize_code)
    out["zona"] = df["ZONA"].astype(str).str.strip()
    out["subzona"] = df["SUBZONA"].astype(str).str.strip()
    out["elemento"] = df["ELEMENTO"].astype(str).str.strip()
    out["viga"] = df["VIGA"].astype(str).str.strip()
    out["posicion"] = df["POSICION"].astype(str).str.strip()
    out["tipo_ubicacion"] = df["TIPO_UBICACION"].astype(str).str.strip()
    out["cantidad"] = pd.to_numeric(
        df["CANTIDAD"].astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    ).fillna(0.0)

    out = out[out["codigo"].ne("")]

    # Si el mismo artículo aparece repetido exactamente en la misma ubicación,
    # consolidamos esas filas sumando la cantidad.
    group_cols = [
        "codigo", "zona", "subzona", "elemento",
        "viga", "posicion", "tipo_ubicacion"
    ]
    out = (
        out.groupby(group_cols, as_index=False, dropna=False)
        .agg(cantidad=("cantidad", "sum"))
    )

    return out


def location_line(row):
    parts = []
    tipo = str(row.get("tipo_ubicacion", "")).strip()
    zona = str(row.get("zona", "")).strip()
    subzona = str(row.get("subzona", "")).strip()
    elemento = str(row.get("elemento", "")).strip()
    viga = str(row.get("viga", "")).strip()
    posicion = str(row.get("posicion", "")).strip()
    cantidad = float(row.get("cantidad", 0) or 0)

    if tipo:
        parts.append(tipo)
    if zona:
        parts.append(zona)
    if subzona:
        parts.append(f"Subzona {subzona}")
    if elemento:
        parts.append(f"Elemento {elemento}")
    if viga:
        parts.append(f"Viga {viga}")
    if posicion:
        parts.append(f"Posición {posicion}")

    if cantidad.is_integer():
        cantidad_texto = f"{int(cantidad):,}"
    else:
        cantidad_texto = f"{cantidad:,.2f}"

    parts.append(f"Cantidad {cantidad_texto}")

    return " · ".join(parts)


def aggregate_locations(locations):
    if locations.empty:
        return pd.DataFrame(
            columns=["codigo", "ubicaciones", "cantidad_ubicaciones"]
        )

    locations = locations.copy()
    locations["ubicacion_linea"] = locations.apply(location_line, axis=1)

    return (
        locations.groupby("codigo", as_index=False)
        .agg(
            ubicaciones=(
                "ubicacion_linea",
                lambda x: " || ".join(
                    dict.fromkeys(v for v in x if str(v).strip())
                ),
            ),
            cantidad_ubicaciones=(
                "ubicacion_linea",
                lambda x: len(set(v for v in x if str(v).strip())),
            ),
        )
    )


def build_products(sales, inventory, locations):
    sales_agg = (
        sales.groupby("codigo", as_index=False)
        .agg(
            descripcion_venta=("descripcion_venta", first_nonempty),
            pzas=("pzas", "sum"),
            monto=("monto", "sum"),
            precio=("precio", "max"),
        )
    )

    inv_agg = (
        inventory.groupby("codigo", as_index=False)
        .agg(
            descripcion_inv=("descripcion_inv", first_nonempty),
            existencia=("existencia", "sum"),
        )
    )

    products = inv_agg.merge(sales_agg, on="codigo", how="outer")

    products["descripcion"] = products["descripcion_venta"].fillna("")
    mask = products["descripcion"].astype(str).str.strip().eq("")
    products.loc[mask, "descripcion"] = (
        products.loc[mask, "descripcion_inv"].fillna("")
    )

    for col in ["existencia", "pzas", "monto", "precio"]:
        products[col] = products[col].fillna(0.0)

    loc_agg = aggregate_locations(locations)
    products = products.merge(loc_agg, on="codigo", how="left")
    products["ubicaciones"] = products["ubicaciones"].fillna("")
    products["cantidad_ubicaciones"] = (
        products["cantidad_ubicaciones"].fillna(0).astype(int)
    )

    return products[
        [
            "codigo", "descripcion", "existencia", "pzas", "monto",
            "precio", "ubicaciones", "cantidad_ubicaciones"
        ]
    ].copy()


def publish_data(products, total_sales, sales_name, inventory_name):
    engine = get_engine()

    products.to_sql(
        "products_upload_tmp",
        engine,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=1000,
    )

    metadata = {
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "sales_file": sales_name,
        "inventory_file": inventory_name,
        "total_sales": f"{float(total_sales):.10f}",
        "product_count": str(len(products)),
    }

    with engine.begin() as conn:
        conn.execute(sql_text("DROP TABLE IF EXISTS products"))
        conn.execute(
            sql_text(
                "ALTER TABLE products_upload_tmp RENAME TO products"
            )
        )

        for key, value in metadata.items():
            conn.execute(
                sql_text(
                    """
                    INSERT INTO metadata(key, value)
                    VALUES (:key, :value)
                    ON CONFLICT (key)
                    DO UPDATE SET value = EXCLUDED.value
                    """
                ),
                {"key": key, "value": value},
            )


def get_metadata():
    init_db()
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sql_text("SELECT key, value FROM metadata")
        ).fetchall()
    return dict(rows)


def products_table_exists():
    return inspect(get_engine()).has_table("products")


def query_products(codes):
    if not codes:
        return pd.DataFrame()

    engine = get_engine()

    bind_names = [f"c{i}" for i in range(len(codes))]
    placeholders = ",".join(f":{name}" for name in bind_names)
    params = {bind_names[i]: codes[i] for i in range(len(codes))}

    sql = sql_text(
        f"""
        SELECT codigo, descripcion, existencia, pzas, monto, precio, ubicaciones, cantidad_ubicaciones
        FROM products
        WHERE codigo IN ({placeholders})
        """
    )

    with engine.connect() as conn:
        df = pd.read_sql_query(sql, conn, params=params)

    order = {code: i for i, code in enumerate(codes)}
    df["_order"] = df["codigo"].map(order)
    return df.sort_values("_order").drop(columns="_order")


def clear_codes():
    st.session_state["query_codes"] = ""
    st.session_state.pop("query_results", None)


metadata = get_metadata()

st.title("📦 Inventario Tienda 6")

if metadata:
    st.markdown(
        f"""
        <div class="updated-box">
            Datos actualizados: {metadata.get('updated_at', '—')}<br>
            Productos cargados: {int(metadata.get('product_count', '0')):,}
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.warning("Aún no se han publicado datos.")

tab_query, tab_admin = st.tabs(["🔎 Consulta", "⚙️ Administración"])

with tab_query:
    if not products_table_exists():
        st.info("Primero publica los archivos desde Administración.")
    else:
        with st.form("query_form"):
            query_text = st.text_area(
                "Códigos a consultar",
                placeholder="Un código por línea",
                height=145,
                key="query_codes",
            )
            submitted = st.form_submit_button(
                "🔎 Consultar",
                type="primary",
            )

        st.button(
            "🧹 Borrar códigos",
            on_click=clear_codes,
            use_container_width=True,
        )

        if submitted:
            codes = []
            for token in re.split(r"[\n,;\s]+", query_text.strip()):
                code = normalize_code(token)
                if code and code not in codes:
                    codes.append(code)

            if not codes:
                st.warning("Ingresa al menos un código.")
            else:
                result = query_products(codes)

                found = (
                    set(result["codigo"].astype(str))
                    if not result.empty
                    else set()
                )
                missing = [code for code in codes if code not in found]

                if missing:
                    missing_df = pd.DataFrame(
                        {
                            "codigo": missing,
                            "descripcion": ["No encontrado"] * len(missing),
                            "existencia": [0.0] * len(missing),
                            "pzas": [0.0] * len(missing),
                            "monto": [0.0] * len(missing),
                            "precio": [0.0] * len(missing),
                            "ubicaciones": [""] * len(missing),
                            "cantidad_ubicaciones": [0] * len(missing),
                        }
                    )
                    result = pd.concat(
                        [result, missing_df],
                        ignore_index=True,
                    )
                    order = {
                        code: i for i, code in enumerate(codes)
                    }
                    result["_order"] = result["codigo"].map(order)
                    result = result.sort_values("_order").drop(
                        columns="_order"
                    )

                st.session_state["query_results"] = result

        if "query_results" in st.session_state:
            result = st.session_state["query_results"].copy()

            total_sales = float(
                metadata.get("total_sales", 0) or 0
            )

            selected_sales = float(result["monto"].sum())
            selected_stock = float(result["existencia"].sum())
            selected_units = float(result["pzas"].sum())

            selected_share = (
                selected_sales / total_sales * 100
                if total_sales
                else 0.0
            )

            st.markdown("### Resumen")

            summary_html = (
                f'<div class="metric-grid">'
                f'<div class="metric-card green">'
                f'<div class="metric-value">Q {selected_sales:,.2f}</div>'
                f'<div class="metric-label">Venta total códigos</div>'
                f'</div>'
                f'<div class="metric-card blue">'
                f'<div class="metric-value">{selected_share:.4f}%</div>'
                f'<div class="metric-label">% sobre venta total</div>'
                f'</div>'
                f'<div class="metric-card">'
                f'<div class="metric-value">{selected_stock:,.0f}</div>'
                f'<div class="metric-label">Existencia combinada</div>'
                f'</div>'
                f'<div class="metric-card">'
                f'<div class="metric-value">{selected_units:,.0f}</div>'
                f'<div class="metric-label">Piezas vendidas</div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(summary_html, unsafe_allow_html=True)

            st.markdown(f"### Detalle de {len(result)} códigos")

            for _, row in result.iterrows():
                stock = float(row["existencia"])
                stock_color = (
                    "#d92d20" if stock <= 0 else "#079455"
                )

                card = (
                    f'<div class="product-card">'
                    f'<div class="product-code">{row["codigo"]}</div>'
                    f'<div class="product-name">{row["descripcion"]}</div>'
                    f'<div class="product-row">'
                    f'<span>Existencia</span>'
                    f'<b style="color:{stock_color}">{stock:,.0f}</b>'
                    f'</div>'
                    f'<div class="product-row">'
                    f'<span>Venta</span>'
                    f'<b>Q {float(row["monto"]):,.2f}</b>'
                    f'</div>'
                    f'<div class="product-row">'
                    f'<span>Piezas vendidas</span>'
                    f'<b>{float(row["pzas"]):,.0f}</b>'
                    f'</div>'
                )

                ubicaciones = str(row.get("ubicaciones", "") or "").strip()

                if ubicaciones:
                    location_rows = "".join(
                        f'<div class="location-line">{loc}</div>'
                        for loc in ubicaciones.split(" || ")
                        if loc.strip()
                    )
                    card += (
                        f'<div class="location-box">'
                        f'<div class="location-title">📍 Ubicaciones ({int(row.get("cantidad_ubicaciones", 0))})</div>'
                        f'{location_rows}'
                        f'</div>'
                    )
                else:
                    card += (
                        f'<div class="location-box">'
                        f'<div class="location-title">📍 Ubicación</div>'
                        f'<div class="no-location">Sin ubicación registrada</div>'
                        f'</div>'
                    )

                card += '</div>'
                st.markdown(card, unsafe_allow_html=True)

            export = result.rename(
                columns={
                    "codigo": "Código",
                    "descripcion": "Descripción",
                    "existencia": "Existencia",
                    "pzas": "Piezas vendidas",
                    "monto": "Venta",
                    "precio": "Precio",
                    "ubicaciones": "Ubicaciones",
                    "cantidad_ubicaciones": "Cantidad ubicaciones",
                }
            )

            st.download_button(
                "⬇️ Descargar resultados",
                data=export.to_csv(index=False).encode("utf-8-sig"),
                file_name="consulta_codigos.csv",
                mime="text/csv",
            )

with tab_admin:
    st.markdown("### Actualización de datos")
    st.caption(
        "Carga ventas, existencias y ubicaciones. "
        "No se modifica el formato de los códigos."
    )

    password = st.text_input(
        "Clave de administrador",
        type="password",
        placeholder="Ingresa la clave",
    )

    if password:
        if password != ADMIN_PASSWORD:
            st.error("Clave incorrecta.")
        else:
            st.success("Acceso autorizado.")

            sales_file = st.file_uploader(
                "1. Ventas — Vta2026.xlsx",
                type=["xlsx"],
            )

            inventory_file = st.file_uploader(
                "2. Existencias — fallaApp.xlsx",
                type=["xlsx"],
            )

            locations_file = st.file_uploader(
                "3. Ubicaciones — XXVEProductAisleRack.csv",
                type=["csv"],
            )

            if sales_file and inventory_file and locations_file:
                try:
                    sales = read_sales(sales_file)
                    inventory = read_inventory(inventory_file)
                    locations = read_locations(locations_file)
                    products = build_products(sales, inventory, locations)

                    total_sales = float(sales["monto"].sum())

                    sales_codes = set(sales["codigo"])
                    inv_codes = set(inventory["codigo"])
                    common = len(sales_codes & inv_codes)

                    st.markdown("### Validación")

                    c1, c2 = st.columns(2)
                    c1.metric(
                        "Venta total",
                        f"Q {total_sales:,.2f}",
                    )
                    c2.metric(
                        "Códigos cruzados",
                        f"{common:,}",
                    )

                    c3, c4 = st.columns(2)
                    c3.metric(
                        "Códigos ventas",
                        f"{len(sales_codes):,}",
                    )
                    c4.metric(
                        "Códigos existencias",
                        f"{len(inv_codes):,}",
                    )

                    location_codes = locations["codigo"].nunique()

                    st.info(
                        f"Se guardarán {len(products):,} productos consolidados. "
                        f"Ubicaciones: {location_codes:,} códigos y "
                        f"{len(locations):,} ubicaciones consolidadas, "
                        f"cada una con su cantidad."
                    )

                    if st.button(
                        "✅ Publicar datos",
                        type="primary",
                    ):
                        publish_data(
                            products,
                            total_sales,
                            sales_file.name,
                            inventory_file.name,
                        )

                        st.session_state.pop(
                            "query_results",
                            None,
                        )

                        st.success(
                            "Datos publicados correctamente."
                        )
                        st.rerun()

                except Exception as exc:
                    st.error(
                        f"No se pudo validar la carga: {exc}"
                    )
            else:
                st.info(
                    "Selecciona los tres archivos para validar."
                )
