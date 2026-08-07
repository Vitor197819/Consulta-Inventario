
# Consulta de Inventario — PostgreSQL persistente

Esta versión conserva ventas, existencias y metadatos en PostgreSQL.

## Qué cambia

- Los datos ya no dependen del disco temporal del contenedor de Render.
- Un redeploy o reinicio de la aplicación no obliga a volver a cargar los archivos.
- Solo se reemplazan los datos cuando un administrador publica una nueva carga.
- Si `DATABASE_URL` no existe, la aplicación usa SQLite local como respaldo para pruebas.

## Configuración en Render

### 1. Crear PostgreSQL

En Render:

1. Dashboard → **New +**
2. **Postgres**
3. Crear la base de datos.
4. Cuando esté lista, abrirla y copiar su **Internal Database URL**.

### 2. Conectar la aplicación

En el Web Service `Consulta-Inventario`:

1. **Environment**
2. Agregar:

   - Key: `DATABASE_URL`
   - Value: pegar la **Internal Database URL** de PostgreSQL

3. Mantener también:

   - Key: `ADMIN_PASSWORD`
   - Value: la contraseña administrativa

4. Guardar y desplegar.

### 3. Actualizar el código

Subir/reemplazar en GitHub:

- `app.py`
- `requirements.txt`
- `Dockerfile`
- `render.yaml`
- `README.md`

Hacer commit y en Render usar **Deploy latest commit** si el despliegue no inicia automáticamente.

### 4. Primera carga

Después de que la nueva versión esté Live:

1. Ir a **Administración**
2. Cargar ventas y existencias
3. Revisar la validación
4. Pulsar **Publicar datos**

Esa primera publicación se guarda en PostgreSQL. A partir de ahí los redeploys conservan la información.

## Importante

La base de porcentaje sigue siendo la **venta bruta total (`MONTO_VENTA`) del archivo cargado**.

Los importes con coma decimal y 3–4 decimales, por ejemplo `5804,9448`, se interpretan correctamente como `5804.9448`.


## Versión móvil

La interfaz está optimizada para celular:

- búsqueda por código con Enter;
- existencia y participación de venta como indicadores principales;
- existencia por tienda en lista vertical;
- resultados múltiples en tarjetas;
- administración compacta;
- última actualización visible.

### Agregar a pantalla de inicio

**iPhone / iPad**
1. Abrir la app en Safari.
2. Compartir.
3. `Agregar a pantalla de inicio`.

**Android**
1. Abrir en Chrome.
2. Menú `⋮`.
3. `Agregar a pantalla de inicio` o `Instalar app`.

No requiere una aplicación nativa.
