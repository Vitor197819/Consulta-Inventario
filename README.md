
# Consulta de Existencias y Ventas

Aplicación web compartida para cargar diariamente un archivo de ventas y un archivo de existencias, y consultar por código:

- existencia total;
- existencia por tienda;
- venta neta;
- unidades netas;
- porcentaje sobre la venta total;
- tiendas con existencia 0 o 1.

## Formato de archivos

### Ventas
CSV con las columnas principales:

- `CODIGO`
- `TIENDA`
- `MONTO_VENTA`

Opcionales:

- `MONTO_DEVOLUCION`
- `MONTO_ANULACION`
- `CANTIDAD_VENTA_UNIDADES`
- `CANTIDAD_DEVOLUCION_UNIDADES`
- `CANTIDAD_ANULACION_UNIDADES`
- `NOMBRE`
- `CATEGORIA`
- `LINEA`

### Existencias
Debe exportarse como `.xlsx`.

Columnas reconocidas:

- código: `CODAMA` o `CODIGO`
- tienda: `TIENAT` o `TIENDA`
- existencia: `EXIST` o `EXISTENCIA`

El formato `.xls` antiguo se rechaza deliberadamente porque suele fallar en servidores modernos.

## Ejecución local

```bash
pip install -r requirements.txt
set ADMIN_PASSWORD=una-clave-segura
streamlit run app.py
```

En macOS/Linux:

```bash
export ADMIN_PASSWORD="una-clave-segura"
streamlit run app.py
```

Abrir: `http://localhost:8501`

## Publicación con Docker

```bash
docker build -t consulta-inventario .
docker run -p 8501:8501 \
  -e ADMIN_PASSWORD="una-clave-segura" \
  -v consulta_datos:/app/data \
  consulta-inventario
```

La aplicación quedará disponible en el puerto 8501. Para acceso externo se debe publicar detrás de HTTPS o usar un proveedor como Render, Railway, Azure, AWS o un servidor interno.

## Persistencia

Los datos se almacenan en SQLite dentro de la carpeta indicada por `DATA_DIR`.

En un servicio de alojamiento, se debe conectar un disco persistente a `/app/data`. Sin disco persistente, los datos pueden perderse al reiniciar el servicio.

## Seguridad mínima

- Cambiar siempre `ADMIN_PASSWORD`.
- Usar HTTPS.
- No publicar el puerto directamente a internet sin autenticación de red.
- Para usuarios individualizados y permisos por tienda se requiere una segunda fase con autenticación completa.
