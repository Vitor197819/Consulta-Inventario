# Inventario Tienda 6 — nueva base

Reconstruida para los archivos:

- `Vta2026.xlsx`
- `fallaApp.xlsx`

## Estructura utilizada

### Vta2026
- CODIGO
- DESCRIPCION
- PZAS
- MONTO
- PRECIO

### fallaApp
- CODIGO
- DEPTO
- DESCRIPCION
- TIPAMA
- EXIST
- PRECIO

## Regla de códigos

No se agregan ni eliminan ceros iniciales.  
Solo se eliminan espacios y un posible `.0` agregado por Excel.

## Cálculos

- Venta del código = `MONTO`
- Piezas vendidas = `PZAS`
- Existencia = `EXIST`
- % combinado = suma de `MONTO` de los códigos consultados / venta total del archivo `Vta2026`

Venta total observada en el archivo de prueba: Q 5,298,950.79.

La app consolida los archivos al publicar y guarda una sola tabla `products` en Supabase para acelerar las consultas.
