---
id: troubleshooting
section: Ayuda
title: Algo se ve mal
summary: Arreglos rápidos para el micrófono, la IA, archivos del POS, variaciones raras, teléfonos e idioma.
view: home
---
## El micrófono no escucha {#the-mic-doesn-t-listen}
Usa Chrome, Edge o Safari y permite el micrófono cuando el navegador pregunte. Firefox no puede escuchar. Siempre puedes escribir en la misma caja.

## Falla la prueba de IA {#ai-test-fails}
Revisa que la clave se pegó completa, que el servicio de IA corresponde a la clave y que el nombre del modelo está bien. Ollama local tiene que estar corriendo. Algunas cuentas necesitan tener el cobro activado con la compañía de IA primero.

## Un archivo del POS se importa mal {#a-pos-file-imports-wrong}
Abre la vista previa y pon las columnas a mano. Los archivos de Clover necesitan que elijas la fecha de ventas. Asegúrate de que los platillos en Menú tengan los nombres del POS que usa tu archivo.

## La variación sale enorme {#variance-looks-huge}
Casi siempre son unidades. Las cantidades de receta tienen que estar en la unidad del producto (0.25 lb, no 4 oz). También revisa que no falte registrar una entrega y que los dos conteos cubrieran los mismos productos.

## Un producto sale en cero después de un conteo diario {#a-product-shows-zero-after-a-daily-count}
Los conteos diarios nunca ponen en cero lo que se saltan. Si un producto sale en 0, estaba en la lista de vigilancia y se contó en 0, o se puso en 0 en la lista No dicho del Conteo por voz.

## El teléfono no conecta {#a-phone-can-t-connect}
Arranca el programa con `python server.py --lan`, usa la dirección que imprime, deja el teléfono en el mismo Wi-Fi y permite Python en el firewall de la computadora.

## La página se regresa a inglés {#the-page-switches-back-to-english}
Usa los botones EN/ES de arriba. Si tu navegador ofrece traducir la página, di que no: el programa se traduce solo.

## Olvidé un PIN {#forgot-a-pin}
Un administrador lo puede cambiar en Ajustes › Personas.
