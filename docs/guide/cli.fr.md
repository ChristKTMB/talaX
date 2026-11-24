# La ligne de commande

`talax` fait la même analyse que le site, mais **sur votre ordinateur** : le
fichier ne le quitte pas. C'est le bon choix pour un fichier sensible, et le
seul pour analyser un dossier entier.

## 1. Installer

Il faut deux choses : **Tala X** et **ExifTool 13 ou plus récent**, le
programme qui lit les métadonnées. Tala X refuse de tourner avec une version
plus ancienne d'ExifTool, qui donnerait d'autres résultats.

### Windows

Tout se fait dans **PowerShell** (menu Démarrer, tapez « PowerShell »).

**1. Installer uv**, qui installe Tala X et la bonne version de Python :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Fermez PowerShell, rouvrez-le, puis vérifiez : `uv --version`.

**2. Installer ExifTool :**

1. Sur <https://exiftool.org/>, téléchargez la version Windows 64 bits
   (fichier `exiftool-XX.XX_64.zip`).
2. Décompressez-la dans `C:\Tools\`, puis renommez le dossier en `exiftool`.
3. Dans ce dossier, renommez `exiftool(-k).exe` en `exiftool.exe`. Gardez le
   dossier `exiftool_files` à côté : ExifTool en a besoin.
4. Ajoutez le dossier au PATH de votre compte :

   ```powershell
   $p = [Environment]::GetEnvironmentVariable("Path", "User")
   [Environment]::SetEnvironmentVariable("Path", "$p;C:\Tools\exiftool", "User")
   ```

5. Fermez PowerShell, rouvrez-le, puis vérifiez : `exiftool -ver` (13 ou plus).

**3. Installer Tala X :**

```powershell
uv tool install talax
talax version
```

### macOS

Dans le Terminal :

```bash
brew install exiftool uv
uv tool install talax
talax version
```

(Sans Homebrew : installez uv avec `curl -LsSf https://astral.sh/uv/install.sh | sh`,
et ExifTool depuis le paquet macOS d'<https://exiftool.org/>.)

### Linux

Les paquets ExifTool des distributions sont souvent trop anciens (Ubuntu 24.04
fournit la 12.76). Installez la dernière version dans votre dossier
personnel :

```bash
v=$(curl -fsS https://exiftool.org/ver.txt)
mkdir -p ~/.local/opt ~/.local/bin
curl -fsSL "https://sourceforge.net/projects/exiftool/files/Image-ExifTool-$v.tar.gz/download" | tar -xz -C ~/.local/opt
ln -sf ~/.local/opt/Image-ExifTool-$v/exiftool ~/.local/bin/exiftool
exiftool -ver
```

Puis Tala X :

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install talax
talax version
```

### Avec pip, si vous préférez

Tala X demande Python 3.12 ou plus récent :

```bash
python3 -m venv ~/talax-env
source ~/talax-env/bin/activate        # PowerShell : ~\talax-env\Scripts\Activate.ps1
pip install talax
```

### Mettre à jour, désinstaller

```bash
uv tool upgrade talax       # ou : pip install --upgrade talax
uv tool uninstall talax     # ou : pip uninstall talax
```

L'installation pèse environ 200 Mo, surtout à cause des bibliothèques qui
lisent les certificats C2PA et trouvent le fuseau horaire d'une position sans
Internet.

## 2. Analyser une photo : `talax analyze`

```bash
talax analyze photo.jpg
```

Le rapport s'affiche dans le terminal : le résultat d'intégrité, puis chaque
contrôle avec son état et son explication. Pour une copie, le message à
envoyer à la source ; pour toute photo, les liens de recherche inversée. Voir
[Lire un rapport](report.fr.md).

Toutes les options :

| Option | Rôle |
| --- | --- |
| `--lang fr` | Langue du rapport (`en` ou `fr`) ; par défaut, celle de votre système |
| `--sky day` | Ce que montre la photo : `day` (jour), `twilight` (crépuscule) ou `night` (nuit), pour la cohérence solaire |
| `--place "-1.68,29.22" --at "2026-06-14 10:00"` | Le lieu (latitude, longitude) et l'heure locale qu'annonce la légende ; les deux ensemble |
| `--weather` | Demander la météo à Open-Meteo ; **seule option qui utilise le réseau** (voir plus bas) |
| `--conditions rain` | Le temps que montre la photo, avec `--weather` : `rain` (pluie), `snow` (neige), `overcast` (couvert), `clear` (dégagé ou ombres nettes) |
| `--html rapport.html` | Écrire aussi un rapport HTML autonome |
| `--json` | Écrire l'analyse en JSON, pour un autre programme |

Exemples :

```bash
# Le rapport en français, et en HTML pour le garder
talax analyze photo.jpg --lang fr --html rapport.html

# La photo montre la nuit : est-ce possible à l'heure enregistrée ?
talax analyze photo.jpg --sky night

# La légende dit « Goma, le 14 juin 2026 à 10 h », la photo montre le jour
talax analyze photo.jpg --place "-1.68,29.22" --at "2026-06-14 10:00" --sky day

# La photo montre de la pluie : que dit le modèle météo ?
talax analyze photo.jpg --place "-1.68,29.22" --at "2026-06-14 10:00" --weather --conditions rain
```

Sur l'option `--weather` : votre ordinateur envoie à Open-Meteo la position
arrondie à environ 11 km et la date, avec votre adresse IP ; Open-Meteo peut
les garder 90 jours. Sans cette option, **rien ne part sur le réseau**.

Pour le PDF : ouvrez le rapport HTML, imprimez-le (Ctrl+P, ou ⌘P sur Mac) et
choisissez « Enregistrer au format PDF ».

## 3. Analyser un dossier : `talax batch`

```bash
talax batch photos/
```

Tala X analyse tous les fichiers du dossier (pas ses sous-dossiers), quatre à
la fois, puis affiche :

- **un tableau** : chaque fichier, son intégrité, son heure de prise de vue,
  sa position, et les contrôles à regarder d'abord ;
- **Même image** : les fichiers identiques, les copies d'une même photo, les
  images très proches (retouche, photos prises à un instant d'écart) ;
- **Chronologie** : les photos dans l'ordre de prise de vue ;
- **Lieux** : les positions, et la plus grande distance entre deux photos.

Les fichiers que Tala X ne reconnaît pas comme des images sont laissés de côté
et listés. Vous pouvez aussi donner plusieurs fichiers ou dossiers :
`talax batch photos/ autre.jpg`.

| Option | Rôle |
| --- | --- |
| `--lang fr` | Langue |
| `--html lot.html` | Un rapport HTML du lot (le détail de chaque fichier y est replié) |
| `--csv lot.csv` | Un tableau à ouvrir dans Excel ou LibreOffice, une ligne par fichier (le fichier est remplacé à chaque fois) |
| `--json` | Le lot en JSON |

Exemple :

```bash
talax batch photos/ --lang fr --html lot.html --csv lot.csv
```

Le CSV est au format standard (virgule, point décimal). Si Excel met tout dans
une seule colonne, ouvrez-le par Données → À partir d'un fichier texte, avec la
virgule comme séparateur.

La ressemblance entre images est calculée sur les pixels : vérifiez-la à
l'œil. Une copie recadrée n'est en général pas retrouvée, et une image presque
uniforme (toute noire, par exemple) n'est pas comparée.

## 4. Autres commandes

```bash
talax version             # versions de Tala X et d'ExifTool
talax --help              # toutes les commandes
talax analyze --help      # toutes les options d'une commande
```

## 5. En cas de problème

| Message | Solution |
| --- | --- |
| `talax` n'est pas reconnu | Avec uv : `uv tool update-shell`, puis rouvrez le terminal. Avec pip : activez l'environnement virtuel. |
| `exiftool` n'est pas reconnu, ou « ExifTool is required but was not found » | ExifTool n'est pas installé ou pas dans le PATH (voir l'installation). |
| « ExifTool … is too old » | Installez ExifTool 13 ou plus récent. |
| `--place and --at go together` | Donnez les deux options ensemble. |
| `expected LAT,LON` | Écrivez la latitude puis la longitude en degrés décimaux, séparées par une virgule : `"-1.68,29.22"`. |
| Les rapports contiennent des positions | C'est normal : ce sont celles des photos. Ne les partagez qu'en connaissance de cause. |
