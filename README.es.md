<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Carga Barata para Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · 🇪🇸 Español · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Recarga una batería doméstica Marstek Venus desde la red en las horas más baratas de un
contrato de electricidad dinámico, para que esté llena antes de que suba el precio.

El punto de partida es el **autoconsumo**. La batería sigue regulándose sola (anti-feed,
cero en el contador). Esta integración añade una sola cosa: cargar desde la red en las horas
más baratas. Además hay una opción aparte, desactivada por defecto, para **vender el excedente**
en las horas más caras.

> **Hardware y compatibilidad.** La integración controla una Marstek Venus a través de sus
> registros de control RS485. Solo la primera fila se ha probado en una batería real:
>
> | Conexión | Modelo | Estado |
> |---|---|---|
> | LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Probado** en hardware real (la configuración sobre la que se construyó) |
> | Hub Modbus en Home Assistant, mediante conversor RS485 a TCP (Elfin EW11 y similares) | Venus E v1/v2 | Probado solo con llamadas simuladas |
> | Hub Modbus en Home Assistant, directamente por Ethernet | Venus E v3 | Probado solo con llamadas simuladas |
> | Integración *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Probado solo con llamadas simuladas |
> | Cualquiera de las anteriores | Venus A, Venus D, otros modelos | **Sin comprobar, sin probar.** Se dice que comparten los registros de control, pero no está verificado. Ajusta la capacidad de la batería en las opciones (por defecto 5,12 kWh). |
> | Nube, app u otras integraciones | cualquiera | No compatible |
>
> Las conexiones en detalle:
>
> - **LilyGO T-CAN485 con ESPHome** por RS485, con la configuración de
>   [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485). Es la
>   configuración sobre la que se construyó la integración y con la que se ha probado. Usa las
>   entidades que ofrece esa configuración: *RS485 Control Mode*, *Forcible Charge/Discharge*,
>   *Forcible Charge Power* (obligatorias) y, opcionalmente, *Max. Charge Power*, *Max. Discharge Power*,
>   *Forcible Discharge Power*, *Discharging Cutoff Capacity* y los contadores de energía total
>   cargada/descargada.
> - **Modbus en Home Assistant**, con un hub Modbus que defines tú mismo en `configuration.yaml`:
>   un Elfin EW11 u otro conversor RS485 a TCP
>   ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), o la
>   **Venus E v3 directamente por Ethernet** (Modbus TCP, puerto 502, unidad 1, EMS V144 o posterior;
>   [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)). La
>   integración lee los sensores de registros de esa configuración y escribe los registros 42000
>   (control RS485), 42010 (modo forzado), 42020/42021 (potencia de carga/descarga forzada) y, si
>   indicas los sensores, 44002/44003 (potencia máxima de carga/descarga) con
>   `modbus.write_register`. Con la potencia máxima de descarga también funcionan *Retener* y
>   *Sin pérdidas*; sin ella no están disponibles. La Venus E v3 guarda su nivel de carga en el
>   registro 34002 (escala 0,1), no en el 32104.
> - **La integración *Marstek Venus Modbus***
>   ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), que
>   también habla Modbus TCP (Ethernet en una Venus E v3, o una pasarela RS485). Elígela si ya usas
>   esa integración: aporta las entidades (`switch` modo de control RS485, `select` modo forzado,
>   `number` potencias). Activa antes allí el interruptor *RS485 control mode* y el selector
>   *Force mode*, que vienen desactivados por defecto.
>
> Las opciones Modbus y Marstek Venus Modbus son **nuevas y por ahora solo probadas con llamadas
> simuladas, no en hardware real**.
>
> Otras formas de conectar la batería (nube, otras integraciones) no están probadas y lo más
> probable es que no funcionen, porque no ofrecen estas entidades de control RS485.
>
> **Precios dinámicos de la energía:** esta integración solo tiene sentido con un **contrato de
> electricidad dinámico**, en el que el precio cambia cada hora. Carga en las horas más baratas y
> evita las caras, así que con una tarifa fija no hay nada que ganar. Se construyó pensando en el
> mercado neerlandés y los precios de Zonneplan (precios horarios, publicados para el día siguiente
> entre las 13:00 y las 15:00). Sirve cualquier sensor de precios con una lista de precios horarios
> como atributo, véase [Sensor de precios](#sensor-de-precios).
>
> **Idioma:** el texto del plan, el diagrama de flujo y las tarjetas siguen la opción *Idioma*
> (Automático, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska o Norsk;
> Automático sigue a Home Assistant cuando es uno de ellos, y si no usa inglés). Los nombres de las entidades siguen el idioma de
> Home Assistant. Los valores de estado y los nombres de atributos (`laden`, `tekst`, …) son fijos.

## Qué hace

1. **¿Merece la pena cargar?** Una hora es lo bastante barata si su precio es inferior a
   `rendimiento × (media de las 6 horas más caras de las próximas 18 horas) − margen`.
   El rendimiento (ida y vuelta de carga y descarga, alrededor del 77 % en mi unidad) se mide
   con los contadores de energía de la Marstek.
2. **Ventana.** El primer bloque de horas baratas es la ventana de carga. Una o dos horas que
   no llegan a ser lo bastante baratas no rompen el bloque; la carga solo ocurre en las propias
   horas baratas.
3. **Horas de carga.** Dentro de esa ventana elige las horas más baratas, exactamente las
   necesarias para pasar del SoC actual al 100 %. Si la ventana es demasiado corta para llenar
   la batería, planifica solo lo que cabe y lo indica en el texto del plan.
4. **Repartir la potencia.** La potencia de carga es la energía que falta por añadir dividida
   entre el tiempo que queda en las horas de carga. Así la carga sobre la conexión a la red y el
   circuito de la casa es la menor posible. La potencia se ajusta sobre la marcha.
5. **Lo hecho, hecho está.** Cuando terminan las horas de carga o la batería está llena, la Marstek
   vuelve a anti-feed. No arranca de nuevo en la misma ventana y no mantiene la carga.

Solo se usan precios **publicados**. Por eso el plan para la noche aparece en cuanto se conocen
los precios de mañana (con Zonneplan entre las 13:00 y las 15:00).

Ejemplo (10 de noviembre de 2026, batería al 12 %): ventana barata 23:00–07:00, carga a las 02:00,
03:00 y 04:00 a unos 1900 W por una media de € 0,37, frente a € 0,55–0,67 durante el día.

## Carga con precio negativo

Si el precio horario es negativo, la batería carga desde la red, sin importar el plan de carga
e incluso con el control por precio desactivado. Tiene su propio interruptor, **activado por defecto**.

Mira toda la **ventana** de horas negativas consecutivas, no solo la hora actual, y le saca el
máximo partido:

1. Calcula cuánto puede admitir aún la batería (del SoC al 100 %).
2. Reparte esa energía entre las horas **según su valor**: cuanto más negativo es el precio, más
   se carga en esa hora (hasta lo que admite una hora a la potencia máxima). Ejemplo: tres horas
   negativas de −€ 0,03, −€ 0,20 y −€ 0,12 y 3 kWh por cargar todavía. La hora de −€ 0,20 recibe
   unos 1,9 kWh y la de −€ 0,12 unos 1,2 kWh. La hora de −€ 0,03 quedaría por debajo de la
   potencia mínima de carga, así que queda fuera y su parte pasa a las otras dos.
3. Como la energía se reparte entre las horas, la potencia se mantiene más baja que cargando a
   plena potencia durante poco tiempo. Si la batería admite más de lo que ofrece la ventana, cada hora
   se llena al máximo. Una hora aislada que no puede llenar la batería se carga a plena potencia.
4. El texto del plan y el diagrama de flujo muestran la ventana, las horas elegidas, la potencia y
   el beneficio esperado (lo que te pagan por cargar).

La opción *Precio negativo: cómo repartir la energía* alterna entre dos formas:

- **Repartir por valor** (por defecto): como se ha descrito, menor potencia, algo menos de beneficio.
- **Beneficio máximo**: las horas se llenan una a una, la de mejor precio primero, cada una a
  plena potencia, y el resto pasa a la siguiente mejor hora. En el ejemplo, la hora de −€ 0,20 admite
  2,25 kWh a plena potencia y la de −€ 0,12 los 0,8 kWh restantes, lo que da unos € 0,55 en lugar
  de € 0,52. El precio a pagar son más ráfagas cortas a plena potencia.

En cuanto el precio vuelve a ser positivo o la batería está llena, la Marstek vuelve a anti-feed.
El plan se recalcula cada minuto; una hora que ya estaba en uso recibe un pequeño margen extra
antes de quedar fuera por estar por debajo de la potencia mínima.

El límite es ajustable (*Precio negativo: límite*, por defecto € 0,00). El precio se toma del
sensor de precios, así que con Zonneplan es el precio con impuestos incluidos.

## Previsión solar

Con paneles solares, la batería se llena gratis durante el día. Si la cargas del todo desde la
red por la noche, el excedente solar se queda sin sitio y va a la red por poco o nada, algo que
importa más ahora que termina el balance neto (*salderingsregeling*). Por eso la integración
tiene en cuenta el rendimiento solar esperado:

1. Lee la previsión del **panel de Energía** de Home Assistant (*Ajustes → Paneles →
   Energía → Paneles solares → Previsión de producción solar*). Funcionan Forecast.Solar,
   Solcast, Open-Meteo y otras integraciones de previsión, y no hay que configurar nada más. Sin
   previsión allí, no cambia nada.
2. Calcula el excedente esperado: por hora la previsión, multiplicada por el ajuste de
   fiabilidad (por defecto 70 %), menos tu consumo propio (el ajuste *Venta: consumo propio
   medio*).
3. Por la noche carga solo lo justo para que quede espacio para ese excedente cuando salga el
   sol: la energía que gasta tu consumo propio hasta entonces, más lo que aún hace falta. En un
   día soleado pueden ser unos pocos kWh en lugar de una batería llena, o nada en absoluto (el
   texto del plan dice entonces que el sol llenará la batería).
4. Un día nublado da un excedente pequeño o nulo, y entonces la batería se carga del todo como
   antes.

Se puede desactivar con *Usar la previsión solar*. La previsión se lee cada 30 minutos. Solo
reduce la cantidad a cargar; no mueve las horas de carga ni cambia la venta.

## Retener bajo el precio de coste

La energía cargada desde la red tiene un precio de coste: el precio de carga dividido por el
rendimiento. Si la batería devolviera esa energía justo después de cargarla, en horas más baratas
que ese precio de coste, cargar costaría dinero. Por eso se bloquea la descarga mientras:

- haya existencias cargadas en la batería (véase *Beneficio*), y
- el precio horario sea inferior al precio de coste de esas existencias.

La casa usa entonces electricidad de la red, que en ese momento es más barata que la de la
batería. En cuanto el precio alcanza el precio de coste, o se agotan las existencias, la Marstek
retoma el control. Tiene su propio interruptor, **activado por defecto**.

Técnicamente, la integración pone la potencia máxima de descarga (*Max. Discharge power*) a 0.
La Marstek se queda en anti-feed, así que la carga con excedente solar continúa. Si otra
automatización cambia esa potencia a otro valor durante la retención (por ejemplo un limitador
para un cargador de coche eléctrico), la integración recuerda ese valor, vuelve a ponerla a 0 y
restaura después el valor recordado.

Atención: la Marstek no distingue la energía cargada de la red de la energía solar. Durante una
retención, por tanto, no se descarga toda la batería.

## Sin pérdidas

Un interruptor aparte (desactivado por defecto) que hace estricta a la integración: la energía
cargada desde la red nunca se usa ni se vende por debajo de su precio de coste.

- **Se impone la retención**, aunque el interruptor *Retener* esté desactivado.
- **Se bloquea la venta por debajo del precio de coste.** Si hay existencias cargadas en la
  batería y el precio de venta es inferior a su precio de coste, no se vende nada.

Cada kWh contabilizado rinde entonces al menos su precio de coste, así que el beneficio de un día
no puede bajar de cero. Lo que no puede descartar:

- **Bloqueo.** Si el precio se mantiene por debajo del precio de coste durante mucho tiempo, la
  batería sigue bloqueada para descargar, incluida la energía solar almacenada.
- **Rendimiento diferente.** El precio de coste usa el rendimiento medio. Si la batería devuelve
  menos en un ciclo, se queda vacía antes de agotar las existencias contabilizadas; el resto
  caduca sin registrar pérdida.
- **El desgaste** de la batería no se cuenta; para eso usa el beneficio mínimo por kWh.

La integración recalcula de inmediato cuando empieza un nuevo periodo de precio, así que una
retención nunca arranca con hasta un minuto de retraso.

## Venta (opcional)

La venta tiene su propio interruptor y es independiente de la carga. Solo se vende lo que
realmente sobra. Una hora se usa para vender cuando se cumple todo lo siguiente:

1. **Se acerca una carga barata**: hay por delante una ventana de carga con precios publicados,
   así que se conoce el coste de volver a cargar.
2. **El ingreso es claramente superior a recargar**: precio de venta ≥ precio de carga dividido
   por el rendimiento, más el margen de venta (por defecto € 0,10 por kWh).
3. **Hay excedente por encima de la reserva.** La reserva es el límite de descarga de la Marstek
   más el consumo propio previsto hasta volver a cargar (potencia media de la casa × horas), con
   un mínimo ajustable (por defecto 20 %).
4. **Es una de las horas más caras** antes de la ventana de carga.

Igual que en la carga, la potencia de venta se reparte entre las horas elegidas. Al llegar a la
reserva, la venta se detiene y la Marstek vuelve a anti-feed.

En invierno rara vez hay excedente: con una batería de 5 kWh, el consumo propio hasta la
siguiente carga suele consumir toda la carga. La opción sirve sobre todo cuando el sol llena
la batería y hay un pico de precio por la tarde.

**Tras el fin del balance neto** (la *salderingsregeling* neerlandesa, 1 de enero de 2027) verter
a la red rinde menos que el precio horario. Entonces ajusta *Precio de venta: factor* y
*deducción*: precio de venta = precio horario × factor − deducción. Para el precio de mercado
puro en Zonneplan son aproximadamente 0,826 y € 0,108.

## Control de la Marstek

La integración controla la batería a través de la interfaz RS485 (LilyGO T-CAN485 con
ESPHome):

| Momento | Comandos |
|---|---|
| Empezar a cargar | fijar potencia de carga → *Forcible charge/discharge* a `charge` → *RS485 Control Mode* a `enable` |
| Durante la carga | ajustar la potencia de carga (pasos de 100 W) |
| Terminado, o control por precio desactivado | *RS485 Control Mode* a `disable`, forzado de vuelta a `charge`, potencia de carga de vuelta al máximo |
| Empezar a vender | fijar potencia de descarga → forzado a `discharge` → *RS485 Control Mode* a `enable` |
| Venta terminada, o venta desactivada | igual que terminado: de vuelta al estado de reposo |

La **des**carga forzada que inicies tú mismo se deja como está. La carga forzada que inicies tú
mismo se restablece mientras el control por precio esté activado; desactívalo antes si quieres eso.

## Entidades

| Entidad | Contenido |
|---|---|
| `switch.*_price_control` | Activado: se ejecuta el plan de carga. Desactivado: la Marstek lo regula todo sola. Al desactivarlo, la Marstek vuelve a anti-feed de inmediato. |
| `switch.*_charge_at_negative_price` | Activado (por defecto): carga siempre a plena potencia cuando el precio horario es negativo. Atributo `nu_actief`. |
| `switch.*_hold_below_cost_price` | Activado (por defecto): no descarga mientras el precio horario esté por debajo del precio de coste de las existencias cargadas. Atributos `nu_actief`, `tot`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_no_loss` | Activado: se impone la retención y nunca se vende por debajo del precio de coste. Atributos `vasthouden_actief`, `verkoop_tegengehouden`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_selling` | Activado: el excedente se vende en las horas más caras. Independiente del control por precio. |
| `sensor.*_sell_plan` | Estado: `verkopen`, `gepland`, `geen` o `onbekend`. Atributos: `verkoopuren`, `vermogen`, `overschot_kwh`, `reserve_soc`, `drempelprijs`, `terugkoopprijs` y `tekst`. |
| `sensor.*_charge_plan` | Estado: `laden`, `gepland`, `klaar`, `vol`, `geen` o `onbekend`. Atributos: `laaduren`, `venster`, `eind`, `uren_nodig`, `vermogen`, `klaar_tot`, `tekst` (resumen legible) y `stroomschema` (cronología y comprobaciones para la tarjeta). |
| `sensor.*_planned_charge_power` | La potencia de carga repartida en W. |
| `sensor.*_energy_to_charge` | Energía de la red necesaria para llenar la batería, en kWh. |
| `sensor.*_charge_start` / `*_charge_end` | Inicio y fin de la carga planificada. |
| `sensor.*_gain_today` / `*_gain_this_week` / `*_gain_this_month` | Beneficio realizado en euros desde las 00:00, desde el lunes a las 00:00 y desde el día uno del mes (véase *Beneficio*). Atributos: las existencias y, para hoy, lo cargado y lo usado. |
| `sensor.*_gain_this_year` | Beneficio realizado desde el 1 de enero. |
| `sensor.*_gain_last_week` | El beneficio final de la semana anterior. |
| `sensor.*_expected_gain` | Beneficio estimado de los planes actuales en euros (carga más venta); el atributo `regels` contiene el desglose. |
| `sensor.*_efficiency` | El rendimiento usado, en porcentaje. Atributo `bron`: medido con los contadores de energía o el valor fijo. |
| `sensor.*_average_charge_price` | Precio medio de las horas de carga en €/kWh. |

Los nombres de arriba corresponden a una instalación en inglés. Con Home Assistant en neerlandés
se llaman `*_laadplan`, `*_prijssturing` y así sucesivamente. Los valores de estado y los nombres
de atributos son los mismos en todos los idiomas.

## Instalación

1. Instala con HACS (botón de arriba, o añade este repositorio como repositorio personalizado,
   categoría *Integración*), o copia `custom_components/marstek_goedkoop_laden` a
   `/config/custom_components/`. Reinicia Home Assistant.
2. Ve a *Ajustes → Dispositivos y servicios → Añadir integración → Marstek Goedkoop Laden*.
3. Elige cómo está conectada tu Marstek (*LilyGO RS485 con ESPHome*, *Modbus en Home Assistant* o *Integración Marstek Venus Modbus*),
   luego el sensor de precios y las entidades de la Marstek. Lo que se detecta ya viene rellenado. Con Modbus
   indicas además el nombre de tu hub Modbus (por ejemplo `MarstekVenus`) y la dirección esclava.

Requiere Home Assistant 2026.3 o posterior.

### Sensor de precios

La integración lee los precios de un atributo de un sensor (por defecto `forecast`):

- Precios horarios de Zonneplan: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (antiguo): `datetime`, `electricity_price`
- Genérico: `start` (o `start_time`, `datetime`) y `price` (o `value`, `prijs`) en €/kWh

### Ajustes

En *Configurar* dentro de la integración:

| Ajuste | Por defecto | Significado |
|---|---|---|
| Idioma | Automático | Idioma del texto del plan, el diagrama de flujo y las tarjetas: Automático, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska o Norsk. |
| Precio de compra de la batería | € 0 | Se usa para la amortización. 0 desactiva la amortización. |
| Vida útil de la batería (ciclos) | 6000 | Número esperado de ciclos completos. Amortización por kWh = precio ÷ (ciclos × capacidad); por ejemplo € 1500 en 6000 ciclos de 5,12 kWh son unos € 0,049 por kWh. |
| Usar la previsión solar | Activado | Tener en cuenta el rendimiento solar esperado del panel de Energía al cargar por la noche. |
| Fiabilidad de la previsión solar | 70 % | La parte de la previsión con la que contar. Más baja es más prudente. |
| Beneficio mínimo por kWh | € 0,02 | Lo mínimo que debe rendir cargar, tras las pérdidas de carga. Las horas que están menos de medio céntimo por encima del límite también cuentan, para que una noche casi plana no se trocee por una fracción de céntimo. |
| Número de horas más caras con las que comparar | 6 | Con cuántas horas caras posteriores se compara una hora. |
| Horas a mirar hacia delante | 18 | Hasta dónde mirar después de una hora para buscar horas caras. |
| Mínimo de horas conocidas por delante | 8 | Se ignoran las horas con menos precios conocidos a continuación. |
| Potencia mínima de carga | 400 W | Límite inferior al repartir. |
| Rendimiento si faltan los contadores | 0,77 | El rendimiento se calcula con los contadores de energía de la Marstek (total descargado ÷ total cargado, limitado a 70–95 %). Este valor fijo solo se aplica cuando faltan esos contadores. El rendimiento en un solo sentido, solo para cargar o solo para descargar, es su raíz cuadrada. |
| Capacidad de la batería | 5,12 kWh | Solo se usa cuando no hay sensor de capacidad. |
| Precio negativo: límite | € 0,00 | Por debajo de este precio horario la batería carga a plena potencia. |
| Venta: beneficio mínimo por kWh | € 0,10 | Lo mínimo que debe rendir vender tras recargar. |
| Venta: consumo propio medio | 400 W | Determina la reserva hasta volver a cargar. |
| Venta: reserva mínima | 20 % | No se vende nada por debajo de este SoC. |
| Precio de venta: factor y deducción | 1 y € 0 | Precio de venta = precio horario × factor − deducción. |

La potencia máxima de carga (*Max. Charge power* de la Marstek) determina el número de horas de
carga. Si la bajas, planifica más horas y carga más suavemente.

## Panel

### Tarjetas de la integración

La integración incluye siete tarjetas; no hace falta añadir ningún recurso. Actualiza el
navegador tras instalar o actualizar. Cada tarjeta se puede configurar tanto en el editor de
tarjetas (el editor visual) como en YAML, y si omites `entity` el sensor del plan de carga se
encuentra automáticamente.

| Tarjeta | Contenido |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Diagrama de flujo: la cronología de hoy y, por parte (carga, venta, precio negativo, retención), qué comprobaciones se superan y dónde se detiene. |
| `custom:marstek-goedkoop-laden-compact-card` | Lo mismo en pocas líneas: la cronología, el resultado por parte con el motivo y una línea con el beneficio. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Solo el beneficio: hoy, esta semana, la semana pasada, este mes y la previsión del plan actual. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Compacta: botones para activar o desactivar la carga, la venta, la carga con precio negativo, la retención y sin pérdidas. |
| `custom:marstek-goedkoop-laden-status-card` | Qué está pasando ahora, el nivel de carga como barra, el precio actual y el siguiente paso. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Gráfico de precios sin tarjetas adicionales: las horas con carga, venta y precios negativos marcadas, y una línea para ahora. |
| `custom:marstek-goedkoop-laden-voorraad-card` | Las existencias cargadas, su precio de coste, el rendimiento, la amortización por kWh y la capacidad. |

```yaml
type: custom:marstek-goedkoop-laden-card
entity: sensor.marstek_goedkoop_laden_laadplan   # optional
title: Price control                             # optional
opbrengst: false                                 # optional, see below
```

La tarjeta de beneficio se puede personalizar, en YAML o en el editor de tarjetas:

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
tiles: [vandaag, maand, jaar]   # any of: vandaag, week, vorige_week, maand, jaar, verwacht (in this order)
expected_details: false         # hide the lines per part of the plan (default: true)
notes: false                    # hide the note below the card (default: true)
```

| Opción | Por defecto | Significado |
|---|---|---|
| `tiles` | las seis | Qué mosaicos mostrar y en qué orden: hoy, esta semana, la semana pasada, este mes, este año, esperado (plan). |
| `expected_details` | `true` | Las líneas con el beneficio esperado por parte (carga, venta). |
| `notes` | `true` | La nota con las existencias cargadas, lo cargado hoy y la amortización. |

Opciones de las demás tarjetas (todas están también en el editor de tarjetas):

| Tarjeta | Opción | Por defecto | Significado |
|---|---|---|---|
| flujo, compacta | `show_timeline` | `true` | Mostrar la cronología de hoy. |
| flujo, compacta, interruptores | `lanes` | las cinco | Qué partes mostrar: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| estado | `show_soc`, `show_price`, `show_next` | `true` | La barra del nivel de carga, el precio actual, el siguiente paso. |
| precios | `hours_back` | `2` | Horas del pasado que se muestran. |
| precios | `hours_ahead` | `0` | Horas por delante que se muestran; 0 es hasta el último precio conocido. |
| precios | `show_values` | `false` | Escribir el precio sobre cada barra (hasta 24 barras). |
| precios | `height` | `140` | Altura del gráfico en píxeles. |
| existencias | `tiles` | las cinco | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`. |
| existencias | `notes` | `true` | La nota bajo la tarjeta. |

`opbrengst` decide si la tarjeta de flujo muestra también el beneficio: desactivado por defecto en
la tarjeta normal, una línea por defecto en la tarjeta compacta. En el diagrama de flujo el verde
es una comprobación que se supera, el rojo es la comprobación donde se detiene y las líneas
discontinuas son un resultado en el que no ocurre nada. Todas las tarjetas leen el atributo
`stroomschema` del sensor del plan de carga.

## Beneficio

**Amortización.** Si indicas un precio de compra, cada kWh que descarga la batería cuesta un poco de desgaste: precio ÷ (ciclos × capacidad). Se resta del beneficio realizado (hoy, semana, mes), se cuenta en el beneficio esperado y se usa en las decisiones: una hora solo merece la pena cargarla si aún supera el desgaste, vender necesita el desgaste además del margen de venta, y *Retener* y *Sin pérdidas* tratan el precio de coste más el desgaste como precio de equilibrio. Con un precio de 0 (por defecto) no cambia nada.

Hay dos tipos de beneficio: lo que se espera que rinda el plan actual y lo que se ha ganado
realmente.

### Esperado (estimación previa)

- **Carga**: lo que cuesta la energía a comprar, frente a lo que vale más tarde. Ese valor es el
  rendimiento por el precio medio de las horas caras con las que se comparó la hora de carga.
- **Venta**: el ingreso del excedente, menos lo que cuesta recargar.

Durante una carga solo cuenta lo que aún falta por cargar.

### Hoy y esta semana (realizado)

1. La energía que la integración carga desde la red (plan de carga o precio negativo) se convierte
   en **existencias**: kWh utilizables = kWh cargados × rendimiento, con el precio de coste que
   costó esa energía en ese momento.
2. Si la batería se descarga después para el consumo propio, se usan primero esas existencias. El
   beneficio es `kWh descargados × (precio de la electricidad en ese momento − precio de coste por kWh utilizable)`.
3. Al vender, el beneficio es `kWh vendidos × precio de venta − precio de coste`; para la energía
   que no procede de las existencias (energía solar), el precio de coste es lo que cuesta recargar.
4. **Hoy** es la suma desde las 00:00, **esta semana** desde el lunes a las 00:00 y **este mes** desde el día uno del mes. **La semana pasada** es la cantidad final de la semana anterior.

Lo que aún está en las existencias no se ha ganado todavía y solo cuenta cuando se usa. La
energía que el sol mete en la batería y que usas tú más tarde no cuenta: la Marstek lo hace
también sin esta integración. Las cantidades proceden de los contadores de energía de la Marstek
y del precio horario en ese momento; un salto de contador tras un fallo no se contabiliza.

### Tarjetas sueltas

Línea del plan (tarjeta Markdown):

```yaml
type: markdown
content: >-
  **Charge plan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ price control is **off**{% endif %}
```

La tarjeta de precios de arriba hace lo mismo sin tarjetas adicionales. Como alternativa, un gráfico con
[apexcharts-card](https://github.com/RomRider/apexcharts-card): los precios de
Zonneplan de hoy y mañana, verde = carga, azul = resto de la ventana barata, gris = otras horas.
Repite la serie tres veces con `'laden'`, `'venster'` y `'rest'` en lugar de `KIES`:

```yaml
type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
now:
  show: true
  label: now
stacked: true
series:
  - entity: sensor.zonneplan_current_hourly_electricity_tariff
    name: Charging
    type: column
    color: "#22c55e"
    data_generator: |
      const a = hass.states['sensor.marstek_goedkoop_laden_laadplan'].attributes;
      const L = new Set((a.laaduren || []).map(s => new Date(s).getTime()));
      const V = new Set((a.venster || []).map(s => new Date(s).getTime()));
      return (entity.attributes.forecast || []).map(i => {
        const t = new Date(i.start_date).getTime();
        const k = L.has(t) ? 'laden' : (V.has(t) ? 'venster' : 'rest');
        return [t, k === 'KIES' ? Math.round(i.price_tax_included.amount / 1e5) / 100 : null];
      });
```

## Desarrollo

La regla de cálculo vive separada de Home Assistant en `planner.py` y tiene pruebas con
precios reales. La lógica de control se prueba contra un Home Assistant simulado
(`tests/test_sturing.py`):

```bash
python3 -m unittest discover -s tests -v
```


## Registro de cambios

Véase [CHANGELOG.md](CHANGELOG.md), incluidos los cambios incompatibles.

## Licencia

Apache 2.0, véase [LICENSE](LICENSE).
