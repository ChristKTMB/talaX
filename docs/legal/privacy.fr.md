# Politique de confidentialité — Tala X

Version du 2026-11-19.

Cette page explique ce que le service web Tala X (talax.online) fait des
fichiers et des données qu'il reçoit. Elle décrit le fonctionnement réel du
logiciel, dont le code est public : <https://github.com/ChristKTMB/talaX>.

**En bref : votre fichier est analysé puis supprimé. Rien n'est conservé :
ni le fichier, ni son nom, ni son empreinte, ni le résultat.** Seule
exception, et seulement si vous la demandez : la consultation de la météo
envoie un lieu arrondi et une date à Open-Meteo, qui peut les garder
90 jours (section 4).

## 1. Responsable du traitement

Christ KATUMBA KATUMBA, Kinshasa, République démocratique du Congo.
Contact : <contact@talax.online>

## 2. Ce que nous traitons, et pourquoi

| Donnée | Pourquoi | Combien de temps |
| --- | --- | --- |
| Le fichier que vous déposez (image et métadonnées, dont parfois une position GPS, une date, un modèle d'appareil) | L'analyser, à votre demande | Le temps de l'analyse, quelques secondes, puis supprimé, y compris en cas d'erreur |
| Ce que vous ajoutez au fichier, si vous le faites : ce que montre la photo (jour, crépuscule, nuit), le lieu et la date annoncés par une légende | Compléter l'analyse, à votre demande | Comme le fichier : le temps de l'analyse, puis oubliés |
| Le lieu de la photo, arrondi à environ 11 km, et sa date, si vous demandez la météo | Recouper avec la météo, à votre demande | Non conservés chez nous ; transmis à Open-Meteo (section 4) |
| Le résultat de l'analyse et le rapport HTML | Vous les renvoyer | Non conservés : envoyés à votre navigateur, puis oubliés |
| Votre adresse IP | Limiter le nombre d'analyses par minute, pour que le service reste disponible pour tous | Gardée dans la mémoire du serveur seulement, jamais écrite sur disque ni dans un journal ; remplacée au fil des requêtes et effacée au redémarrage |
| La langue de votre navigateur | Afficher les résultats en français ou en anglais | Non conservée |

Le fichier est traité en mémoire vive : il n'est jamais écrit sur un disque.
Les journaux techniques du serveur ne contiennent ni nom de fichier, ni
coordonnées, ni adresse IP, ni texte tiré du fichier : seulement le type de
requête, sa réponse et sa durée.

Le message à envoyer à votre source est copié par votre navigateur dans
votre presse-papiers : il n'est envoyé nulle part.

Nous n'utilisons **aucun cookie**, aucun outil de mesure d'audience, aucune
publicité, aucun service tiers dans la page (polices, scripts).

## 3. Base légale

- Le traitement du fichier, et de ce que vous y ajoutez (ce que montre la
  photo, le lieu et la date d'une légende, la consultation de la météo), est
  fait **à votre demande**, pour vous fournir le service que vous sollicitez
  (RGPD, article 6, paragraphe 1, b).
- La limitation du nombre de requêtes repose sur notre **intérêt légitime** à
  protéger le service contre la surcharge (RGPD, article 6, paragraphe 1, f).
- En République démocratique du Congo : Code du numérique (ordonnance-loi
  n° 23/010 du 13 mars 2023), titre III.

## 4. Qui d'autre reçoit des données

- **Contabo GmbH** (Allemagne), hébergeur du serveur, centre de données dans
  l'Union européenne. Votre fichier transite par ses machines le temps de
  l'analyse.
- **OpenStreetMap Foundation** (Royaume-Uni), seulement si vous demandez à
  afficher la carte. Les tuiles de carte sont demandées par notre serveur,
  pas par votre navigateur : OpenStreetMap reçoit la zone affichée, mais ni
  votre adresse IP ni votre fichier. La page vous prévient avant d'afficher
  la carte.
- **OpenMeteo GmbH** (Suisse), seulement si vous demandez la météo. Notre
  serveur lui envoie la position arrondie à environ 11 km (0,1 degré) et la
  date, jamais l'heure exacte, ni votre adresse IP, ni votre fichier.
  Open-Meteo indique garder dans ses journaux techniques, jusqu'à 90 jours,
  les requêtes reçues, coordonnées comprises ; il agit comme responsable de
  traitement indépendant. La page vous prévient avant l'envoi. La Suisse
  bénéficie d'une décision d'adéquation de la Commission européenne.
- **Google Lens, TinEye, Yandex** : seulement si vous y déposez vous-même la
  photo, en suivant les liens du rapport. Tala X ne leur envoie rien, et les
  liens ne leur transmettent pas la page d'où vous venez ; leurs propres
  conditions s'appliquent à ce que vous y déposez.

Aucune donnée n'est vendue, partagée à des fins publicitaires, ni utilisée
pour entraîner un modèle d'intelligence artificielle.

## 5. Un fichier sensible ? Utilisez l'outil en ligne de commande

Si vous protégez une source, ou si le fichier ne doit quitter votre machine
sous aucun prétexte, utilisez l'outil en ligne de commande (`pip install
talax`) : il fait la même analyse sur votre ordinateur, sans rien envoyer.
Seule exception, si vous la demandez (`--weather`) : la consultation de la
météo, faite alors directement par votre ordinateur, qui envoie à
Open-Meteo la position arrondie et la date, avec votre adresse IP.

## 6. Vos droits

Vous disposez des droits d'accès, de rectification, d'effacement,
d'opposition, de limitation et de portabilité sur vos données. Comme nous ne
conservons rien, nous n'aurons en général rien à vous communiquer ni à
effacer ; écrivez-nous quand même pour toute question : <contact@talax.online>.

Vous pouvez aussi saisir une autorité de contrôle : celle de votre pays si
vous résidez dans l'Union européenne (en France, la CNIL), ou l'autorité de
protection des données prévue par le Code du numérique en République
démocratique du Congo.

## 7. Sécurité

Connexion chiffrée (HTTPS), fichiers en mémoire seulement, conteneurs en
lecture seule et sans privilèges, aucune donnée conservée : ce qui n'est pas
gardé ne peut pas fuir.

## 8. Modifications

Toute modification de cette page est datée et visible dans l'historique du
dépôt public. En cas de divergence entre les versions, la version française
prévaut.
