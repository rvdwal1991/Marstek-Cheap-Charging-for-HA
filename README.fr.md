<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Charge économique pour Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · 🇫🇷 Français · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Recharge une batterie domestique Marstek Venus depuis le réseau pendant les heures les moins
chères d'un contrat d'électricité dynamique, afin qu'elle soit pleine avant que les prix ne montent.

Le point de départ est l'**autosuffisance**. La batterie continue de se réguler seule (anti-feed,
zéro au compteur). Cette intégration n'ajoute qu'une chose : la charge depuis le réseau pendant
les heures les moins chères. Il existe aussi une option distincte, désactivée par défaut, pour
**vendre le surplus** pendant les heures les plus chères.

> **Matériel et compatibilité.** L'intégration pilote une Marstek Venus via ses registres de
> commande RS485. Seule la première ligne a été éprouvée sur une vraie batterie :
>
> | Connexion | Modèle | État |
> |---|---|---|
> | LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Testé** sur du vrai matériel (l'installation sur laquelle elle a été conçue) |
> | Hub Modbus dans Home Assistant, via un convertisseur RS485 vers TCP (Elfin EW11 et similaires) | Venus E v1/v2 | Testé uniquement avec des appels simulés |
> | Hub Modbus dans Home Assistant, directement en Ethernet | Venus E v3 | Testé uniquement avec des appels simulés |
> | Intégration *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Testé uniquement avec des appels simulés |
> | N'importe laquelle des précédentes | Venus A, Venus D, autres modèles | **Non vérifié, non testé.** Elles partageraient les registres de commande, mais ce n'est pas confirmé. Réglez la capacité de la batterie dans les options (par défaut 5,12 kWh). |
> | Cloud, appli ou autres intégrations | toutes | Non pris en charge |
>
> Les connexions en détail :
>
> - **LilyGO T-CAN485 sous ESPHome** via RS485, avec la configuration
>   [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485).
>   C'est l'installation sur laquelle l'intégration a été conçue et testée. Elle utilise les
>   entités que cette installation expose : *RS485 Control Mode*, *Forcible Charge/Discharge*,
>   *Forcible Charge Power* (obligatoire) et, en option, *Max. Charge Power*, *Max. Discharge Power*,
>   *Forcible Discharge Power*, *Discharging Cutoff Capacity* ainsi que les compteurs d'énergie
>   totale chargée/déchargée.
> - **Modbus dans Home Assistant**, avec un hub Modbus que vous définissez vous-même dans
>   `configuration.yaml` : un Elfin EW11 ou un autre convertisseur RS485 vers TCP
>   ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), ou la
>   **Venus E v3 directement en Ethernet** (Modbus TCP, port 502, unité 1, EMS V144 ou plus récent ;
>   [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)).
>   L'intégration lit les capteurs de registres de cette installation et écrit les registres 42000
>   (contrôle RS485), 42010 (mode de forçage), 42020/42021 (puissance de charge/décharge forcée) et,
>   si vous indiquez les capteurs, 44002/44003 (puissance de charge/décharge maximale) avec
>   `modbus.write_register`. Avec la puissance de décharge maximale, *Maintien* et *Sans perte*
>   fonctionnent aussi ; sans elle, ils ne sont pas disponibles. La Venus E v3 conserve son état de
>   charge dans le registre 34002 (échelle 0,1), et non dans le 32104.
> - **L'intégration *Marstek Venus Modbus***
>   ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), qui
>   parle aussi Modbus TCP (Ethernet sur une Venus E v3, ou une passerelle RS485). Choisissez-la si
>   vous utilisez déjà cette intégration : elle fournit les entités (`switch` mode de contrôle RS485,
>   `select` mode de forçage, `number` puissances). Activez-y d'abord l'interrupteur *RS485 control
>   mode* et le select *Force mode*, ils sont désactivés par défaut.
>
> Les options Modbus et Marstek Venus Modbus sont **nouvelles et, pour l'instant, testées
> uniquement avec des appels simulés, pas sur du vrai matériel**.
>
> Les autres façons de connecter la batterie (cloud, autres intégrations) n'ont pas été testées et
> ne fonctionnent très probablement pas, car elles ne proposent pas ces entités de contrôle RS485.
>
> **Prix dynamiques de l'énergie :** cette intégration n'a de sens qu'avec un **contrat d'électricité
> dynamique**, où le prix change chaque heure. Elle charge pendant les heures les moins chères et
> évite les chères ; avec un tarif fixe, il n'y a donc rien à gagner. Elle a été conçue autour du
> marché néerlandais et des prix Zonneplan (prix horaires, publiés pour le lendemain entre 13:00 et
> 15:00). Tout capteur de prix dont un attribut contient une liste de prix horaires convient, voir
> [Capteur de prix](#capteur-de-prix).
>
> **Langue :** le texte du plan, le schéma de flux et les cartes suivent l'option *Langue*
> (Automatique, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska ou Norsk ;
> Automatique suit Home Assistant quand c'en est une, sinon l'anglais). Les noms d'entités suivent la langue de Home Assistant. Les valeurs d'état et les noms d'attributs (`laden`, `tekst`, …) sont fixes.

## Ce qu'elle fait

1. **La charge vaut-elle le coup ?** Une heure est assez bon marché si son prix est inférieur à
   `rendement × (moyenne des 6 heures les plus chères des 18 prochaines heures) − marge`.
   Le rendement (aller-retour charge et décharge, environ 77 % sur mon unité) est mesuré à partir
   des compteurs d'énergie de la Marstek.
2. **Fenêtre.** Le premier bloc d'heures bon marché est la fenêtre de charge. Une ou deux heures
   à peine trop chères ne brisent pas le bloc ; la charge n'a lieu que pendant les heures
   bon marché elles-mêmes.
3. **Heures de charge.** Dans cette fenêtre, elle choisit les heures les moins chères, juste
   assez pour passer du SoC actuel à 100 %. Si la fenêtre est trop courte pour remplir la
   batterie, elle ne planifie que ce qui tient et le signale dans le texte du plan.
4. **Étaler la puissance.** La puissance de charge est l'énergie restant à ajouter divisée par le
   temps restant dans les heures de charge. Cela ménage au maximum le raccordement au réseau et le
   circuit de la maison. La puissance est ajustée en cours de route.
5. **Terminé, c'est terminé.** Quand les heures de charge sont écoulées ou que la batterie est
   pleine, la Marstek repasse en anti-feed. Elle ne redémarre pas dans la même fenêtre et ne
   maintient pas la charge.

Seuls les prix **publiés** sont utilisés. Le plan de la nuit apparaît donc dès que les prix de
demain sont connus (avec Zonneplan entre 13:00 et 15:00).

Exemple (10 novembre 2026, batterie à 12 %) : fenêtre bon marché 23:00–07:00, charge à 02:00,
03:00 et 04:00 à environ 1900 W pour une moyenne de € 0,37, contre € 0,55–0,67 en journée.

## Charge à prix négatif

Si le prix horaire est négatif, la batterie charge depuis le réseau, indépendamment du plan de
charge et même quand le pilotage par les prix est désactivé. Cette fonction a son propre
interrupteur, **activé par défaut**.

Elle examine toute la **fenêtre** d'heures négatives consécutives, pas seulement l'heure en cours,
et en tire le meilleur parti :

1. Elle calcule ce que la batterie peut encore absorber (du SoC à 100 %).
2. Elle répartit cette énergie sur les heures **selon leur valeur** : plus le prix est négatif,
   plus on charge pendant cette heure (dans la limite de ce qu'une heure peut absorber à la
   puissance maximale). Exemple : trois heures négatives à −€ 0,03, −€ 0,20 et −€ 0,12 et 3 kWh
   encore à charger. L'heure à −€ 0,20 reçoit environ 1,9 kWh et l'heure à −€ 0,12 environ 1,2 kWh.
   L'heure à −€ 0,03 resterait sous la puissance de charge minimale ; elle est donc écartée et sa
   part revient aux deux autres.
3. Comme l'énergie est étalée sur les heures, la puissance reste plus faible que si l'on chargeait
   à pleine puissance pendant un court instant. Si la batterie peut absorber plus que ce que la
   fenêtre offre, chaque heure est remplie au maximum. Une heure isolée qui ne peut pas remplir
   la batterie est chargée à pleine puissance.
4. Le texte du plan et le schéma de flux montrent la fenêtre, les heures choisies, la puissance et
   le gain attendu (ce que l'on vous paie pour charger).

L'option *Prix négatif : répartition de l'énergie* permet de choisir entre deux méthodes :

- **Répartie selon la valeur** (par défaut) : comme décrit ci-dessus, puissance plus faible, gain
  légèrement inférieur.
- **Gain maximal** : les heures sont remplies une à une, meilleur prix d'abord, chacune à pleine
  puissance, et le reste va à la meilleure heure suivante. Dans l'exemple, l'heure à −€ 0,20 absorbe
  2,25 kWh à pleine puissance et l'heure à −€ 0,12 les 0,8 kWh restants, ce qui rapporte environ
  € 0,55 au lieu de € 0,52. Le prix à payer : davantage de courtes périodes à pleine puissance.

Dès que le prix redevient positif ou que la batterie est pleine, la Marstek repasse en
anti-feed. Le plan est recalculé chaque minute ; une heure déjà en cours obtient un peu de marge
supplémentaire avant d'être écartée pour cause de puissance sous le minimum.

La limite est réglable (*Prix négatif : limite*, par défaut € 0,00). Le prix provient du capteur
de prix ; avec Zonneplan, c'est donc le prix taxes comprises.

## Maintien sous le prix de revient

L'énergie chargée depuis le réseau a un prix de revient : le prix de charge divisé par le
rendement. Si la batterie restituait cette énergie juste après la charge, pendant des heures
moins chères que ce prix de revient, la charge coûterait de l'argent. La décharge est donc
bloquée tant que :

- il y a du stock chargé dans la batterie (voir *Gain*), et
- le prix horaire est inférieur au prix de revient de ce stock.

La maison utilise alors le courant du réseau, qui est à ce moment-là moins cher que ce qui se
trouve dans la batterie. Dès que le prix atteint le prix de revient, ou que le stock est épuisé,
la Marstek reprend la main. Cette fonction a son propre interrupteur, **activé par défaut**.

Techniquement, l'intégration met la puissance de décharge maximale (*Max. Discharge power*) à 0.
La Marstek reste en anti-feed, donc la charge par le surplus solaire se poursuit. Si une autre
automatisation règle cette puissance sur une autre valeur pendant le maintien (par exemple un
limiteur pour une borne de recharge de véhicule électrique), l'intégration mémorise cette valeur,
la remet à 0 puis rétablit ensuite la valeur mémorisée.

Remarque : la Marstek ne distingue pas l'énergie chargée depuis le réseau de l'énergie solaire.
Pendant un maintien, toute la batterie reste donc sans décharge.

## Sans perte

Un interrupteur distinct (désactivé par défaut) qui rend l'intégration stricte : l'énergie
chargée depuis le réseau n'est jamais utilisée ni vendue sous son prix de revient.

- **Le maintien est imposé**, même si l'interrupteur *Maintien* est désactivé.
- **La vente sous le prix de revient est bloquée.** S'il y a du stock chargé dans la batterie et
  que le prix de vente est inférieur à son prix de revient, rien n'est vendu.

Chaque kWh comptabilisé rapporte alors au moins son prix de revient, de sorte que le gain d'une
journée ne peut pas passer sous zéro. Ce qu'elle ne peut pas exclure :

- **L'immobilisation.** Si le prix reste longtemps sous le prix de revient, la batterie reste
  bloquée en décharge, y compris pour l'énergie solaire stockée.
- **Un rendement différent.** Le prix de revient utilise le rendement moyen. Si la batterie
  restitue moins que cela sur un cycle, elle est vide avant que le stock comptabilisé soit
  utilisé ; le reste expire sans enregistrer de perte.
- **L'usure** de la batterie n'est pas comptée ; utilisez pour cela le gain minimal par kWh.

L'intégration recalcule immédiatement au début d'une nouvelle période de prix, de sorte qu'un
maintien ne démarre jamais avec jusqu'à une minute de retard.

## Vente (facultative)

La vente a son propre interrupteur et est indépendante de la charge. Seul ce qui reste vraiment en
surplus est vendu. Une heure est retenue pour la vente quand tout ceci est vrai :

1. **Une charge bon marché approche** : une fenêtre de charge aux prix publiés se profile, de
   sorte que le coût de la recharge est connu.
2. **Le revenu est nettement supérieur à celui de la recharge** : prix de vente ≥ prix de charge
   divisé par le rendement, plus la marge de vente (par défaut € 0,10 par kWh).
3. **Il y a un surplus au-dessus de la réserve.** La réserve est le seuil de décharge de la
   Marstek plus la consommation propre attendue jusqu'à la recharge (puissance moyenne de la
   maison × heures), avec un minimum réglable (par défaut 20 %).
4. **C'est l'une des heures les plus chères** avant la fenêtre de charge.

Comme pour la charge, la puissance de vente est étalée sur les heures choisies. À la réserve, la
vente s'arrête et la Marstek repasse en anti-feed.

En hiver, il y a rarement un surplus : avec une batterie de 5 kWh, la consommation propre
jusqu'à la prochaine charge absorbe généralement toute la charge. L'option sert surtout quand le
soleil remplit la batterie et qu'il y a un pic de prix en soirée.

**Après la fin de la compensation** (la *salderingsregeling* néerlandaise, 1er janvier 2027),
l'injection rapporte moins que le prix horaire. Réglez alors *Prix de vente : facteur* et
*déduction* : prix de vente = prix horaire × facteur − déduction. Pour le prix de marché brut chez
Zonneplan, cela donne environ 0,826 et € 0,108.

## Pilotage de la Marstek

L'intégration pilote la batterie via l'interface RS485 (LilyGO T-CAN485 avec
ESPHome) :

| Moment | Commandes |
|---|---|
| Début de la charge | régler la puissance de charge → *Forcible charge/discharge* sur `charge` → *RS485 Control Mode* sur `enable` |
| Pendant la charge | ajuster la puissance de charge (par pas de 100 W) |
| Terminé, ou pilotage par les prix désactivé | *RS485 Control Mode* sur `disable`, forçage de nouveau sur `charge`, puissance de charge de nouveau au maximum |
| Début de la vente | régler la puissance de décharge → forçage sur `discharge` → *RS485 Control Mode* sur `enable` |
| Vente terminée, ou vente désactivée | comme pour « terminé » : retour à l'état de repos |

La **dé**charge forcée que vous lancez vous-même est laissée en l'état. La charge forcée que vous
lancez vous-même est réinitialisée tant que le pilotage par les prix est activé ; désactivez-le
d'abord si vous le souhaitez.

## Entités

| Entité | Contenu |
|---|---|
| `switch.*_price_control` | Activé : le plan de charge est exécuté. Désactivé : la Marstek régule tout elle-même. Le désactiver remet immédiatement la Marstek en anti-feed. |
| `switch.*_charge_at_negative_price` | Activé (par défaut) : toujours charger à pleine puissance quand le prix horaire est négatif. Attribut `nu_actief`. |
| `switch.*_hold_below_cost_price` | Activé (par défaut) : ne pas décharger tant que le prix horaire est inférieur au prix de revient du stock chargé. Attributs `nu_actief`, `tot`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_no_loss` | Activé : maintien imposé et jamais de vente sous le prix de revient. Attributs `vasthouden_actief`, `verkoop_tegengehouden`, `voorraad_kwh`, `kostprijs`. |
| `switch.*_selling` | Activé : le surplus est vendu pendant les heures les plus chères. Indépendant du pilotage par les prix. |
| `sensor.*_sell_plan` | État : `verkopen`, `gepland`, `geen` ou `onbekend`. Attributs : `verkoopuren`, `vermogen`, `overschot_kwh`, `reserve_soc`, `drempelprijs`, `terugkoopprijs` et `tekst`. |
| `sensor.*_charge_plan` | État : `laden`, `gepland`, `klaar`, `vol`, `geen` ou `onbekend`. Attributs : `laaduren`, `venster`, `eind`, `uren_nodig`, `vermogen`, `klaar_tot`, `tekst` (résumé lisible) et `stroomschema` (chronologie et contrôles pour la carte). |
| `sensor.*_planned_charge_power` | La puissance de charge étalée, en W. |
| `sensor.*_energy_to_charge` | Énergie à tirer du réseau pour remplir la batterie, en kWh. |
| `sensor.*_charge_start` / `*_charge_end` | Début et fin de la charge planifiée. |
| `sensor.*_gain_today` / `*_gain_this_week` / `*_gain_this_month` | Gain réalisé en euros depuis 00:00, depuis lundi 00:00 et depuis le premier du mois (voir *Gain*). Attributs : le stock et, pour aujourd'hui, ce qui a été chargé et utilisé. |
| `sensor.*_gain_this_year` | Gain réalisé depuis le 1er janvier. |
| `sensor.*_gain_last_week` | Le gain définitif de la semaine précédente. |
| `sensor.*_expected_gain` | Gain estimé des plans en cours en euros (charge plus vente) ; l'attribut `regels` contient le détail. |
| `sensor.*_efficiency` | Le rendement utilisé, en pourcentage. Attribut `bron` : mesuré à partir des compteurs d'énergie ou valeur fixe. |
| `sensor.*_average_charge_price` | Prix moyen des heures de charge en €/kWh. |

Les noms ci-dessus correspondent à une installation en anglais. Avec Home Assistant réglé en
néerlandais, ils s'appellent `*_laadplan`, `*_prijssturing`, etc. Les valeurs d'état et les noms
d'attributs sont identiques dans les deux langues.

## Installation

1. Installez avec HACS (bouton ci-dessus, ou ajoutez ce dépôt comme dépôt personnalisé, catégorie
   *Intégration*), ou copiez `custom_components/marstek_goedkoop_laden` dans
   `/config/custom_components/`. Redémarrez Home Assistant.
2. Allez dans *Paramètres → Appareils et services → Ajouter une intégration → Marstek Goedkoop Laden*.
3. Choisissez comment votre Marstek est connectée (*LilyGO RS485 avec ESPHome*, *Modbus dans Home Assistant* ou *Intégration Marstek Venus Modbus*),
   puis le capteur de prix et les entités de la Marstek. Ce qui est détecté est prérempli. Pour Modbus,
   vous indiquez aussi le nom de votre hub Modbus (par exemple `MarstekVenus`) et l'adresse esclave.

Nécessite Home Assistant 2026.3 ou plus récent.

### Capteur de prix

L'intégration lit les prix dans un attribut d'un capteur (par défaut `forecast`) :

- Prix horaires Zonneplan : `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (ancien) : `datetime`, `electricity_price`
- Générique : `start` (ou `start_time`, `datetime`) et `price` (ou `value`, `prijs`) en €/kWh

### Réglages

Sous *Configurer* dans l'intégration :

| Réglage | Par défaut | Signification |
|---|---|---|
| Langue | Automatique | Langue du texte du plan, du schéma de flux et des cartes : Automatique, Nederlands, English, Frysk, Deutsch, Français, Español, Svenska ou Norsk. |
| Prix d'achat de la batterie | € 0 | Sert à l'amortissement. 0 désactive l'amortissement. |
| Durée de vie de la batterie (cycles) | 6000 | Nombre attendu de cycles complets. Amortissement par kWh = prix ÷ (cycles × capacité) ; par exemple € 1 500 sur 6 000 cycles de 5,12 kWh font environ € 0,049 par kWh. |
| Gain minimal par kWh | € 0,02 | Ce que la charge doit rapporter au minimum, après les pertes de charge. Les heures qui dépassent la limite de moins d'un demi-centime comptent quand même, afin qu'une nuit presque plate ne soit pas découpée pour une fraction de centime. |
| Nombre d'heures les plus chères | 6 | Avec combien d'heures chères ultérieures une heure est comparée. |
| Heures à anticiper | 18 | Jusqu'où regarder après une heure pour trouver les heures chères. |
| Minimum d'heures connues à l'avance | 8 | Les heures suivies de moins de prix connus que cela sont ignorées. |
| Puissance de charge minimale | 400 W | Limite basse lors de l'étalement. |
| Rendement en l'absence de compteurs | 0,77 | Le rendement est calculé à partir des compteurs d'énergie de la Marstek (total déchargé ÷ total chargé, borné à 70–95 %). Cette valeur fixe ne s'applique que si ces compteurs sont absents. Le rendement à sens unique, pour la charge ou la décharge seule, en est la racine carrée. |
| Capacité de la batterie | 5,12 kWh | Utilisée uniquement si aucun capteur de capacité n'est défini. |
| Prix négatif : limite | € 0,00 | Sous ce prix horaire, la batterie charge à pleine puissance. |
| Vente : gain minimal par kWh | € 0,10 | Ce que la vente doit rapporter au minimum après la recharge. |
| Vente : consommation propre moyenne | 400 W | Détermine la réserve jusqu'à la recharge. |
| Vente : réserve minimale | 20 % | Rien n'est vendu sous ce SoC. |
| Prix de vente : facteur et déduction | 1 et € 0 | Prix de vente = prix horaire × facteur − déduction. |

La puissance de charge maximale (la *Max. Charge power* de la Marstek) détermine le nombre
d'heures de charge. Réglez-la plus bas et elle planifie plus d'heures et charge plus doucement.

## Tableau de bord

### Cartes de l'intégration

L'intégration fournit sept cartes ; aucune ressource n'est à ajouter. Actualisez le navigateur
après l'installation ou une mise à jour. Chaque carte peut être configurée dans l'éditeur de carte
(l'éditeur visuel) comme en YAML, et si vous omettez `entity`, le capteur du plan de charge est
trouvé automatiquement.

| Carte | Contenu |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Schéma de flux : la chronologie du jour et, par partie (charge, vente, prix négatif, maintien), quels contrôles sont validés et où elle s'arrête. |
| `custom:marstek-goedkoop-laden-compact-card` | La même chose en quelques lignes : la chronologie, le résultat par partie avec la raison, et une ligne pour le gain. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Le gain seul : aujourd'hui, cette semaine, la semaine dernière, ce mois-ci et l'attente du plan en cours. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Compacte : boutons pour activer ou désactiver la charge, la vente, la charge à prix négatif, le maintien et sans perte. |
| `custom:marstek-goedkoop-laden-status-card` | Ce qui se passe maintenant, le niveau de charge sous forme de barre, le prix actuel et l'étape suivante. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Graphique des prix sans cartes supplémentaires : les heures de charge, de vente et de prix négatifs sont marquées, avec une ligne pour maintenant. |
| `custom:marstek-goedkoop-laden-voorraad-card` | Le stock chargé, son prix de revient, le rendement, l'amortissement par kWh et la capacité. |

```yaml
type: custom:marstek-goedkoop-laden-card
entity: sensor.marstek_goedkoop_laden_laadplan   # optional
title: Price control                             # optional
opbrengst: false                                 # optional, see below
```

La carte de gain peut être personnalisée, en YAML ou dans l'éditeur de carte :

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
tiles: [vandaag, maand, jaar]   # any of: vandaag, week, vorige_week, maand, jaar, verwacht (in this order)
expected_details: false         # hide the lines per part of the plan (default: true)
notes: false                    # hide the note below the card (default: true)
```

| Option | Par défaut | Signification |
|---|---|---|
| `tiles` | les six | Quelles tuiles afficher et dans quel ordre : aujourd'hui, cette semaine, la semaine dernière, ce mois-ci, cette année, attendu (plan). |
| `expected_details` | `true` | Les lignes avec le gain attendu par partie (charge, vente). |
| `notes` | `true` | La note avec le stock chargé, ce qui a été chargé aujourd'hui et l'amortissement. |

Options des autres cartes (toutes aussi disponibles dans l'éditeur de carte) :

| Carte | Option | Par défaut | Signification |
|---|---|---|---|
| flow, compact | `show_timeline` | `true` | Afficher la chronologie du jour. |
| flow, compact, switches | `lanes` | les cinq | Quelles parties afficher : `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| status | `show_soc`, `show_price`, `show_next` | `true` | La barre du niveau de charge, le prix actuel, l'étape suivante. |
| prices | `hours_back` | `2` | Heures passées à afficher. |
| prices | `hours_ahead` | `0` | Heures à venir à afficher ; 0 correspond au dernier prix connu. |
| prices | `show_values` | `false` | Écrire le prix au-dessus de chaque barre (jusqu'à 24 barres). |
| prices | `height` | `140` | Hauteur du graphique en pixels. |
| stock | `tiles` | les cinq | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit`. |
| stock | `notes` | `true` | La note sous la carte. |

`opbrengst` détermine si la carte de flux affiche aussi le gain : désactivé par défaut pour la
carte normale, une ligne par défaut pour la carte compacte. Dans le schéma de flux, le vert est un
contrôle validé, le rouge est le contrôle où elle s'arrête et les pointillés sont un résultat où
rien ne se passe. Toutes les cartes lisent l'attribut `stroomschema` du capteur du plan de charge.

## Gain

**Amortissement.** Si vous indiquez un prix d'achat, chaque kWh que la batterie décharge coûte un peu d'usure : prix ÷ (cycles × capacité). Il est déduit du gain réalisé (aujourd'hui, semaine, mois), compté dans le gain attendu et utilisé dans les décisions : une heure ne vaut la peine d'être chargée que si elle dépasse encore l'usure, la vente exige l'usure en plus de la marge de vente, et *Maintien* et *Sans perte* considèrent prix de revient plus usure comme le prix d'équilibre. Avec un prix de 0 (par défaut), rien ne change.

Il existe deux sortes de gain : ce que le plan en cours devrait rapporter, et ce qui a réellement
été gagné.

### Attendu (estimation à l'avance)

- **Charge** : ce que coûte l'énergie à acheter, par rapport à ce qu'elle vaudra plus tard. Cette
  valeur est le rendement multiplié par le prix moyen des heures chères auxquelles l'heure de
  charge a été comparée.
- **Vente** : le revenu du surplus, moins ce que coûte la recharge.

Pendant une charge, seul ce qui reste à charger compte.

### Aujourd'hui et cette semaine (réalisé)

1. L'énergie que l'intégration charge depuis le réseau (plan de charge ou prix négatif) devient du
   **stock** : kWh utilisables = kWh chargés × rendement, avec comme prix de revient ce que cette
   énergie a coûté à ce moment-là.
2. Si la batterie se décharge ensuite pour la consommation propre, ce stock est utilisé en premier.
   Le gain est `kWh déchargés × (prix de l'électricité à ce moment − prix de revient par kWh utilisable)`.
3. À la vente, le gain est `kWh vendus × prix de vente − prix de revient` ; pour l'énergie qui ne
   provient pas du stock (énergie solaire), le prix de revient est ce que coûte la recharge.
4. **Aujourd'hui** est la somme depuis 00:00, **cette semaine** depuis lundi 00:00 et **ce mois-ci** depuis le premier du mois. **La semaine dernière** est le montant définitif de la semaine précédente.

Ce qui reste dans le stock n'est pas encore gagné et ne compte qu'une fois utilisé. L'énergie
que le soleil met dans la batterie et que vous utilisez vous-même plus tard ne compte pas : la
Marstek le fait aussi sans cette intégration. Les montants proviennent des compteurs d'énergie de
la Marstek et du prix horaire à ce moment-là ; un saut de compteur après une panne n'est pas
comptabilisé.

### Cartes séparées

Ligne du plan (carte Markdown) :

```yaml
type: markdown
content: >-
  **Charge plan:** {{ state_attr('sensor.marstek_goedkoop_laden_laadplan', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_prijssturing', 'off') %}
  · ⚠️ price control is **off**{% endif %}
```

La carte des prix ci-dessus fait la même chose sans cartes supplémentaires. Comme alternative, un
graphique avec [apexcharts-card](https://github.com/RomRider/apexcharts-card) : les prix Zonneplan
d'aujourd'hui et de demain, vert = charge, bleu = reste de la fenêtre bon marché, gris = autre.
Répétez la série trois fois avec `'laden'`, `'venster'` et `'rest'` à la place de `KIES` :

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

## Développement

La règle de calcul vit séparément de Home Assistant dans `planner.py` et dispose de tests avec
de vrais prix. La logique de pilotage est testée contre un Home Assistant simulé
(`tests/test_sturing.py`) :

```bash
python3 -m unittest discover -s tests -v
```


## Journal des modifications

Voir [CHANGELOG.md](CHANGELOG.md), y compris les changements incompatibles.

## Licence

Apache 2.0, voir [LICENSE](LICENSE).
