<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Carga Barata para Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · [🇫🇷 Français](README.fr.md) · 🇪🇸 Español · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Recarga una batería doméstica Marstek Venus desde la red en las horas más baratas de un
contrato de electricidad dinámico, para que esté llena antes de que suba el precio.

El punto de partida es el **autoconsumo**: la batería sigue regulándose sola (anti-feed, cero
en el contador). Esta integración añade una sola cosa, cargar desde la red en las horas más
baratas, además de unos cuantos extras opcionales a su alrededor.

**Necesitas:**

- un **contrato de electricidad dinámico** con precios por hora. Con una tarifa fija no hay nada
  que ganar. Se construyó pensando en el mercado neerlandés y en Zonneplan (los precios del día
  siguiente aparecen entre las 13:00 y las 15:00), pero sirve cualquier sensor con una lista de
  precios horarios, véase [Sensor de precios](#sensor-de-precios);
- una Marstek Venus que Home Assistant pueda controlar por RS485 o Modbus, véase
  [Compatibilidad](#compatibilidad). **Solo la configuración LilyGO RS485 + ESPHome se ha probado
  en una batería real.**
- Home Assistant 2026.3 o posterior.

## Qué hace

| Modo | Por defecto | Qué hace |
|---|---|---|
| **Control por precio** | desactivado | Carga desde la red en las horas más baratas y reparte la potencia entre ellas. |
| **Cargar con precio negativo** | activado | Carga cuando el precio horario es negativo y le saca el máximo partido a la ventana. |
| **Previsión solar** | activado | Carga menos por la noche cuando el sol llenará la batería durante el día. Necesita una previsión solar en el panel de Energía. |
| **Retener bajo el precio de coste** | activado | No descarga mientras la red sea más barata de lo que costaron las existencias cargadas. |
| **Sin pérdidas** | desactivado | Versión estricta de retener: además, nunca vende existencias cargadas por debajo del precio de coste. |
| **Venta** | desactivado | Vende el excedente en las horas más caras. |

Cada modo tiene su propio interruptor. **El control por precio está desactivado tras instalar**:
configura la integración, comprueba que el texto del plan en el sensor del plan de carga tiene
buena pinta y entonces actívalo.

## Inicio rápido

1. Instala con HACS (botón de arriba, o añade este repositorio como repositorio personalizado,
   categoría *Integración*), o copia `custom_components/marstek_goedkoop_laden` a
   `/config/custom_components/`. Reinicia Home Assistant.
2. *Ajustes → Dispositivos y servicios → Añadir integración → Marstek Goedkoop Laden*.
3. Elige cómo está conectada tu Marstek, luego el sensor de precios y las entidades de la
   Marstek. Lo que se detecta ya viene rellenado. Con Modbus indicas además el nombre de tu hub
   Modbus (por ejemplo `MarstekVenus`) y la dirección esclava.
4. Activa el interruptor **Control por precio** cuando el plan te parezca correcto.
5. Añade tarjetas: *Editar panel → Añadir tarjeta → busca "Marstek"*, véase
   [Tarjetas del panel](#tarjetas-del-panel).

Los textos (línea del plan, diagrama de flujo, tarjetas) siguen la opción *Idioma*: Automático,
Nederlands, English, Frysk, Deutsch, Français, Español, Svenska o Norsk. Automático sigue a Home
Assistant cuando es uno de ellos, y si no usa inglés.

## Cómo funciona el plan de carga

1. **¿Merece la pena cargar?** Una hora es lo bastante barata si su precio es inferior a
   `rendimiento × (media de las 6 horas más caras de las próximas 18 horas) − margen`. El
   rendimiento (ida y vuelta de carga y descarga, alrededor del 77 % medido aquí) sale de los
   contadores de energía de la Marstek.
2. **Ventana.** El primer bloque de horas baratas es la ventana de carga. Una o dos horas que
   no llegan a ser lo bastante baratas no rompen el bloque; la carga solo ocurre en las propias
   horas baratas.
3. **Horas de carga.** Dentro de esa ventana elige las horas más baratas, exactamente las
   necesarias para pasar del SoC actual al 100 %. Si la ventana es demasiado corta para llenar
   la batería, planifica solo lo que cabe y lo indica en el texto del plan.
4. **Repartir la potencia.** La potencia de carga es la energía que falta por añadir dividida
   entre el tiempo que queda en las horas de carga. Así la carga sobre la conexión a la red se
   mantiene baja. La potencia se ajusta sobre la marcha.
5. **Lo hecho, hecho está.** Cuando terminan las horas de carga o la batería está llena, la
   Marstek vuelve a anti-feed. No arranca de nuevo en la misma ventana.

Solo se usan precios **publicados**, así que el plan para la noche aparece en cuanto se conocen
los precios de mañana. Ejemplo (10 de noviembre de 2026, batería al 12 %): ventana barata
23:00–07:00, carga a las 02:00, 03:00 y 04:00 a unos 1900 W por una media de € 0,37, frente a
€ 0,55–0,67 durante el día.

### Carga con precio negativo

Si el precio horario es negativo, la batería carga, sin importar el plan de carga e incluso con
el control por precio desactivado. Mira toda la **ventana** de horas negativas consecutivas:

1. Calcula cuánto puede admitir aún la batería (del SoC al 100 %).
2. Reparte esa energía entre las horas **según su valor**: cuanto más negativo es el precio,
   más se carga en esa hora, hasta lo que admite una hora a la potencia máxima. Ejemplo:
   −€ 0,03, −€ 0,20 y −€ 0,12 con 3 kWh por cargar dan unos 1,9 kWh en la hora de −€ 0,20 y
   1,2 kWh en la de −€ 0,12. La hora de −€ 0,03 quedaría por debajo de la potencia mínima de
   carga, así que queda fuera y su parte pasa a las otras dos.
3. Repartir mantiene la potencia más baja que una ráfaga corta a plena potencia. Una hora
   aislada que no puede llenar la batería se carga a plena potencia.

La opción *Precio negativo: cómo repartir la energía* se puede poner en **Beneficio máximo**: la
mejor hora se llena primero a plena potencia, luego la siguiente. En el ejemplo eso da unos
€ 0,55 en lugar de € 0,52, a costa de más ráfagas a plena potencia. El plan se recalcula cada
minuto, y una hora que ya estaba en uso recibe un pequeño margen extra antes de quedar fuera.

### Previsión solar

Con paneles solares, la batería se llena gratis durante el día. Si la cargas del todo desde la
red por la noche, el excedente se queda sin sitio y va a la red por poco o nada, algo que
importa más ahora que termina el balance neto (*salderingsregeling*). Por eso la integración
mira el rendimiento solar esperado:

1. Lee la previsión del **panel de Energía** (*Ajustes → Paneles → Energía → Paneles solares →
   Previsión de producción solar*). Funcionan Forecast.Solar, Solcast, Open-Meteo y otras
   integraciones de previsión, sin nada más que configurar. Sin previsión allí, no cambia nada.
2. Calcula el excedente esperado: por hora la previsión, multiplicada por la fiabilidad, menos
   tu consumo propio en esa hora. Las previsiones suelen ser demasiado optimistas, sobre todo en
   invierno. Con *Aprender la fiabilidad a partir de la producción real* activado, la
   integración compara la previsión de cada día con lo que los paneles produjeron realmente (el
   contador de producción del panel de Energía) y usa la mediana de los últimos días como
   fiabilidad, a partir de 3 días. Hasta entonces, y con el aprendizaje desactivado, se aplica el
   ajuste *Fiabilidad de la previsión solar* (por defecto 70 %). Tu consumo propio en esa hora:
   con un *Sensor de potencia de la casa* la integración aprende tu consumo medio por hora del
   día (días laborables y fines de semana por separado) y usa ese valor, de modo que un mediodía
   que la propia casa se come no deja excedente. Sin el sensor se usa el valor fijo de *Venta:
   consumo propio medio*.
3. Por la noche carga solo lo justo para que quede espacio para ese excedente cuando salga el
   sol: lo que gasta tu consumo propio hasta entonces, más lo que aún hace falta. En un día
   soleado pueden ser unos pocos kWh en lugar de una batería llena, o nada (el texto del plan
   dice entonces que el sol llenará la batería). Un día nublado da poco o ningún excedente, y la
   batería se carga del todo.

La previsión se lee cada 30 minutos. Solo reduce la cantidad a cargar; no mueve las horas de
carga ni cambia la venta.

### Retener y sin pérdidas

La energía cargada desde la red tiene un precio de coste: el precio de carga dividido por el
rendimiento. Si la batería devolviera esa energía en horas más baratas que eso, cargar costaría
dinero. Por eso **Retener** bloquea la descarga mientras haya existencias cargadas en la batería
(véase [Beneficio](#beneficio)) y el precio horario esté por debajo del precio de coste de esas
existencias. La casa usa entonces electricidad de la red, que en ese momento es más barata. En
cuanto el precio alcanza el precio de coste, o se agotan las existencias, la Marstek retoma el
control.

Técnicamente, la integración pone la potencia máxima de descarga a 0. La Marstek se queda en
anti-feed, así que la carga con excedente solar continúa. Si otra automatización cambia esa
potencia durante la retención (por ejemplo un limitador para un cargador de coche eléctrico), la
integración recuerda ese valor y lo restaura después. La Marstek no distingue la energía de la
red de la solar, así que durante una retención no se descarga toda la batería. Retener necesita
la entidad de la potencia máxima de descarga.

**Sin pérdidas** es un interruptor aparte y más estricto: se impone la retención aunque el
interruptor de Retener esté desactivado, y no se vende nada por debajo del precio de coste. Cada
kWh contabilizado rinde entonces al menos su precio de coste. Lo que no puede descartar:

- **Bloqueo:** si el precio se mantiene por debajo del precio de coste durante mucho tiempo, la
  batería sigue bloqueada, incluida la energía solar almacenada.
- **Rendimiento diferente:** si la batería devuelve menos que el rendimiento medio, se queda
  vacía antes de agotar las existencias contabilizadas; el resto caduca sin registrar pérdida.
- **El desgaste** no se cuenta salvo que indiques un precio de compra (véase
  [Beneficio](#beneficio)).

### Venta

La venta tiene su propio interruptor y es independiente de la carga. Solo se vende lo que
realmente sobra. Una hora se usa para vender cuando se cumple todo lo siguiente:

1. **Se acerca una carga barata**: hay por delante una ventana de carga con precios publicados,
   así que se conoce el coste de volver a cargar.
2. **El ingreso es claramente superior a recargar**: precio de venta ≥ precio de carga dividido
   por el rendimiento, más el margen de venta (por defecto € 0,10 por kWh).
3. **Hay excedente por encima de la reserva**: el límite de descarga de la Marstek más el
   consumo propio previsto hasta volver a cargar, con un mínimo ajustable (por defecto 20 %).
4. **Es una de las horas más caras** antes de la ventana de carga.

La potencia de venta se reparte entre las horas elegidas; al llegar a la reserva, la venta se
detiene. En invierno rara vez hay excedente; la opción sirve sobre todo cuando el sol llena la
batería y hay un pico de precio por la tarde. Necesita la entidad de la potencia de descarga
forzada.

**Tras el fin del balance neto** (la *salderingsregeling* neerlandesa, 1 de enero de 2027) verter
a la red rinde menos que el precio horario. Entonces ajusta *Precio de venta: factor* y
*deducción*: precio de venta = precio horario × factor − deducción. Para el precio de mercado
puro en Zonneplan son aproximadamente 0,826 y € 0,108.

## Compatibilidad

La integración controla una Marstek Venus a través de sus registros de control RS485.

| Conexión | Modelo | Estado |
|---|---|---|
| LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Probado** en hardware real (la configuración sobre la que se construyó) |
| Hub Modbus en Home Assistant, mediante conversor RS485 a TCP (Elfin EW11 y similares) | Venus E v1/v2 | Probado solo con llamadas simuladas |
| Hub Modbus en Home Assistant, directamente por Ethernet | Venus E v3 | Probado solo con llamadas simuladas |
| Integración *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Probado solo con llamadas simuladas |
| Cualquiera de las anteriores | Venus A, Venus D, otros modelos | **Sin comprobar, sin probar.** Se dice que comparten los registros de control, pero no está verificado. Ajusta la capacidad de la batería en las opciones (por defecto 5,12 kWh). |
| Nube, app u otras integraciones | cualquiera | No compatible |

- **LilyGO T-CAN485 con ESPHome** por RS485, con la configuración de
  [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485). Usa las
  entidades que ofrece esa configuración: *RS485 Control Mode*, *Forcible Charge/Discharge*,
  *Forcible Charge Power* (obligatorias) y, opcionalmente, *Max. Charge Power*,
  *Max. Discharge Power*, *Forcible Discharge Power*, *Discharging Cutoff Capacity* y los
  contadores de energía total cargada/descargada.
- **Modbus en Home Assistant**, con un hub Modbus que defines tú mismo en
  `configuration.yaml`: un Elfin EW11 u otro conversor RS485 a TCP
  ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), o la
  **Venus E v3 directamente por Ethernet** (Modbus TCP, puerto 502, unidad 1, EMS V144 o posterior;
  [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)). La
  integración lee los sensores de registros de esa configuración y escribe los registros 42000
  (control RS485), 42010 (modo forzado), 42020/42021 (potencia de carga/descarga forzada) y, si
  indicas los sensores, 44002/44003 (potencia máxima de carga/descarga) con
  `modbus.write_register`. Sin la potencia máxima de descarga, *Retener* y *Sin pérdidas* no están
  disponibles. La Venus E v3 guarda su nivel de carga en el registro 34002 (escala 0,1), no en
  el 32104.
- **La integración *Marstek Venus Modbus***
  ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), que
  también habla Modbus TCP. Elígela si ya la usas: aporta las entidades (`switch` modo de
  control RS485, `select` modo forzado, `number` potencias). Activa antes allí el interruptor
  *RS485 control mode* y el selector *Force mode*, que vienen desactivados por defecto.

### Qué envía la integración a la Marstek

| Momento | Comandos |
|---|---|
| Empezar a cargar | fijar potencia de carga → modo forzado `charge` → control RS485 `enable` |
| Durante la carga | ajustar la potencia de carga (pasos de 100 W) |
| Terminado, o control por precio desactivado | control RS485 `disable`, modo forzado de vuelta a `charge`, potencia de carga de vuelta al máximo |
| Empezar a vender | fijar potencia de descarga → modo forzado `discharge` → control RS485 `enable` |
| Venta terminada, o venta desactivada | igual que terminado: de vuelta al estado de reposo |

La **des**carga forzada que inicies tú mismo se deja como está. La carga forzada que inicies tú
mismo se restablece mientras el control por precio esté activado; desactívalo antes si quieres eso.

## Ajustes

En *Configurar* dentro de la integración. Las opciones están en grupos; las entidades están en un
grupo plegado al final.

### Sensor de precios

La integración lee los precios de un atributo de un sensor (por defecto `forecast`):

- Precios horarios de Zonneplan: `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (antiguo): `datetime`, `electricity_price`
- Genérico: `start` (o `start_time`, `datetime`) y `price` (o `value`, `prijs`) en €/kWh

### Opciones

| Grupo | Ajuste | Por defecto | Significado |
|---|---|---|---|
| | Idioma | Automático | Idioma del texto del plan, el diagrama de flujo y las tarjetas. |
| Batería | Capacidad de la batería | 5,12 kWh | Solo se usa cuando no hay sensor de capacidad. |
| Batería | Rendimiento si faltan los contadores | 0,77 | El rendimiento se calcula con los contadores de energía de la Marstek (total descargado ÷ total cargado, limitado a 70–95 %). Este valor fijo solo se aplica cuando faltan esos contadores. El rendimiento en un solo sentido es su raíz cuadrada. |
| Batería | Precio de compra de la batería | € 0 | Se usa para la amortización. 0 la desactiva. |
| Batería | Vida útil de la batería (ciclos) | 6000 | Amortización por kWh = precio ÷ (ciclos × capacidad); € 1500 en 6000 ciclos de 5,12 kWh son unos € 0,049 por kWh. |
| Batería | Límite de descarga | 12 % | Se usa cuando no hay entidad de límite de descarga. |
| Carga | Beneficio mínimo por kWh | € 0,02 | Lo mínimo que debe rendir cargar, tras las pérdidas de carga. Las horas que están menos de medio céntimo por encima del límite también cuentan, para que una noche casi plana no se trocee por una fracción de céntimo. |
| Carga | Potencia mínima de carga | 400 W | Límite inferior al repartir. |
| Carga | Atributo con los precios | `forecast` | El atributo del sensor de precios con los precios horarios. |
| Carga | Número de horas más caras con las que comparar | 6 | Con cuántas horas caras posteriores se compara una hora. |
| Carga | Horas a mirar hacia delante | 18 | Hasta dónde mirar después de una hora para buscar horas caras. |
| Carga | Mínimo de horas conocidas por delante | 8 | Se ignoran las horas con menos precios conocidos a continuación. |
| Precio negativo | Precio negativo: límite | € 0,00 | Por debajo de este precio horario la batería carga. |
| Precio negativo | Precio negativo: cómo repartir la energía | Por valor | Repartir por valor (menor potencia) o beneficio máximo (mejores horas primero). |
| Solar | Usar la previsión solar | Activado | Tener en cuenta el rendimiento solar esperado del panel de Energía al cargar por la noche. |
| Solar | Aprender la fiabilidad a partir de la producción real | Activado | Compara la previsión solar de cada día con lo que los paneles produjeron realmente y usa la mediana de los últimos días como fiabilidad (a partir de 3 días). |
| Solar | Fiabilidad de la previsión solar | 70 % | La parte de la previsión con la que contar. Más baja es más prudente. |
| Solar | Sensor de potencia de la casa | ninguno | Sensor opcional con la potencia que consume toda la casa (W o kW), sin la batería. Un cargador de coche distorsiona la media, así que déjalo fuera si puedes. |
| Venta | Venta: beneficio mínimo por kWh | € 0,10 | Lo mínimo que debe rendir vender tras recargar. |
| Venta | Venta: consumo propio medio | 400 W | Determina la reserva hasta volver a cargar, y es el consumo propio fijo para el excedente solar. |
| Venta | Venta: reserva mínima | 20 % | No se vende nada por debajo de este SoC. |
| Venta | Precio de venta: factor y deducción | 1 y € 0 | Precio de venta = precio horario × factor − deducción. |

La potencia máxima de carga (*Max. Charge power* de la Marstek) determina el número de horas de
carga. Si la bajas, planifica más horas y carga más suavemente.

## Tarjetas del panel

La integración incluye siete tarjetas; no hace falta añadir ningún recurso. Actualiza el
navegador tras instalar o actualizar. Cada tarjeta se puede configurar tanto en el editor de
tarjetas como en YAML, y si omites `entity` el sensor del plan de carga se encuentra
automáticamente.

| Tarjeta | Contenido |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Diagrama de flujo: la cronología de hoy y, por parte (carga, venta, precio negativo, retención), qué comprobaciones se superan y dónde se detiene. |
| `custom:marstek-goedkoop-laden-compact-card` | Lo mismo en pocas líneas: la cronología, el resultado por parte con el motivo y una línea con el beneficio. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Solo el beneficio: hoy, esta semana, la semana pasada, este mes, este año y la previsión del plan actual. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Compacta: botones para activar o desactivar los modos. |
| `custom:marstek-goedkoop-laden-status-card` | Qué está pasando ahora, el nivel de carga como barra, el precio actual y el siguiente paso. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Gráfico de precios sin tarjetas adicionales: las horas con carga, venta y precios negativos marcadas, y una línea para ahora. |
| `custom:marstek-goedkoop-laden-voorraad-card` | Las existencias cargadas, su precio de coste, el rendimiento, la amortización por kWh y la capacidad. |

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
entity: sensor.marstek_goedkoop_laden_plan_de_carga   # opcional
title: Beneficio                                      # opcional
tiles: [vandaag, maand, jaar]                         # qué mosaicos, en este orden
notes: false                                          # oculta la nota bajo la tarjeta
```

| Tarjeta | Opción | Por defecto | Significado |
|---|---|---|---|
| todas | `entity`, `title` | automático, ninguno | El sensor del plan de carga y un título. |
| flujo, compacta | `show_timeline` | `true` | Mostrar la cronología de hoy. |
| flujo, compacta | `opbrengst` | no, una línea | Mostrar también el beneficio. |
| flujo, compacta, interruptores | `lanes` | las cinco | Qué partes mostrar: `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| beneficio | `tiles` | las seis | Cualquiera de `vandaag`, `week`, `vorige_week`, `maand`, `jaar`, `verwacht`, en este orden. |
| beneficio | `expected_details`, `notes` | `true` | Las líneas por parte del plan; la nota con existencias, carga de hoy y amortización. |
| estado | `show_soc`, `show_price`, `show_next` | `true` | La barra del nivel de carga, el precio actual, el siguiente paso. |
| precios | `hours_back`, `hours_ahead` | `2`, `0` | Horas del pasado; horas por delante (0 es hasta el último precio conocido). |
| precios | `show_values`, `height` | `false`, `140` | Escribir el precio sobre cada barra (hasta 24 barras); altura en píxeles. |
| existencias | `tiles`, `notes` | las cinco, `true` | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`; la nota bajo la tarjeta. |

En el diagrama de flujo el verde es una comprobación que se supera, el rojo es la comprobación
donde se detiene y las líneas discontinuas son un resultado en el que no ocurre nada. Línea del
plan en una tarjeta Markdown:

```yaml
type: markdown
content: >-
  **Plan de carga:** {{ state_attr('sensor.marstek_goedkoop_laden_plan_de_carga', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_control_por_precio', 'off') %}
  · ⚠️ el control por precio está **desactivado**{% endif %}
```

## Beneficio

Hay dos tipos de beneficio: lo que se espera que rinda el plan actual y lo que se ha ganado
realmente.

**Esperado (estimación previa).** Carga: lo que cuesta la energía a comprar, frente a lo que vale
más tarde (el rendimiento por el precio medio de las horas caras con las que se comparó la hora
de carga). Venta: el ingreso del excedente, menos lo que cuesta recargar. Durante una carga solo
cuenta lo que aún falta por cargar.

**Realizado (hoy, semana, mes, año).**

1. La energía que la integración carga desde la red (plan de carga o precio negativo) se convierte
   en **existencias**: kWh utilizables = kWh cargados × rendimiento, con el precio de coste que
   costó esa energía en ese momento.
2. Si la batería se descarga después para el consumo propio, se usan primero esas existencias. El
   beneficio es `kWh descargados × (precio de la electricidad en ese momento − precio de coste por kWh utilizable)`.
3. Al vender, el beneficio es `kWh vendidos × precio de venta − precio de coste`; para la energía
   que no procede de las existencias (energía solar), el precio de coste es lo que cuesta recargar.
4. **Hoy** cuenta desde las 00:00, **esta semana** desde el lunes a las 00:00, **este mes** desde
   el día uno y **este año** desde el 1 de enero. **La semana pasada** es la cantidad final de la
   semana anterior.

Lo que aún está en las existencias no se ha ganado todavía y solo cuenta cuando se usa. La
energía que el sol mete en la batería y que usas tú más tarde no cuenta: la Marstek lo hace
también sin esta integración. Las cantidades proceden de los contadores de energía de la Marstek
y del precio horario en ese momento; un salto de contador tras un fallo no se contabiliza.

**Amortización.** Si indicas un precio de compra, cada kWh que descarga la batería cuesta un poco
de desgaste: precio ÷ (ciclos × capacidad). Se resta del beneficio realizado, se cuenta en el
beneficio esperado y se usa en las decisiones: una hora solo merece la pena cargarla si aún
supera el desgaste, vender necesita el desgaste además del margen de venta, y *Retener* y
*Sin pérdidas* tratan el precio de coste más el desgaste como precio de equilibrio. Con un precio
de 0 (por defecto) no cambia nada.

## Entidades

| Entidad | Contenido |
|---|---|
| `switch.*_control_por_precio` | Activado: se ejecuta el plan de carga. Desactivado: la Marstek lo regula todo sola. |
| `switch.*_cargar_con_precio_negativo` | Activado (por defecto): carga cuando el precio horario es negativo. |
| `switch.*_retener_bajo_el_precio_de_coste` | Activado (por defecto): no descarga por debajo del precio de coste de las existencias. |
| `switch.*_sin_perdidas` | Activado: se impone la retención y nunca se vende por debajo del precio de coste. |
| `switch.*_venta` | Activado: el excedente se vende en las horas más caras. Independiente del control por precio. |
| `sensor.*_plan_de_carga` | Estado: `laden`, `gepland`, `klaar`, `vol`, `geen` u `onbekend`. Atributos: `tekst` (resumen legible), `laaduren`, `venster`, `stroomschema` (cronología, comprobaciones, precios y resumen para las tarjetas) y más. |
| `sensor.*_plan_de_venta` | Estado: `verkopen`, `gepland`, `geen` u `onbekend`. Atributos: `verkoopuren`, `overschot_kwh`, `reserve_soc`, `tekst` y más. |
| `sensor.*_potencia_de_carga_planificada`, `*_energia_por_cargar`, `*_inicio_de_la_carga`, `*_fin_de_la_carga`, `*_precio_medio_de_carga` | La potencia de carga repartida en W, la energía que aún falta por cargar en kWh, inicio y fin de la carga planificada, y su precio medio en €/kWh. |
| `sensor.*_beneficio_de_hoy`, `*_beneficio_de_esta_semana`, `*_beneficio_de_la_semana_pasada`, `*_beneficio_de_este_mes`, `*_beneficio_de_este_ano` | Beneficio realizado en euros (véase [Beneficio](#beneficio)). |
| `sensor.*_beneficio_esperado` | Beneficio estimado de los planes actuales en euros; el atributo `regels` contiene el desglose. |
| `sensor.*_rendimiento` | El rendimiento usado, en porcentaje. Atributo `bron`: medido o fijo. |

Los nombres de las entidades siguen el idioma de Home Assistant en el momento de crearlas (con
neerlandés se llaman `*_laadplan`, `*_prijssturing` y así sucesivamente). **Los valores de estado
y los nombres de atributos están en neerlandés en todos los idiomas** (`laden`, `tekst`, …); son
fijos para que las automatizaciones sigan funcionando.

## Desarrollo

La regla de cálculo vive separada de Home Assistant en `planner.py` y tiene pruebas con
precios reales. La lógica de control se prueba contra un Home Assistant simulado:

```bash
python3 -m unittest discover -s tests -v
```

## Registro de cambios

Véase [CHANGELOG.md](CHANGELOG.md), incluidos los cambios incompatibles.

## Agradecimientos

Esta integración se apoya en el trabajo de la comunidad de Marstek Venus:

- El [hilo del foro de Tweakers](https://gathering.tweakers.net/forum/list_messages/2282240/0) donde se comenta este trabajo comunitario, una mención de honor para todos los que comparten allí hallazgos y configuraciones.
- [Superduper1969](https://github.com/Superduper1969) por las configuraciones de LilyGO RS485 y Elfin EW11 en torno a las que se ha construido esta integración, y scruysberghs, a quien se agradece en esas configuraciones.
- [fonske](https://github.com/fonske) por la configuración Modbus TCP de la Venus E v3.
- [ViperRNMC](https://github.com/ViperRNMC) por la integración Marstek Venus Modbus.

## Licencia

Apache 2.0, véase [LICENSE](LICENSE).
