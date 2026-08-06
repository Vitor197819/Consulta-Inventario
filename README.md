# Consulta de Inventario y Participación de Venta

Versión reconstruida desde cero.

## Funciones

- Carga diaria de ventas en CSV.
- Carga directa de existencias en `.xls` o `.xlsx`.
- Validación previa antes de publicar.
- Vista del período y cantidad de días.
- Cálculo correcto de venta neta:
  `venta + devolución + anulación`.
- Consulta con Enter.
- Existencia total y por tienda.
- Participación porcentual sobre la venta bruta total.
- Descarga de resultados.
- Acceso administrativo mediante contraseña.

## Archivos del proyecto

- `app.py`
- `requirements.txt`
- `Dockerfile`
- `render.yaml`

## Actualizar en GitHub

Lo más seguro es reemplazar todos los archivos anteriores por los incluidos en este paquete.

## Render

1. Render debe usar `Runtime: Docker`.
2. Crear la variable:
   - `ADMIN_PASSWORD`: contraseña elegida.
3. Desplegar el último commit.
4. Entrar a Administración, validar los archivos y pulsar `Publicar datos`.

## Persistencia

En el plan gratuito, Render puede reiniciar el contenedor y perder la base local.
Para uso permanente se recomienda un disco persistente o una base externa.


## Base del porcentaje

El porcentaje de cada código se calcula así:

`venta neta del código / venta bruta total del archivo × 100`

Para el archivo revisado, la base es `Q3,594,777.20`.
