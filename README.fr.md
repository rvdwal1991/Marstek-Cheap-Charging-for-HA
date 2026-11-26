<img src="custom_components/marstek_goedkoop_laden/brand/icon.png" width="96" align="right" alt="">

# Marstek Charge économique pour Home Assistant

[🇬🇧 English](README.md) · [🇳🇱 Nederlands](README.nl.md) · [🏳️ Frysk](README.fy.md) · [🇩🇪 Deutsch](README.de.md) · 🇫🇷 Français · [🇪🇸 Español](README.es.md) · [🇸🇪 Svenska](README.sv.md) · [🇳🇴 Norsk](README.nb.md)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rvdwal1991&repository=Marstek-Cheap-Charging-for-HA&category=integration)
[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_goedkoop_laden)

Recharge une batterie domestique Marstek Venus depuis le réseau pendant les heures les moins
chères d'un contrat d'électricité dynamique, afin qu'elle soit pleine avant que les prix ne montent.

Le point de départ est l'**autosuffisance** : la batterie continue de se réguler seule (anti-feed,
zéro au compteur). Cette intégration ajoute une seule chose, la charge depuis le réseau pendant les
heures les moins chères, plus quelques extras facultatifs autour.

**Il vous faut :**

- un **contrat d'électricité dynamique** avec des prix horaires. Avec un tarif fixe, il n'y a rien
  à gagner. Elle a été conçue autour du marché néerlandais et de Zonneplan (les prix du lendemain
  apparaissent entre 13:00 et 15:00), mais tout capteur avec une liste de prix horaires convient,
  voir [Capteur de prix](#capteur-de-prix) ;
- une Marstek Venus que Home Assistant peut piloter via RS485 ou Modbus, voir
  [Compatibilité](#compatibilité). **Seule l'installation LilyGO RS485 + ESPHome a été testée sur
  une vraie batterie.**
- Home Assistant 2026.3 ou plus récent.

## Ce qu'elle fait

| Mode | Par défaut | Ce qu'il fait |
|---|---|---|
| **Pilotage par les prix** | désactivé | Charge depuis le réseau pendant les heures les moins chères et étale la puissance sur ces heures. |
| **Charge à prix négatif** | activé | Charge quand le prix horaire est négatif et tire le meilleur parti de la fenêtre. |
| **Prévision solaire** | activé | Charge moins la nuit quand le soleil remplira la batterie dans la journée. Nécessite une prévision solaire dans le tableau de bord Énergie. |
| **Maintien sous le prix de revient** | activé | Ne décharge pas tant que le réseau est moins cher que le stock chargé n'a coûté. |
| **Sans perte** | désactivé | Version stricte du maintien : ne vend jamais non plus le stock chargé sous son prix de revient. |
| **Vente** | désactivé | Vend le surplus pendant les heures les plus chères. |

Chaque mode a son propre interrupteur. **Le pilotage par les prix est désactivé après l'installation** :
configurez l'intégration, vérifiez que le texte du plan sur le capteur du plan de charge est
cohérent, puis activez-le.

## Démarrage rapide

1. Installez avec HACS (bouton ci-dessus, ou ajoutez ce dépôt comme dépôt personnalisé, catégorie
   *Intégration*), ou copiez `custom_components/marstek_goedkoop_laden` dans
   `/config/custom_components/`. Redémarrez Home Assistant.
2. *Paramètres → Appareils et services → Ajouter une intégration → Marstek Goedkoop Laden*.
3. Choisissez comment votre Marstek est connectée, puis le capteur de prix et les entités de la
   Marstek. Ce qui est détecté est prérempli. Pour Modbus, vous indiquez aussi le nom de votre
   hub Modbus (par exemple `MarstekVenus`) et l'adresse esclave.
4. Activez l'interrupteur **Pilotage par les prix** quand le plan est cohérent.
5. Ajoutez des cartes : *Modifier le tableau de bord → Ajouter une carte → cherchez « Marstek »*, voir
   [Cartes du tableau de bord](#cartes-du-tableau-de-bord).

Les textes (ligne du plan, schéma de flux, cartes) suivent l'option *Langue* : Automatique, Nederlands,
English, Frysk, Deutsch, Français, Español, Svenska ou Norsk. Automatique suit Home Assistant
quand c'en est une, sinon l'anglais.

## Fonctionnement du plan de charge

1. **La charge vaut-elle le coup ?** Une heure est assez bon marché si son prix est inférieur à
   `rendement × (moyenne des 6 heures les plus chères des 18 prochaines heures) − marge`. Le
   rendement (aller-retour charge et décharge, environ 77 % mesuré ici) provient des compteurs
   d'énergie de la Marstek.
2. **Fenêtre.** Le premier bloc d'heures bon marché est la fenêtre de charge. Une ou deux heures
   à peine trop chères ne brisent pas le bloc ; la charge n'a lieu que pendant les heures
   bon marché elles-mêmes.
3. **Heures de charge.** Dans cette fenêtre, elle choisit les heures les moins chères, juste
   assez pour passer du SoC actuel à 100 %. Si la fenêtre est trop courte pour remplir la
   batterie, elle ne planifie que ce qui tient et le signale dans le texte du plan.
4. **Étaler la puissance.** La puissance de charge est l'énergie restant à ajouter divisée par le
   temps restant dans les heures de charge. Cela ménage le raccordement au réseau. La puissance
   est ajustée en cours de route.
5. **Terminé, c'est terminé.** Quand les heures de charge sont écoulées ou que la batterie est
   pleine, la Marstek repasse en anti-feed. Elle ne redémarre pas dans la même fenêtre.

Seuls les prix **publiés** sont utilisés ; le plan de la nuit apparaît donc dès que les prix de
demain sont connus. Exemple (10 novembre 2026, batterie à 12 %) : fenêtre bon marché 23:00–07:00,
charge à 02:00, 03:00 et 04:00 à environ 1900 W pour une moyenne de € 0,37, contre € 0,55–0,67
en journée.

### Charge à prix négatif

Si le prix horaire est négatif, la batterie charge, indépendamment du plan de charge et même
quand le pilotage par les prix est désactivé. Elle examine toute la **fenêtre** d'heures négatives
consécutives :

1. Elle calcule ce que la batterie peut encore absorber (du SoC à 100 %).
2. Elle répartit cette énergie sur les heures **selon leur valeur** : plus le prix est négatif,
   plus on charge pendant cette heure, dans la limite de ce qu'une heure peut absorber à la
   puissance maximale. Exemple : −€ 0,03, −€ 0,20 et −€ 0,12 avec 3 kWh à charger donnent
   environ 1,9 kWh dans l'heure à −€ 0,20 et 1,2 kWh dans l'heure à −€ 0,12. L'heure à −€ 0,03
   resterait sous la puissance de charge minimale ; elle est donc écartée et sa part revient aux
   deux autres.
3. L'étalement maintient la puissance plus bas qu'une courte pointe à pleine puissance. Une heure
   isolée qui ne peut pas remplir la batterie est chargée à pleine puissance.

L'option *Prix négatif : répartition de l'énergie* peut être réglée sur **Gain maximal** : la
meilleure heure est remplie d'abord à pleine puissance, puis la suivante. Dans l'exemple, cela
rapporte environ € 0,55 au lieu de € 0,52, au prix de davantage de pointes à pleine puissance.
Le plan est recalculé chaque minute, et une heure déjà en cours obtient un peu de marge
supplémentaire avant d'être écartée.

### Prévision solaire

Avec des panneaux solaires, la batterie se remplit gratuitement dans la journée. Si vous la
chargez à fond depuis le réseau la nuit, le surplus n'a plus de place et part vers le réseau pour
presque rien, ce qui compte davantage maintenant que la compensation (*salderingsregeling*) touche
à sa fin. L'intégration tient donc compte de la production solaire attendue :

1. Elle lit la prévision dans le **tableau de bord Énergie** (*Paramètres → Tableaux de bord →
   Énergie → Panneaux solaires → Prévision de production solaire*). Forecast.Solar, Solcast,
   Open-Meteo et d'autres intégrations de prévision fonctionnent, sans rien de plus à configurer.
   Sans prévision à cet endroit, rien ne change.
2. Elle calcule le surplus attendu : par heure, la prévision multipliée par la fiabilité, moins
   votre propre consommation pendant cette heure. Les prévisions sont souvent trop optimistes,
   surtout en hiver. Avec *Apprendre la fiabilité à partir de la production réelle* activé,
   l'intégration compare la prévision de chaque jour à ce que les panneaux ont réellement produit
   (le compteur de production du tableau de bord Énergie) et utilise la médiane des derniers jours
   comme fiabilité, dès qu'elle dispose d'au moins 3 jours. D'ici là, et quand l'apprentissage est
   désactivé, le réglage *Fiabilité de la prévision solaire* (par défaut 70 %) s'applique. Pour la
   consommation propre pendant cette heure : avec un *Capteur de puissance de la maison*,
   l'intégration apprend votre consommation moyenne par heure de la journée (jours de semaine et
   week-ends séparément) et l'utilise, de sorte qu'un midi que la maison consomme elle-même ne
   laisse aucun surplus. Sans le capteur, la *Vente : consommation propre moyenne* fixe est utilisée.
3. Elle ne charge la nuit que ce qu'il faut pour qu'il reste de la place pour ce surplus au lever
   du soleil : ce que votre propre consommation aura utilisé d'ici là, plus ce qui est encore
   nécessaire. Par une journée ensoleillée, cela peut représenter quelques kWh au lieu d'une
   batterie pleine, voire rien (le texte du plan indique alors que le soleil remplira la
   batterie). Une journée nuageuse donne peu ou pas de surplus, et la batterie est chargée à fond.

La prévision est lue toutes les 30 minutes. Elle ne fait que réduire la quantité à charger ; elle
ne déplace pas les heures de charge et ne change rien à la vente.

### Maintien et sans perte

L'énergie chargée depuis le réseau a un prix de revient : le prix de charge divisé par le
rendement. Si la batterie restituait cette énergie pendant des heures moins chères que cela, la
charge coûterait de l'argent. Le **maintien** bloque donc la décharge tant qu'il y a du stock
chargé dans la batterie (voir [Gain](#gain)) et que le prix horaire est inférieur au prix de
revient de ce stock. La maison utilise alors le courant du réseau, qui est à ce moment-là moins
cher. Dès que le prix atteint le prix de revient, ou que le stock est épuisé, la Marstek reprend
la main.

Techniquement, l'intégration met la puissance de décharge maximale à 0. La Marstek reste en
anti-feed, donc la charge par le surplus solaire se poursuit. Si une autre automatisation règle
cette puissance pendant le maintien (par exemple un limiteur pour une borne de recharge de
véhicule électrique), l'intégration mémorise cette valeur et la rétablit ensuite. La Marstek ne
distingue pas l'énergie du réseau de l'énergie solaire ; pendant un maintien, toute la batterie
reste donc sans décharge. Le maintien nécessite l'entité de la puissance de décharge maximale.

**Sans perte** est un interrupteur distinct, plus strict : le maintien est imposé même si
l'interrupteur Maintien est désactivé, et rien n'est vendu sous le prix de revient. Chaque kWh
comptabilisé rapporte alors au moins son prix de revient. Ce qu'il ne peut pas exclure :

- **L'immobilisation :** si le prix reste longtemps sous le prix de revient, la batterie reste
  bloquée, y compris pour l'énergie solaire stockée.
- **Un rendement différent :** si la batterie restitue moins que le rendement moyen, elle est vide
  avant que le stock comptabilisé soit utilisé ; le reste expire sans enregistrer de perte.
- **L'usure** n'est pas comptée, sauf si vous indiquez un prix d'achat (voir [Gain](#gain)).

### Vente

La vente a son propre interrupteur et est indépendante de la charge. Seul ce qui reste vraiment en
surplus est vendu. Une heure est retenue pour la vente quand tout ceci est vrai :

1. **Une charge bon marché approche** : une fenêtre de charge aux prix publiés se profile, de
   sorte que le coût de la recharge est connu.
2. **Le revenu est nettement supérieur à celui de la recharge** : prix de vente ≥ prix de charge
   divisé par le rendement, plus la marge de vente (par défaut € 0,10 par kWh).
3. **Il y a un surplus au-dessus de la réserve** : le seuil de décharge de la Marstek plus la
   consommation propre attendue jusqu'à la recharge, avec un minimum réglable (par défaut 20 %).
4. **C'est l'une des heures les plus chères** avant la fenêtre de charge.

La puissance de vente est étalée sur les heures choisies ; à la réserve, la vente s'arrête. En
hiver, il y a rarement un surplus ; l'option sert surtout quand le soleil remplit la batterie et
qu'il y a un pic de prix en soirée. Elle nécessite l'entité de la puissance de décharge forcée.

**Après la fin de la compensation** (la *salderingsregeling* néerlandaise, 1er janvier 2027),
l'injection rapporte moins que le prix horaire. Réglez alors *Prix de vente : facteur* et
*déduction* : prix de vente = prix horaire × facteur − déduction. Pour le prix de marché brut chez
Zonneplan, cela donne environ 0,826 et € 0,108.

## Compatibilité

L'intégration pilote une Marstek Venus via ses registres de commande RS485.

| Connexion | Modèle | État |
|---|---|---|
| LilyGO T-CAN485 + ESPHome (RS485) | Venus E v2 | **Testé** sur du vrai matériel (l'installation sur laquelle elle a été conçue) |
| Hub Modbus dans Home Assistant, via un convertisseur RS485 vers TCP (Elfin EW11 et similaires) | Venus E v1/v2 | Testé uniquement avec des appels simulés |
| Hub Modbus dans Home Assistant, directement en Ethernet | Venus E v3 | Testé uniquement avec des appels simulés |
| Intégration *Marstek Venus Modbus* (ViperRNMC) | Venus E v3 | Testé uniquement avec des appels simulés |
| N'importe laquelle des précédentes | Venus A, Venus D, autres modèles | **Non vérifié, non testé.** Elles partageraient les registres de commande, mais ce n'est pas confirmé. Réglez la capacité de la batterie dans les options (par défaut 5,12 kWh). |
| Cloud, appli ou autres intégrations | toutes | Non pris en charge |

- **LilyGO T-CAN485 sous ESPHome** via RS485, avec la configuration
  [MarstekVenus-LilygoRS485](https://github.com/Superduper1969/MarstekVenus-LilygoRS485).
  Elle utilise les entités que cette installation expose : *RS485 Control Mode*, *Forcible
  Charge/Discharge*, *Forcible Charge Power* (obligatoire) et, en option, *Max. Charge Power*,
  *Max. Discharge Power*, *Forcible Discharge Power*, *Discharging Cutoff Capacity* ainsi que les
  compteurs d'énergie totale chargée/déchargée.
- **Modbus dans Home Assistant**, avec un hub Modbus que vous définissez vous-même dans
  `configuration.yaml` : un Elfin EW11 ou un autre convertisseur RS485 vers TCP
  ([MarstekVenus-ElfinEW11](https://github.com/Superduper1969/MarstekVenus-ElfinEW11)), ou la
  **Venus E v3 directement en Ethernet** (Modbus TCP, port 502, unité 1, EMS V144 ou plus récent ;
  [MarstekVenusV3-modbus-TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP)).
  L'intégration lit les capteurs de registres de cette installation et écrit les registres 42000
  (contrôle RS485), 42010 (mode de forçage), 42020/42021 (puissance de charge/décharge forcée) et,
  si vous indiquez les capteurs, 44002/44003 (puissance de charge/décharge maximale) avec
  `modbus.write_register`. Sans la puissance de décharge maximale, *Maintien* et *Sans perte* ne
  sont pas disponibles. La Venus E v3 conserve son état de charge dans le registre 34002
  (échelle 0,1), et non dans le 32104.
- **L'intégration *Marstek Venus Modbus***
  ([ViperRNMC/marstek_venus_modbus](https://github.com/ViperRNMC/marstek_venus_modbus)), qui
  parle aussi Modbus TCP. Choisissez-la si vous l'utilisez déjà : elle fournit les entités
  (`switch` mode de contrôle RS485, `select` mode de forçage, `number` puissances). Activez-y
  d'abord l'interrupteur *RS485 control mode* et le select *Force mode*, ils sont désactivés par
  défaut.

### Ce que l'intégration envoie à la Marstek

| Moment | Commandes |
|---|---|
| Début de la charge | régler la puissance de charge → mode de forçage `charge` → contrôle RS485 `enable` |
| Pendant la charge | ajuster la puissance de charge (par pas de 100 W) |
| Terminé, ou pilotage par les prix désactivé | contrôle RS485 `disable`, mode de forçage de nouveau sur `charge`, puissance de charge de nouveau au maximum |
| Début de la vente | régler la puissance de décharge → mode de forçage `discharge` → contrôle RS485 `enable` |
| Vente terminée, ou vente désactivée | comme pour « terminé » : retour à l'état de repos |

La **dé**charge forcée que vous lancez vous-même est laissée en l'état. La charge forcée que vous
lancez vous-même est réinitialisée tant que le pilotage par les prix est activé ; désactivez-le
d'abord si vous le souhaitez.

## Réglages

Sous *Configurer* dans l'intégration. Les options sont regroupées ; les entités se trouvent dans
un groupe replié en bas.

### Capteur de prix

L'intégration lit les prix dans un attribut d'un capteur (par défaut `forecast`) :

- Prix horaires Zonneplan : `start_date`, `end_date`, `price_tax_included.amount`
- Zonneplan (ancien) : `datetime`, `electricity_price`
- Générique : `start` (ou `start_time`, `datetime`) et `price` (ou `value`, `prijs`) en €/kWh

### Options

| Groupe | Réglage | Par défaut | Signification |
|---|---|---|---|
| | Langue | Automatique | Langue du texte du plan, du schéma de flux et des cartes. |
| Batterie | Capacité de la batterie | 5,12 kWh | Utilisée uniquement si aucun capteur de capacité n'est défini. |
| Batterie | Rendement en l'absence de compteurs | 0,77 | Le rendement est calculé à partir des compteurs d'énergie de la Marstek (total déchargé ÷ total chargé, borné à 70–95 %). Cette valeur fixe ne s'applique que si ces compteurs sont absents. Le rendement à sens unique en est la racine carrée. |
| Batterie | Prix d'achat de la batterie | € 0 | Sert à l'amortissement. 0 le désactive. |
| Batterie | Durée de vie de la batterie (cycles) | 6000 | Amortissement par kWh = prix ÷ (cycles × capacité) ; € 1 500 sur 6 000 cycles de 5,12 kWh font environ € 0,049 par kWh. |
| Batterie | Seuil de décharge | 12 % | Utilisé si aucune entité de seuil n'est définie. |
| Charge | Gain minimal par kWh | € 0,02 | Ce que la charge doit rapporter au minimum, après les pertes de charge. Les heures qui dépassent la limite de moins d'un demi-centime comptent quand même, afin qu'une nuit presque plate ne soit pas découpée pour une fraction de centime. |
| Charge | Puissance de charge minimale | 400 W | Limite basse lors de l'étalement. |
| Charge | Attribut contenant les prix | `forecast` | L'attribut du capteur de prix qui contient les prix horaires. |
| Charge | Nombre d'heures les plus chères à comparer | 6 | Avec combien d'heures chères ultérieures une heure est comparée. |
| Charge | Heures à anticiper | 18 | Jusqu'où regarder après une heure pour trouver les heures chères. |
| Charge | Minimum d'heures connues à l'avance | 8 | Les heures suivies de moins de prix connus que cela sont ignorées. |
| Prix négatif | Prix négatif : limite | € 0,00 | Sous ce prix horaire, la batterie charge. |
| Prix négatif | Prix négatif : répartition de l'énergie | Selon la valeur | Selon la valeur (puissance plus faible) ou gain maximal (meilleures heures d'abord). |
| Solaire | Utiliser la prévision solaire | Activé | Tient compte de la production solaire attendue du tableau de bord Énergie lors de la charge de nuit. |
| Solaire | Apprendre la fiabilité à partir de la production réelle | Activé | Compare la prévision solaire de chaque jour à ce que les panneaux ont réellement produit et utilise la médiane des derniers jours comme fiabilité (à partir de 3 jours). |
| Solaire | Fiabilité de la prévision solaire | 70 % | La part de la prévision sur laquelle compter. Plus bas = plus prudent. |
| Solaire | Capteur de puissance de la maison | aucun | Capteur facultatif de la puissance utilisée par toute la maison (W ou kW), sans la batterie. Une borne de recharge de véhicule fausse la moyenne, laissez-la donc de côté si possible. |
| Vente | Vente : gain minimal par kWh | € 0,10 | Ce que la vente doit rapporter au minimum après la recharge. |
| Vente | Vente : consommation propre moyenne | 400 W | Détermine la réserve jusqu'à la recharge, et sert de consommation propre fixe pour le surplus solaire. |
| Vente | Vente : réserve minimale | 20 % | Rien n'est vendu sous ce SoC. |
| Vente | Prix de vente : facteur et déduction | 1 et € 0 | Prix de vente = prix horaire × facteur − déduction. |

La puissance de charge maximale (la *Max. Charge power* de la Marstek) détermine le nombre
d'heures de charge. Réglez-la plus bas et elle planifie plus d'heures et charge plus doucement.

## Cartes du tableau de bord

L'intégration fournit sept cartes ; aucune ressource n'est à ajouter. Actualisez le navigateur
après l'installation ou une mise à jour. Chaque carte peut être configurée dans l'éditeur de
carte comme en YAML, et si vous omettez `entity`, le capteur du plan de charge est trouvé
automatiquement.

| Carte | Contenu |
|---|---|
| `custom:marstek-goedkoop-laden-card` | Schéma de flux : la chronologie du jour et, par partie (charge, vente, prix négatif, maintien), quels contrôles sont validés et où elle s'arrête. |
| `custom:marstek-goedkoop-laden-compact-card` | La même chose en quelques lignes : la chronologie, le résultat par partie avec la raison, et une ligne pour le gain. |
| `custom:marstek-goedkoop-laden-opbrengst-card` | Le gain seul : aujourd'hui, cette semaine, la semaine dernière, ce mois-ci, cette année et l'attente du plan en cours. |
| `custom:marstek-goedkoop-laden-schakelaars-card` | Compacte : boutons pour activer ou désactiver les modes. |
| `custom:marstek-goedkoop-laden-status-card` | Ce qui se passe maintenant, le niveau de charge sous forme de barre, le prix actuel et l'étape suivante. |
| `custom:marstek-goedkoop-laden-prijzen-card` | Graphique des prix sans cartes supplémentaires : les heures de charge, de vente et de prix négatifs sont marquées, avec une ligne pour maintenant. |
| `custom:marstek-goedkoop-laden-voorraad-card` | Le stock chargé, son prix de revient, le rendement, l'amortissement par kWh et la capacité. |

```yaml
type: custom:marstek-goedkoop-laden-opbrengst-card
entity: sensor.marstek_goedkoop_laden_plan_de_charge   # facultatif
title: Gain                                            # facultatif
tiles: [vandaag, maand, jaar]                          # quelles tuiles, dans cet ordre
notes: false                                           # masquer la note sous la carte
```

| Carte | Option | Par défaut | Signification |
|---|---|---|---|
| toutes | `entity`, `title` | trouvé automatiquement, aucun | Le capteur du plan de charge et un titre. |
| flow, compact | `show_timeline` | `true` | Afficher la chronologie du jour. |
| flow, compact | `opbrengst` | désactivé, une ligne | Afficher aussi le gain. |
| flow, compact, switches | `lanes` | les cinq | Quelles parties afficher : `bijladen`, `verkoop`, `negatief`, `vasthouden`, `geen_verlies`. |
| gain | `tiles` | les six | Parmi `vandaag`, `week`, `vorige_week`, `maand`, `jaar`, `verwacht`, dans cet ordre. |
| gain | `expected_details`, `notes` | `true` | Les lignes par partie du plan ; la note avec le stock, la charge du jour et l'amortissement. |
| status | `show_soc`, `show_price`, `show_next` | `true` | La barre du niveau de charge, le prix actuel, l'étape suivante. |
| prices | `hours_back`, `hours_ahead` | `2`, `0` | Heures passées ; heures à venir (0 correspond au dernier prix connu). |
| prices | `show_values`, `height` | `false`, `140` | Écrire le prix au-dessus de chaque barre (jusqu'à 24 barres) ; hauteur en pixels. |
| stock | `tiles`, `notes` | les cinq, `true` | `voorraad`, `kostprijs`, `rendement`, `afschrijving`, `capaciteit` ; la note sous la carte. |

Dans le schéma de flux, le vert est un contrôle validé, le rouge est le contrôle où elle s'arrête
et les pointillés sont un résultat où rien ne se passe. Ligne du plan dans une carte Markdown :

```yaml
type: markdown
content: >-
  **Plan de charge :** {{ state_attr('sensor.marstek_goedkoop_laden_plan_de_charge', 'tekst') }}
  {% if is_state('switch.marstek_goedkoop_laden_pilotage_par_les_prix', 'off') %}
  · ⚠️ le pilotage par les prix est **désactivé**{% endif %}
```

## Gain

Il existe deux sortes de gain : ce que le plan en cours devrait rapporter, et ce qui a réellement
été gagné.

**Attendu (estimation à l'avance).** Charge : ce que coûte l'énergie à acheter, par rapport à ce
qu'elle vaudra plus tard (le rendement multiplié par le prix moyen des heures chères auxquelles
l'heure de charge a été comparée). Vente : le revenu du surplus, moins ce que coûte la recharge.
Pendant une charge, seul ce qui reste à charger compte.

**Réalisé (aujourd'hui, semaine, mois, année).**

1. L'énergie que l'intégration charge depuis le réseau (plan de charge ou prix négatif) devient du
   **stock** : kWh utilisables = kWh chargés × rendement, avec comme prix de revient ce que cette
   énergie a coûté à ce moment-là.
2. Si la batterie se décharge ensuite pour la consommation propre, ce stock est utilisé en premier.
   Le gain est `kWh déchargés × (prix de l'électricité à ce moment − prix de revient par kWh utilisable)`.
3. À la vente, le gain est `kWh vendus × prix de vente − prix de revient` ; pour l'énergie qui ne
   provient pas du stock (énergie solaire), le prix de revient est ce que coûte la recharge.
4. **Aujourd'hui** compte depuis 00:00, **cette semaine** depuis lundi 00:00, **ce mois-ci** depuis
   le premier du mois et **cette année** depuis le 1er janvier. **La semaine dernière** est le
   montant définitif de la semaine précédente.

Ce qui reste dans le stock n'est pas encore gagné et ne compte qu'une fois utilisé. L'énergie que
le soleil met dans la batterie et que vous utilisez vous-même plus tard ne compte pas : la Marstek
le fait aussi sans cette intégration. Les montants proviennent des compteurs d'énergie de la
Marstek et du prix horaire à ce moment-là ; un saut de compteur après une panne n'est pas
comptabilisé.

**Amortissement.** Si vous indiquez un prix d'achat, chaque kWh que la batterie décharge coûte un
peu d'usure : prix ÷ (cycles × capacité). Il est déduit du gain réalisé, compté dans le gain
attendu et utilisé dans les décisions : une heure ne vaut la peine d'être chargée que si elle
dépasse encore l'usure, la vente exige l'usure en plus de la marge de vente, et *Maintien* et
*Sans perte* considèrent prix de revient plus usure comme le prix d'équilibre. Avec un prix de 0
(par défaut), rien ne change.

## Entités

| Entité | Contenu |
|---|---|
| `switch.*_pilotage_par_les_prix` | Activé : le plan de charge est exécuté. Désactivé : la Marstek régule tout elle-même. |
| `switch.*_charge_a_prix_negatif` | Activé (par défaut) : charger quand le prix horaire est négatif. |
| `switch.*_maintien_sous_le_prix_de_revient` | Activé (par défaut) : ne pas décharger sous le prix de revient du stock. |
| `switch.*_sans_perte` | Activé : maintien imposé et jamais de vente sous le prix de revient. |
| `switch.*_vente` | Activé : le surplus est vendu pendant les heures les plus chères. Indépendant du pilotage par les prix. |
| `sensor.*_plan_de_charge` | État : `laden`, `gepland`, `klaar`, `vol`, `geen` ou `onbekend`. Attributs : `tekst` (résumé lisible), `laaduren`, `venster`, `stroomschema` (chronologie, contrôles, prix et vue d'ensemble pour les cartes) et d'autres. |
| `sensor.*_plan_de_vente` | État : `verkopen`, `gepland`, `geen` ou `onbekend`. Attributs : `verkoopuren`, `overschot_kwh`, `reserve_soc`, `tekst` et d'autres. |
| `sensor.*_puissance_de_charge_prevue`, `*_energie_a_charger`, `*_debut_de_charge`, `*_fin_de_charge`, `*_prix_de_charge_moyen` | La puissance de charge étalée en W, l'énergie restant à charger en kWh, le début et la fin de la charge planifiée, et son prix moyen en €/kWh. |
| `sensor.*_gain_aujourd_hui`, `*_gain_cette_semaine`, `*_gain_la_semaine_derniere`, `*_gain_ce_mois_ci`, `*_gain_cette_annee` | Gain réalisé en euros (voir [Gain](#gain)). |
| `sensor.*_gain_attendu` | Gain estimé des plans en cours en euros ; l'attribut `regels` contient le détail. |
| `sensor.*_rendement` | Le rendement utilisé, en pourcentage. Attribut `bron` : mesuré ou fixe. |

Les noms d'entités suivent la langue de Home Assistant au moment de la création de l'entité (en
néerlandais, elles s'appellent `*_laadplan`, `*_prijssturing`, etc.). **Les valeurs d'état et les
noms d'attributs sont en néerlandais dans toutes les langues** (`laden`, `tekst`, …) ; ils sont
figés pour que les automatisations continuent de fonctionner.

## Développement

La règle de calcul vit séparément de Home Assistant dans `planner.py` et dispose de tests avec
de vrais prix. La logique de pilotage est testée contre un Home Assistant simulé :

```bash
python3 -m unittest discover -s tests -v
```

## Journal des modifications

Voir [CHANGELOG.md](CHANGELOG.md), y compris les changements incompatibles.

## Remerciements

Cette intégration s'appuie sur le travail de la communauté Marstek Venus :

- Le [fil du forum Tweakers](https://gathering.tweakers.net/forum/list_messages/2282240/0) où ce travail communautaire est discuté, avec une mention d'honneur pour tous ceux qui y partagent leurs découvertes et leurs configurations.
- [Superduper1969](https://github.com/Superduper1969) pour les configurations LilyGO RS485 et Elfin EW11 autour desquelles cette intégration est construite, et scruysberghs, remercié dans ces configurations.
- [fonske](https://github.com/fonske) pour la configuration Modbus TCP de la Venus E v3.
- [ViperRNMC](https://github.com/ViperRNMC) pour l'intégration Marstek Venus Modbus.

## Licence

Apache 2.0, voir [LICENSE](LICENSE).
