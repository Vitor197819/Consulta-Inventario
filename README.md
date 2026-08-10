# Inventario Tienda 6

Nueva versión construida para:

- `Vta2026(1).xlsx`
- `fallaApp(4).xlsx`

## Columnas reales detectadas

### Ventas
- CODIGO
- DESCRIPCION
- EXISTENCIA
- PZAS
- MONTO
- PRECIO

### Existencias
- CODIGO
- DESCRIPCION
- EXIST

## Reglas

- No se agregan ceros.
- No se eliminan ceros iniciales.
- El código se cruza tal como viene.
- Solo se limpia un posible `.0` de Excel.

## Cálculos

- Venta = MONTO
- Piezas vendidas = PZAS
- Existencia actual = EXIST
- % sobre venta total = venta de códigos consultados / venta total Vta2026

## Validación realizada con los archivos entregados

- Venta total: Q 5,298,950.79
- Códigos únicos en ventas: 11,216
- Códigos únicos en existencias: 51,364
- Códigos que cruzan directamente: 11,003
