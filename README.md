
# Consulta Inventario móvil — conexión Supabase robusta

Esta versión evita construir manualmente `DATABASE_URL`.

En Render configura estas variables por separado:

- `ADMIN_PASSWORD`: contraseña del administrador de la app
- `DB_HOST`: host del Session Pooler de Supabase
- `DB_PORT`: `5432`
- `DB_NAME`: `postgres`
- `DB_USER`: usuario completo del pooler, por ejemplo `postgres.<PROJECT_REF>`
- `DB_PASSWORD`: contraseña real de la base de datos de Supabase

Para el proyecto mostrado durante la configuración:

- DB_HOST: `aws-0-ca-central-1.pooler.supabase.com`
- DB_PORT: `5432`
- DB_NAME: `postgres`
- DB_USER: copiar exactamente el valor de `user` mostrado por Supabase

La contraseña se introduce separadamente, por lo que caracteres especiales como `@`, `#`, `%`, `/` o `:` ya no rompen la conexión.

Después de guardar las variables en Render, hacer un redeploy.

`DATABASE_URL` puede eliminarse para evitar que una configuración antigua cause confusión.
