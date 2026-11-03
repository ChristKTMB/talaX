# Tala X

> *Regardez au-delà du pixel*

[English](https://github.com/ChristKTMB/talaX/blob/main/README.md)

Tala X dit ce qu'on peut honnêtement affirmer d'une image : si c'est un
fichier original d'appareil ou une copie retraitée par une plateforme, où et
quand elle a été prise, et si elle est passée par un logiciel de retouche. La
vidéo (métadonnées de conteneur) est prévue.

> **État : pré-alpha (0.3).** Utilisable, mais les règles et la sortie peuvent encore changer.

## La question posée en premier

Pas *« cette image est-elle fausse ? »* — aucune technologie n'y répond de
façon fiable aujourd'hui. Mais :

> **Ce fichier est-il un original d'appareil, ou une copie retraitée par une
> plateforme ?**

Toutes les grandes plateformes (Instagram, X, TikTok, WhatsApp…) effacent les
métadonnées EXIF, IPTC et C2PA à l'upload. Tala X le détecte, identifie la
plateforme quand il le peut, et invite à demander l'original à la source — en
expliquant comment l'envoyer sans l'abîmer.

## Comment il rend ses résultats

Chaque signal rend un état parmi quatre, **toujours accompagné d'une
explication en langage clair** :

| État | Signification |
| --- | --- |
| Cohérent | Évalué, aucune contradiction |
| À vérifier | Anomalie pouvant avoir une explication légitime |
| Suspect | Contradiction difficile à expliquer autrement |
| Non vérifiable | L'information nécessaire est absente |

Tala X ne dit jamais « cette image est fausse » et ne certifie jamais qu'une
image est authentique. Un original d'appareil n'est pas une preuve de vérité :
les métadonnées se falsifient. Tala X est conçu contre le blanchiment par les
plateformes et les images recyclées, pas contre les faussaires experts.

## Ce qu'il vérifie

- Intégrité du fichier : original d'appareil, copie de plateforme ou
  indéterminé. Empreintes mesurées à ce jour : WhatsApp (galerie) et
  retouches de la Galerie Samsung ; d'autres seront mesurées.
- Format réel du fichier par rapport à son extension
- **Cohérence solaire** : l'heure enregistrée est-elle physiquement possible
  au lieu enregistré, compte tenu de ce que vous voyez sur la photo ?
- Fuseau horaire enregistré par l'appareil par rapport au fuseau légal de la
  position GPS
- Position GPS, date et heure, logiciel de retouche
- Certificats C2PA (Content Credentials), vérifiés hors ligne avec la
  [liste de confiance C2PA](https://github.com/c2pa-org/conformance-public/tree/main/trust-list)
  officielle
- La miniature intégrée, affichée à côté de l'image dans le rapport HTML
  comme exploration visuelle, explicitement non concluante

À venir : un mode manuel pour les fichiers dépouillés (saisie du lieu et de
la date annoncés), un recoupement météo, et un renvoi vers la recherche
d'image inversée (Google Lens, TinEye, Yandex), qui attrape les vieilles
photos recyclées avec une fausse légende — la forme la plus répandue de
désinformation visuelle.

## Ce qu'il refuse de faire

- **Aucune détection d'IA par analyse de pixels.** Des mesures indépendantes
  montrent que ces détecteurs tombent au niveau du hasard après le
  redimensionnement et la compression qu'applique chaque plateforme, avec
  jusqu'à un tiers de faux positifs sur de vraies photos de presse.
- Pas d'Error Level Analysis utilisée comme verdict.
- Pas de géolocalisation visuelle automatique.
- Vidéo : métadonnées de conteneur uniquement.

## Installer

**1. Installer Tala X** (Python 3.12 ou plus récent) :

```bash
pipx install talax        # ou : uv tool install talax    ou : pip install talax
```

**2. Installer ExifTool 13.0 ou plus récent.** Tala X refuse de tourner avec
une version plus ancienne, qui manquerait des tags constructeur et donnerait
d'autres résultats.

- **macOS** : `brew install exiftool`
- **Windows** : téléchargez l'exécutable Windows sur
  [exiftool.org](https://exiftool.org/), décompressez-le, renommez
  `exiftool(-k).exe` en `exiftool.exe`, gardez le dossier `exiftool_files` à
  côté, et ajoutez ce dossier à votre `PATH`.
- **Linux** : les paquets des distributions sont souvent trop anciens (Ubuntu
  24.04 fournit la 12.76). Installez la dernière version dans votre dossier
  personnel :

  ```bash
  v=$(curl -fsS https://exiftool.org/ver.txt)
  mkdir -p ~/.local/opt ~/.local/bin
  curl -fsSL "https://sourceforge.net/projects/exiftool/files/Image-ExifTool-$v.tar.gz/download" | tar -xz -C ~/.local/opt
  ln -sf ~/.local/opt/Image-ExifTool-$v/exiftool ~/.local/bin/exiftool
  ```

Vérifiez avec `exiftool -ver`. Testé sous Linux, macOS et Windows.

## L'utiliser en ligne de commande

```bash
talax analyze photo.jpg                       # rapport dans le terminal
talax analyze photo.jpg --sky day             # ce que montre la photo, pour la cohérence solaire
talax analyze photo.jpg --html rapport.html   # rapport HTML autonome
talax analyze photo.jpg --json                # format machine
talax analyze photo.jpg --lang en             # en anglais (par défaut : la langue du système)
```

Les rapports existent en français et en anglais.

Rien n'est jamais envoyé sur le réseau. Le rapport HTML est un fichier unique :
l'ouvrir ne charge rien depuis le réseau non plus.

## L'utiliser comme bibliothèque Python

```python
from pathlib import Path

from talax import Observation, Sky, analyze
from talax.i18n import Language

analysis = analyze(Path("photo.jpg"), observation=Observation(Sky.DAY))
print(analysis.integrity.verdict, analysis.integrity.explain(Language.FR))
for result in analysis.results:
    print(result.signal_id, result.state, result.explain(Language.FR))
```

Chaque résultat porte un état, un message (`result.message.key`, identique
dans les deux langues), son explication en français ou en anglais, et les
valeurs brutes qui y ont mené (`result.evidence`). La sortie JSON de la ligne
de commande suit un schéma versionné (`"schema": 2`).

## Héberger l'API web soi-même

La même analyse derrière une API HTTP, pour votre propre serveur :

```bash
pip install "talax[server]"
talax serve                    # http://127.0.0.1:8000
```

Les fichiers envoyés sont analysés dans un dossier temporaire puis supprimés
aussitôt ; le serveur ne garde rien et ne journalise ni nom de fichier, ni
position, ni adresse du client. Le dépôt contient aussi une configuration
`docker compose` prête à l'emploi (API derrière nginx, conteneurs en lecture
seule, fichiers en mémoire seulement). Voir la
[documentation de l'API](https://github.com/ChristKTMB/talaX/blob/main/docs/api.md) (en anglais).

## Développer

```bash
git clone https://github.com/ChristKTMB/talaX.git
cd talaX
uv sync --all-extras
uv run pytest
uv run ruff check && uv run ruff format --check && uv run mypy
```

Les tests qui ont besoin du corpus de référence sont sautés quand
`corpus/files/` est absent : ces fichiers ne sont pas publiés (voir le
[protocole du corpus](https://github.com/ChristKTMB/talaX/blob/main/corpus/README.md)).

## Les trois façons de l'utiliser

- **Bibliothèque Python** — `pip install talax`, à intégrer dans votre
  plateforme
- **CLI** — tourne sur votre machine, votre fichier ne la quitte pas.
  Recommandée pour les fichiers sensibles.
- **Application web** (à venir) — hébergée, pour les vérifications rapides. Les
  fichiers seront analysés puis supprimés immédiatement, jamais conservés.

Nécessite [ExifTool](https://exiftool.org/).

## Contribuer

Le projet est ouvert aux contributions. La plus précieuse sera les
**empreintes de plateformes** : les caractéristiques mesurées de la façon dont
une plateforme et une version d'app retraitent les fichiers. Un guide de
contribution arrivera avec le premier code.

## Licence

[Apache-2.0](https://github.com/ChristKTMB/talaX/blob/main/LICENSE)

Le paquet embarque la [liste de confiance C2PA](https://github.com/c2pa-org/conformance-public/tree/main/trust-list)
du programme de conformité de la C2PA (© C2PA, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)),
utilisée sans modification pour reconnaître les signataires des Content
Credentials. Sa date et son origine sont dans `src/talax/data/c2pa/source.yaml`.
