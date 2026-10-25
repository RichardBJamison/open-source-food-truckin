---
id: counting
section: Contar
title: Contar el camión
summary: Inicia un conteo, recorre el camión sección por sección, guarda sobre la marcha y complétalo.
view: count
---
## Iniciar un conteo {#start-a-count}
Hojas de inventario › Hoja de conteo. Elige el **Tipo de conteo** (Diario al cierre, Semanal o Mensual) y la **Fecha del negocio**, y presiona **Iniciar conteo**. La pantalla te dice qué cubre el conteo antes de empezar.

## Recorre el camión {#walk-the-truck}
Los productos salen sección por sección en tu orden de recorrido. Escribe la cantidad o usa los botones grandes **−** y **+** (hechos para una mano en el teléfono). El avance se guarda sobre la marcha, así que puedes parar y volver; solo puede haber un conteo en curso a la vez.

## Completa el conteo {#complete-the-count}
Presiona **Guardar y completar conteo**. El programa actualiza lo que hay a la mano, la Variación, la Lista de pedido, Inicio y los reportes.

## Conteos completos y parciales {#full-counts-and-partial-counts}
- Un **conteo completo** (Semanal, Mensual) cubre todo el camión. Lo que quede en blanco dentro de él se marca como faltante.
- Un **conteo parcial** (Diario al cierre) cubre solo su lista de vigilancia. Todo lo que no está en la lista se queda con su último conteo: nunca se pone en cero ni se marca faltante.

## Antes del servicio o al cierre {#before-service-or-end-of-shift}
Cada tipo de conteo tiene un momento. "Antes del servicio" quiere decir que el conteo fue antes de las ventas de ese día; "Al cierre" quiere decir después. Los archivos del POS traen fechas, no horas, así que este ajuste mantiene honestas las cuentas de uso.

## Historial de conteos {#count-history}
Reportes › Dinero muestra cada conteo completado con su tipo, alcance y quién contó.

## Contar desde el teléfono {#counting-from-a-phone}
Corre el programa con `python server.py --lan` en la computadora y abre la dirección que imprime en un teléfono conectado al mismo Wi-Fi. Hazlo solo en una red de confianza.
