---
id: pos-sales
section: Ventas y dinero
title: Importar ventas del POS
summary: Trae las ventas de anoche de Square, Toast, Clover o cualquier CSV.
view: sales
---
## Exporta desde tu POS {#export-from-your-pos}
Exporta las ventas por artículo como CSV desde tu punto de venta:
- **Square**: Item Sales o Item Details.
- **Toast**: Item Selection Details o Product Mix. Las anulaciones se saltan.
- **Clover**: reporte Item Sales. Los archivos de Clover no traen fechas, así que elige la fecha de ventas al importar.
- **Cualquier otro POS**: cualquier CSV con una columna de artículo y una de cantidad funciona con el mapeo de columnas.

## Impórtalo {#import-it}
Entradas › Ventas POS. Elige el archivo, deja **Formato de POS** en Detectar automáticamente (o elige uno), presiona **Vista previa**, revisa las líneas y luego **Importar**. Si las columnas salen mal, pon a mano las columnas de fecha, platillo, cantidad, precio unitario o total de línea.

Los nombres de columnas de Square, Toast y Clover salen de su documentación pública y todavía no se han revisado contra cada exportación real, así que siempre mira la vista previa.

## Liga las ventas a tu menú {#link-sales-to-your-menu}
Las líneas de venta se emparejan con los platillos por su nombre en el POS. Las líneas marcadas "Sin vincular a un platillo" necesitan ese nombre en un platillo de Menú (Nombre(s) en el POS).

## Cuentas de POS {#pos-accounts}
Ajustes › Cuentas › Cuentas POS marca qué cajas meten ventas. Son solo etiquetas.

## Borrar una importación {#deleting-an-import}
Cada importación sale en la lista con su fecha y número de líneas. Bórrala si importaste el archivo equivocado.
