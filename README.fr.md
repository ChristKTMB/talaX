# Tala X

> *Regardez au-delà du pixel*

[English](README.md)

Tala X dit ce qu'on peut honnêtement affirmer d'une image ou d'une vidéo : si
c'est un fichier original d'appareil ou une copie retraitée par une
plateforme, où et quand elle a été prise, et si elle est passée par un
logiciel de retouche.

> **État : développement en cours.** Aucune version utilisable pour l'instant.

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

- Intégrité du fichier et plateforme traversée (WhatsApp, Instagram, X…)
- Format réel du fichier par rapport à son extension
- **Cohérence solaire** : l'heure enregistrée est-elle physiquement possible
  au lieu enregistré ?
- Recoupement météo avec les relevés historiques
- Position GPS, date et heure, logiciel de retouche, miniature intégrée
- Certificats de provenance C2PA

Il renvoie aussi vers la recherche d'image inversée (Google Lens, TinEye,
Yandex), qui attrape les vieilles photos recyclées avec une fausse légende —
la forme la plus répandue de désinformation visuelle.

## Ce qu'il refuse de faire

- **Aucune détection d'IA par analyse de pixels.** Des mesures indépendantes
  montrent que ces détecteurs tombent au niveau du hasard après le
  redimensionnement et la compression qu'applique chaque plateforme, avec
  jusqu'à un tiers de faux positifs sur de vraies photos de presse.
- Pas d'Error Level Analysis utilisée comme verdict.
- Pas de géolocalisation visuelle automatique.
- Vidéo : métadonnées de conteneur uniquement.

## Installer et essayer (version de développement)

Testé sous Linux (Ubuntu dans WSL). Windows et macOS devraient fonctionner mais
n'ont pas encore été testés : signalez tout problème.

**1. Installer uv** (il installe aussi la bonne version de Python) :

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```
```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. Installer ExifTool 13.0 ou plus récent** — Tala X refuse de tourner avec
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

Vérifiez avec `exiftool -ver`.

**3. Récupérer Tala X et analyser une photo :**

```bash
git clone https://github.com/ChristKTMB/talaX.git
cd talaX
uv sync
uv run talax analyze photo.jpg                       # rapport dans le terminal
uv run talax analyze photo.jpg --sky day             # ce que montre la photo, pour la cohérence solaire
uv run talax analyze photo.jpg --html rapport.html   # rapport HTML autonome
uv run talax analyze photo.jpg --json                # format machine
```

Le rapport HTML est un fichier unique : l'ouvrir ne charge rien depuis le
réseau. La ligne de commande n'envoie jamais rien nulle part.

**4. Lancer les tests** (contributeurs) :

```bash
uv run pytest
uv run ruff check && uv run ruff format --check && uv run mypy
```

Les tests qui ont besoin du corpus de référence sont sautés quand
`corpus/files/` est absent : ces fichiers ne sont pas publiés (voir
`corpus/README.md`).

## Comment l'utiliser

- **Bibliothèque Python** — `pip install talax`, à intégrer dans votre
  plateforme
- **CLI** — tourne sur votre machine, votre fichier ne la quitte pas.
  Recommandée pour les fichiers sensibles.
- **Application web** — hébergée, pour les vérifications rapides. Les fichiers
  sont analysés puis supprimés immédiatement, jamais conservés.

Nécessite [ExifTool](https://exiftool.org/) et, pour la vidéo,
[ffprobe](https://ffmpeg.org/).

## Contribuer

Le projet est ouvert aux contributions. La plus précieuse sera les
**empreintes de plateformes** : les caractéristiques mesurées de la façon dont
une plateforme et une version d'app retraitent les fichiers. Un guide de
contribution arrivera avec le premier code.

## Licence

[Apache-2.0](LICENSE)
