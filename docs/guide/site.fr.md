# Utiliser Tala X en ligne

Tala X en ligne (<https://talax.online/fr>) analyse une photo dans votre
navigateur, sans rien installer. Ce guide montre, écran par écran, tout ce que
vous pouvez y faire.

Un fichier sensible (une source à protéger, une photo qui ne doit quitter
votre ordinateur sous aucun prétexte) ? Utilisez plutôt la
[ligne de commande](cli.fr.md) : elle fait la même analyse sur votre machine,
sans rien envoyer.

## 1. Déposer une photo

1. Ouvrez <https://talax.online/fr>.
2. Glissez la photo dans le cadre « Glissez une photo ici », ou cliquez sur
   **Choisir un fichier**.
3. Cliquez sur **Analyser la photo**.

Bon à savoir :

- **Une photo à la fois, 50 Mo au maximum.** Pour analyser un dossier entier,
  utilisez `talax batch` en [ligne de commande](cli.fr.md).
- **Formats** : JPEG, PNG, HEIC, WebP, TIFF… Tala X reconnaît le format au
  contenu du fichier, pas à son extension. Certains navigateurs n'affichent pas
  les HEIC : l'analyse porte quand même sur le fichier.
- **Prenez le fichier tel que vous l'avez reçu.** Une capture d'écran de la
  photo, ou une photo « enregistrée sous » depuis un réseau social, n'est plus
  le même fichier : elle a perdu ce qu'on cherche.
- **10 analyses par minute au plus** depuis une même connexion. Au-delà, un
  compte à rebours indique quand réessayer.

## 2. Le rapport

En quelques secondes, le rapport s'affiche, de haut en bas :

1. **Le résultat d'intégrité** : original d'appareil, copie retraitée ou
   indéterminé, avec son explication. C'est la réponse la plus importante.
   Voir [Lire un rapport](report.fr.md).
2. **Un bandeau par contrôle « Suspect »**, s'il y en a, qui mène au contrôle.
3. **Demander l'original**, si le fichier n'est pas un original d'appareil
   (voir plus bas).
4. **Vérifier la légende** (voir plus bas).
5. **Recouper avec la météo** (voir plus bas).
6. **L'image et son aperçu intégré**, côte à côte : une exploration visuelle,
   non concluante.
7. **Les contrôles**, chacun avec son état et son explication.
8. **Cette photo a-t-elle déjà circulé ?** : la recherche inversée.
9. **Avertissement**, **téléchargement** du rapport et **détails techniques**
   (empreinte SHA-256 du fichier, taille, heure de l'analyse, outils).

Le rapport n'est gardé nulle part : **si vous rechargez la page, il disparaît.**
Téléchargez-le si vous voulez le garder (section 8).

## 3. « Que montre la photo ? » : la question du ciel

Quand le fichier indique **où et quand** la photo a été prise, Tala X calcule
la position du soleil à ce moment-là. Il ne regarde pas l'image : c'est vous
qui dites ce qu'elle montre.

1. Un bandeau noir en haut du rapport pose la question ; cliquez sur
   **Répondre**.
2. Choisissez **Jour**, **Crépuscule** ou **Nuit**.
3. Le fichier est analysé de nouveau, avec votre réponse. Le contrôle
   « Cohérence solaire » compare alors le ciel que vous voyez au soleil
   calculé.

Exemple : la photo montre la nuit, mais le soleil était à 50° au-dessus de
l'horizon à l'heure et au lieu enregistrés : le contrôle passe en « Suspect ».
Si un simple décalage d'horloge (3 heures au plus) peut l'expliquer, il passe
en « À vérifier ».

Le contrôle décrit aussi où devaient tomber les ombres. Pour changer d'avis :
**Modifier la réponse**.

## 4. Vérifier la légende

Une photo circule souvent avec une légende : « Goma, ce matin ». Tala X peut
confronter ce lieu et cette date au soleil et au fichier.

- **Si le fichier ne dit pas où ou quand** la photo a été prise (le cas
  habituel d'une photo reçue par WhatsApp), la section est déjà ouverte.
- **Sinon**, cliquez sur **Saisir le lieu et la date annoncés**.

Puis :

1. **Le lieu**, de deux façons :
   - tapez ou collez les coordonnées, par exemple `-1.67920, 29.22280`
     (latitude puis longitude, en degrés décimaux ; c'est ce que donne un
     service de carte quand on clique sur un point) ;
   - ou cliquez sur **Choisir sur la carte**, puis à l'endroit annoncé. Quelques
     kilomètres d'écart changent à peine la position du soleil.
2. **La date** et **l'heure**, en heure locale du lieu.
3. Cliquez sur **Vérifier**.

Le rapport est refait avec ce lieu et cette heure :

- la **cohérence solaire** utilise la légende ; répondez ensuite à « Que montre
  la photo ? » ;
- un contrôle **Lieu et date déclarés** apparaît si le fichier a lui-même une
  position ou une heure : il dit à quelle distance et à quel écart de temps
  est la légende. Plus de 100 km entre la légende et le GPS du fichier :
  « Suspect ».

Pour corriger : **Modifier la légende** ; pour revenir au fichier seul :
**Retirer la légende**.

## 5. Recouper avec la météo

Une fois un lieu et une heure connus (par le fichier ou par la légende),
Tala X peut demander le temps qu'il faisait au modèle météo d'Open-Meteo.

1. Lisez l'avertissement : **le lieu, arrondi à environ 11 km, et la date
   sont envoyés à Open-Meteo**, qui peut les garder 90 jours dans ses
   journaux. Ni votre adresse, ni votre fichier. Pour un fichier sensible, ne
   le faites pas.
2. Cliquez sur **Consulter la météo**.
3. Répondez à **Quel temps montre la photo ?** : pluie qui tombe, neige qui
   tombe, ciel couvert, ciel dégagé ou ombres nettes.

Le contrôle « Météo » donne les valeurs du modèle (pluie, neige, nuages) et
rend au mieux « Cohérent », au pire « À vérifier ». **Jamais « Suspect »** :
le modèle travaille sur des carrés de 9 à 25 km, et une averse locale peut lui
échapper.

## 6. Demander l'original

Si le fichier est une copie retraitée ou indéterminé, la section
**Demander l'original** propose un message prêt à envoyer à votre source. Il
explique comment renvoyer la photo sans l'abîmer (WhatsApp ou Telegram « en
tant que document », ou en pièce jointe d'un e-mail).

- Cliquez sur **Copier le message**, puis collez-le dans votre conversation.
- Lisez la mise en garde : l'original peut révéler où se trouvait votre source
  et le numéro de série de son téléphone. Demandez-le seulement si elle peut
  l'envoyer sans risque, et analysez-le avec la ligne de commande.

## 7. La carte

Quand le fichier contient une position GPS valide, le contrôle « Position
GPS » propose **Afficher sur la carte**. La carte ne se charge qu'à ce
moment-là : la zone est demandée à OpenStreetMap **par notre serveur**, qui ne
transmet ni votre adresse ni votre fichier.

## 8. Garder le rapport

- **Télécharger le rapport (HTML)** : un fichier unique, qui s'ouvre sans
  connexion et ne charge rien sur Internet. Pour le fabriquer, le fichier est
  envoyé de nouveau au serveur, puis supprimé.
- **En PDF** : ouvrez le rapport téléchargé, imprimez-le (Ctrl+P, ou ⌘P sur
  Mac) et choisissez « Enregistrer au format PDF ».

## 9. La recherche inversée

Une vraie photo avec une fausse légende est plus courante qu'une photo
truquée, et aucune analyse du fichier ne la repère. La section **Cette photo
a-t-elle déjà circulé ?** donne des liens vers Google Lens, TinEye et Yandex.

1. Ouvrez un des services.
2. Déposez-y vous-même la photo.
3. Cherchez la copie la plus ancienne et comparez sa date et son lieu avec la
   légende. Si rien ne sort, réessayez avec un recadrage sur la partie la plus
   reconnaissable.

Tala X ne leur envoie rien. Eux reçoivent la photo que vous déposez et peuvent
la garder : ne le faites pas avec une photo confidentielle.

## 10. Langue

Le bouton **FR / EN** en bas de page change la langue de tout le site. Si un
rapport est affiché, il est redemandé dans l'autre langue : le fichier est
envoyé de nouveau, avec vos réponses.

## 11. Ce qui est envoyé, ce qui est gardé

- **Votre fichier** est envoyé à notre serveur (dans l'Union européenne),
  analysé en mémoire, puis supprimé. Rien n'est gardé : ni le fichier, ni son
  nom, ni son empreinte, ni le résultat.
- **Vos réponses** (ciel, légende, météo) suivent le même chemin.
- **Rien n'est écrit sur votre appareil** : pas de cookie, pas de mesure
  d'audience.
- **Seules exceptions, à votre demande** : la météo (Open-Meteo, lieu arrondi
  et date) et la carte (OpenStreetMap, zone affichée, par notre serveur).

Le détail est dans la [politique de confidentialité](../legal/privacy.fr.md).
