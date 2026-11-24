# Lire un rapport

Ce guide explique ce que dit chaque partie d'un rapport Tala X, sur le site
comme en ligne de commande, et ce qu'il faut en faire.

## 1. Ce que Tala X dit, et ce qu'il ne dit pas

**Tala X ne dit jamais qu'une image est vraie ou fausse, et ne certifie
rien.** Il dit ce qu'on peut honnêtement affirmer d'un fichier, et ce qu'on ne
peut pas.

- « Original d'appareil » veut dire que le fichier porte les marques d'un
  appareil photo. Pas que ce qu'il montre est vrai : quelqu'un qui sait faire
  peut falsifier des métadonnées.
- Tala X est conçu contre le **blanchiment par les plateformes** (une photo
  recyclée, recompressée, sortie de son contexte, avec une fausse légende), pas
  contre un faussaire expert.
- Ne présentez jamais un résultat de Tala X comme une certification.

## 2. Le résultat d'intégrité

C'est la première réponse du rapport : **d'où vient le fichier ?** Il y a trois
résultats possibles.

| Résultat | Ce que ça veut dire | Quoi faire |
| --- | --- | --- |
| **Original d'appareil** | Le fichier porte les marques d'un appareil : marque et modèle, heure de prise de vue, données propres au fabricant, dimensions d'origine, aucun logiciel de retouche connu. | Lisez les contrôles : ils ont de quoi travailler. |
| **Copie retraitée** | Le fichier a été réenregistré par une application ou une plateforme qui a effacé les métadonnées. Quand Tala X reconnaît l'empreinte (WhatsApp, par exemple), il le dit. | Ce n'est pas un échec : demandez l'original à votre source, vérifiez la légende, faites une recherche inversée. |
| **Indéterminé** | Des marques d'appareil, mais pas toutes : export d'un logiciel de retouche, conversion de format, capture d'écran… | Prudence : le fichier n'est plus celui de l'appareil. Demandez l'original. |

L'explication sous le résultat dit toujours ce qui l'a décidé.

## 3. Les quatre états

Chaque contrôle rend un état, **toujours avec son explication** :

| État | Ce que ça veut dire |
| --- | --- |
| **Cohérent** | Le contrôle a pu se faire, et rien ne se contredit. |
| **À vérifier** | Une anomalie, qui peut avoir une explication légitime (une horloge mal réglée, un logiciel de retouche). |
| **Suspect** | Une contradiction difficile à expliquer autrement (la nuit sur la photo, le soleil haut dans le ciel à l'heure indiquée). |
| **Non vérifiable** | L'information nécessaire manque, souvent parce qu'une plateforme l'a effacée. **Ce n'est pas un mauvais signe** : c'est ce qui n'a pas pu être vérifié. |

Un contrôle « Non vérifiable » reste affiché exprès : vous devez savoir ce qui
n'a **pas** été vérifié.

## 4. Les contrôles, un par un

| Contrôle | Ce qu'il vérifie |
| --- | --- |
| **Format réel du fichier** | Si l'extension (`.jpg`, `.png`…) correspond au contenu. Une photo renommée (un `.png` qui contient du JPEG) est « À vérifier » : c'est souvent sans malice, mais le fichier a été manipulé. |
| **Position GPS** | Où l'appareil s'est situé, et avec quelle précision. Une position masquée (souvent par Android lors d'un partage) est dite « masquée », pas « absente ». |
| **Date et heure** | Quand la photo a été prise, et si les horloges de l'appareil concordent. Une heure de prise de vue qui ne correspond pas à l'horloge interne du fabricant est « Suspect » : c'est la trace d'une date modifiée. |
| **Fuseau horaire** | Si le fuseau enregistré par l'appareil correspond à celui du lieu (heure d'été comprise). |
| **Cohérence solaire** | Où était le soleil au lieu et à l'heure de la photo, et si cela concorde avec ce que vous voyez (jour, crépuscule, nuit). Décrit aussi la direction et la longueur attendues des ombres. |
| **Lieu et date déclarés** | Seulement si vous avez saisi une légende : à quelle distance et à quel écart de temps elle est du fichier. Plus de 100 km : « Suspect » ; un écart de date : au plus « À vérifier », car les horloges sont souvent mal réglées. |
| **Météo** | Seulement si vous l'avez demandée : le temps donné par le modèle d'Open-Meteo, comparé à ce que vous voyez. Au plus « À vérifier », jamais « Suspect » : le modèle travaille sur des carrés de 9 à 25 km. |
| **Logiciel de retouche** | Si un éditeur d'image est inscrit dans le fichier (Photoshop, Lightroom, GIMP…). « Non vérifiable » quand rien n'est inscrit : beaucoup de logiciels n'écrivent rien. |
| **Certificats C2PA** | Les « Content Credentials » : une signature numérique qui dit qui a produit ou modifié le fichier, et parfois qu'une IA a été utilisée. « Cohérent » seulement si la signature est intacte et vient d'une organisation de la liste officielle de la C2PA ; « Suspect » si la signature est cassée ; « À vérifier » si le fichier a été modifié après la signature ou si le signataire n'est pas reconnu. La plupart des photos n'en ont pas. |

Sous chaque contrôle, **Valeurs brutes** montre les données qui ont mené à
l'état.

## 5. L'image et son aperçu intégré

Beaucoup de fichiers contiennent un petit aperçu de l'image. Le rapport les
montre côte à côte. Certains logiciels modifient l'image mais laissent l'ancien
aperçu, qui peut alors montrer ce qu'il y avait avant.

C'est une **exploration visuelle, non concluante** : sur de vraies photos, les
deux peuvent aussi différer un peu (cadrage, couleurs). Aucun état n'en est
tiré : regardez par vous-même.

## 6. Ce que Tala X ne fait pas, volontairement

- **Il ne détecte pas les images générées par IA en analysant les pixels.**
  Ces détecteurs se trompent trop : après le redimensionnement et la
  compression qu'appliquent toutes les plateformes, ils tombent au niveau du
  hasard, avec jusqu'à un tiers de fausses alertes sur de vraies photos de
  presse. Seule une IA **déclarée** dans un certificat C2PA est signalée.
- Il ne rend pas de verdict à partir de l'analyse des niveaux d'erreur (ELA).
- Il ne devine pas un lieu à partir de ce que montre l'image : c'est un travail
  d'enquête humain.
- Pour une vidéo, il ne lit que les métadonnées du conteneur.

## 7. Et ensuite ?

- **Demander l'original** à la source, avec le message proposé, envoyé
  « comme document » ou en pièce jointe d'un e-mail.
- **Vérifier la légende** : saisir le lieu et la date annoncés.
- **Chercher si la photo a déjà circulé** (Google Lens, TinEye, Yandex) : la
  plupart des fausses informations visuelles sont de vraies photos anciennes,
  avec une nouvelle légende.
- **Garder le rapport** : HTML, ou PDF par l'impression.

## 8. Le rapport d'un lot

`talax batch` donne en plus :

- **Même image** : les fichiers identiques (« même fichier »), les copies d'une
  même photo (« même image »), et les images très proches (« la même photo
  retouchée, ou des photos prises à un instant d'écart »). C'est une
  ressemblance calculée, à vérifier à l'œil ; elle ne dit rien de la véracité
  d'une image. Une copie recadrée n'est en général pas retrouvée.
- **Chronologie** : les photos dans l'ordre réel de prise de vue quand tous les
  fuseaux sont connus ; sinon dans l'ordre de l'heure affichée par les
  appareils, et la durée totale est dite approximative.
- **Lieux** : les positions des photos et la plus grande distance entre deux
  d'entre elles.
