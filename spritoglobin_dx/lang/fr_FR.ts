<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="fr_FR">
<context>
    <name>ColorAnimationTimeline</name>
    <message>
        <location filename="../gui.py" line="788"/>
        <source>Color:</source>
        <translation>Couleur :</translation>
    </message>
    <message>
        <location filename="../gui.py" line="790"/>
        <source>Alpha:</source>
        <translation>Alpha :</translation>
    </message>
    <message>
        <location filename="../gui.py" line="924"/>
        <source>Global Palette Color: {0}</source>
        <extracomment>This is referring to which color in the global palette (not an official name) is affected by the current color animation.</extracomment>
        <translation>Couleur de la palette globale : {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="927"/>
        <source>Persistent: {0}</source>
        <extracomment>Refers to whether a color animation continues to loop independently of the current sprite animation or not.</extracomment>
        <translation>Persistant : {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="969"/>
        <source>Start/End Colors:</source>
        <extracomment>Refers to the starting color and the ending color of the current keyframe.</extracomment>
        <translation>Commencer/terminer les couleurs :</translation>
    </message>
    <message>
        <location filename="../gui.py" line="1023"/>
        <source>Current Animation Layer ({0} Total)</source>
        <translation>Calque d&apos;animation actuel ({0} en tout)</translation>
    </message>
</context>
<context>
    <name>FileImportWindow</name>
    <message>
        <location filename="../popups.py" line="31"/>
        <source>Import Object File</source>
        <extracomment>Window title.</extracomment>
        <translatorcomment>finally, it will not be capitalized for adaptation reasons</translatorcomment>
        <translation>Importer un fichier objet</translation>
    </message>
    <message>
        <location filename="../popups.py" line="36"/>
        <source>Choose File</source>
        <translation>Choisir un fichier</translation>
    </message>
    <message>
        <location filename="../popups.py" line="41"/>
        <location filename="../popups.py" line="139"/>
        <source>No File Selected</source>
        <translation>Aucun fichier choisi</translation>
    </message>
    <message>
        <location filename="../popups.py" line="44"/>
        <source>Alphabetize File Contents After Import</source>
        <translation>Alphabétiser le contenu du fichier après importation</translation>
    </message>
    <message>
        <location filename="../popups.py" line="47"/>
        <source>Import File!</source>
        <translation>Importer le fichier !</translation>
    </message>
    <message>
        <location filename="../popups.py" line="82"/>
        <location filename="../popups.py" line="89"/>
        <source>Choose Object Archive</source>
        <extracomment>Window title.</extracomment>
        <translation>Choisir une archive objet</translation>
    </message>
    <message>
        <location filename="../popups.py" line="84"/>
        <source>Please choose an Object archive from {0}, or {1}.</source>
        <extracomment>&quot;{0}, or {1}&quot; appears as &quot;Paper Jam, Superstar Saga DX, or Bowser&apos;s Inside Story DX&quot; in-program (not exact titles but you get the idea)</extracomment>
        <translation>Veuillez choisir une archive objet depuis {0}, ou {1}.</translation>
    </message>
    <message>
        <location filename="../popups.py" line="123"/>
        <source>The file appears to be a valid Object archive, but the data appears to be corrupted or in an unrecognized format.</source>
        <extracomment>For uploading unsupported Obj files. The file had valid CA info, but all tests to check which game it&apos;s from have failed.</extracomment>
        <translation>Le fichier semble être une archive objet valide, mais les données semblent être corrompues ou dans un format non-reconnu.</translation>
    </message>
    <message>
        <location filename="../popups.py" line="125"/>
        <source>The file does not appear to be a valid Object archive.</source>
        <extracomment>For uploading files with a valid BG4 magic number, but no CA info. It&apos;s not an Obj archive.</extracomment>
        <translation>Le fichier ne semble pas être une archive objet valide.</translation>
    </message>
    <message>
        <location filename="../popups.py" line="127"/>
        <source>The file does not appear to be a valid Object archive. Only Object archives from {0}, and {1} are currently supported.</source>
        <extracomment>For uploading any old data file that&apos;s not recognized by any of the program&apos;s tests. Clarifies which games are supported due to the fact that the uploader might be trying to import data from a game that&apos;s planned for future support, like Dream Team (as of writing this note).</extracomment>
        <translation>Le fichier ne semble pas être une archive objet valide. Seules les archives objet depuis {0}, et {1} sont actuellement supportées.</translation>
    </message>
    <message>
        <location filename="../popups.py" line="131"/>
        <source>Failed to Import File</source>
        <extracomment>Window title.</extracomment>
        <translation>L&apos;importation du fichier a échoué</translation>
    </message>
    <message>
        <location filename="../popups.py" line="133"/>
        <source>The chosen file raised an error: &quot;{0}&quot;

{1}</source>
        <translation>Le fichier choisi a reflété une erreur : &quot;{0}&quot;

{1}</translation>
    </message>
    <message>
        <location filename="../popups.py" line="147"/>
        <location filename="../popups.py" line="149"/>
        <source>BG4 Archive (Version {0}.{1})</source>
        <translation>Archive BG4 (Version {0}.{1})</translation>
    </message>
    <message>
        <location filename="../popups.py" line="157"/>
        <source>CellAnime Info</source>
        <extracomment>DO NOT TRANSLATE &quot;CellAnime&quot; AS IT IS AN INTERNAL NAME</extracomment>
        <translation>Info CellAnime</translation>
    </message>
    <message>
        <location filename="../popups.py" line="163"/>
        <location filename="../popups.py" line="170"/>
        <source>{0} Valid Entries, {1} Invalid Entries</source>
        <extracomment>Displays the amount of files that are full of CellAnime data, versus how many files are either unused or full of improper data.</extracomment>
        <translation>{0} entrées valides, {1} entrées invalides</translation>
    </message>
</context>
<context>
    <name>GifExportWindow</name>
    <message>
        <location filename="../popups.py" line="194"/>
        <location filename="../popups.py" line="554"/>
        <source>Export File</source>
        <extracomment>Window title.</extracomment>
        <translation>Exporter un fichier</translation>
    </message>
    <message>
        <location filename="../popups.py" line="204"/>
        <location filename="../popups.py" line="205"/>
        <source>{0} fps</source>
        <extracomment>Framerate indicator, displays as &quot;60 / 50 fps&quot; and &quot;30 / 25 fps&quot; in English. Uses two numbers because GIFs have really weird speed limitations, unlike animated PNGs.</extracomment>
        <translation>{0} FPS</translation>
    </message>
    <message>
        <location filename="../popups.py" line="253"/>
        <source>Export File!</source>
        <translation>Exporter un fichier !</translation>
    </message>
    <message>
        <location filename="../popups.py" line="297"/>
        <source>Framerate:</source>
        <translation>Fréquence :</translation>
    </message>
    <message>
        <location filename="../popups.py" line="302"/>
        <source>Color Animation:</source>
        <translation>Animation de couleur :</translation>
    </message>
    <message>
        <location filename="../popups.py" line="307"/>
        <source>Playback Speed:</source>
        <translation>Relancer la vitesse :</translation>
    </message>
    <message>
        <location filename="../popups.py" line="312"/>
        <source>Sprite Scale:</source>
        <translation>Échelle du sprite :</translation>
    </message>
    <message>
        <location filename="../popups.py" line="318"/>
        <source>Animation Sequence:</source>
        <extracomment>Refers to a sequence of animations to play in order.</extracomment>
        <translation>Séquence d&apos;animation :</translation>
    </message>
    <message>
        <location filename="../popups.py" line="323"/>
        <source>Animation:</source>
        <translation>Animation :</translation>
    </message>
    <message>
        <location filename="../popups.py" line="328"/>
        <source>Loops:</source>
        <translation>Répétitions :</translation>
    </message>
    <message>
        <location filename="../popups.py" line="488"/>
        <source>None</source>
        <extracomment>Used when a file has no color animations.</extracomment>
        <translation>Aucun</translation>
    </message>
    <message>
        <location filename="../popups.py" line="513"/>
        <source>Animation {0}</source>
        <translation>Animation {0}</translation>
    </message>
    <message>
        <location filename="../popups.py" line="515"/>
        <source>Animation {0} ({1} Loops)</source>
        <translation>Animation {0} ({1} répétitions)</translation>
    </message>
    <message>
        <location filename="../popups.py" line="734"/>
        <source>Export Successful</source>
        <extracomment>Window title.</extracomment>
        <translation>Exportation réussie</translation>
    </message>
    <message>
        <location filename="../popups.py" line="735"/>
        <source>File {0} has been successfully exported!</source>
        <translation>Le fichier {0} a été exporté avec succès !</translation>
    </message>
</context>
<context>
    <name>GraphicsAnimationTimeline</name>
    <message>
        <location filename="../gui.py" line="565"/>
        <source>Show Animation Bounding Box</source>
        <translation>Afficher les animations de la bounding box</translation>
    </message>
    <message>
        <location filename="../gui.py" line="668"/>
        <location filename="../gui.py" line="670"/>
        <location filename="../gui.py" line="674"/>
        <source>Sprite Part(s) Used: {0}</source>
        <translation>Partie(s) de sprite utilisée(s) : {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="673"/>
        <source>No Sprite Parts Used!</source>
        <translation>Aucune partie de sprite utilisée !</translation>
    </message>
    <message>
        <location filename="../gui.py" line="679"/>
        <location filename="../gui.py" line="683"/>
        <source>Transformation Matrix Used: {0}</source>
        <translation>Moule(s) de transformation utilisé(s) : {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="682"/>
        <source>No Transformation Matrix Used!</source>
        <translation>Aucun moule de transformation utilisé !</translation>
    </message>
    <message>
        <location filename="../gui.py" line="688"/>
        <source>(Rotation is Inverted)</source>
        <translation>(La rotation est inversée)</translation>
    </message>
    <message>
        <location filename="../gui.py" line="702"/>
        <source>X Scale: {0}</source>
        <translation>Taille X : {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="703"/>
        <source>X Shear: {0}</source>
        <translation>Coupe X : {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="704"/>
        <source>X Position: {1}</source>
        <translation>Position X : {1}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="705"/>
        <source>Y Shear: {0}</source>
        <translation>Coupe Y : {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="706"/>
        <source>Y Scale: {0}</source>
        <translation>Taille Y : {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="707"/>
        <source>Y Position: {1}</source>
        <translation>Position Y : {1}</translation>
    </message>
</context>
<context>
    <name>MainWindow</name>
    <message>
        <location filename="../main.py" line="200"/>
        <source>CheckUpdateErrorTitle</source>
        <translation>Nouvelle mise à jour disponible</translation>
    </message>
    <message>
        <location filename="../main.py" line="201"/>
        <source>CheckUpdateErrorBlurb</source>
        <translation>Pas de nouvelles mises à jour</translation>
    </message>
    <message>
        <location filename="../main.py" line="216"/>
        <source>CheckUpdateNewVersionAssurance</source>
        <translation>&amp;Recherche auto. de mises à jour</translation>
    </message>
    <message>
        <location filename="../main.py" line="218"/>
        <source>CheckUpdateNewVersionTitle</source>
        <translation>Vérification de mises à jour automatique</translation>
    </message>
    <message>
        <location filename="../main.py" line="219"/>
        <source>CheckUpdateNewVersionBlurb</source>
        <translation>Une nouvelle mise à jour est disponible : {0}
---
{1}
---
Installez-la ici : {2}</translation>
    </message>
    <message>
        <location filename="../main.py" line="225"/>
        <source>CheckUpdateNewVersionRemindOption</source>
        <translation>Me rappeler plus tard</translation>
    </message>
    <message>
        <location filename="../main.py" line="226"/>
        <source>CheckUpdateNewVersionIgnoreOption</source>
        <translation>Passer cette version</translation>
    </message>
    <message>
        <location filename="../main.py" line="238"/>
        <source>CheckUpdateUpToDateTitle</source>
        <translation>Pas de nouvelles mises à jour</translation>
    </message>
    <message>
        <location filename="../main.py" line="239"/>
        <source>CheckUpdateUpToDateBlurb</source>
        <translation>Vous avez déjà tout ! Il n&apos;y a pas de nouvelles mises à jour à installer.</translation>
    </message>
    <message>
        <location filename="../main.py" line="257"/>
        <source>MenuBarFileTitle</source>
        <translation>&amp;Fichier</translation>
    </message>
    <message>
        <location filename="../main.py" line="259"/>
        <source>MenuBarFileOpenOption</source>
        <translation>&amp;Ouvrir un fichier</translation>
    </message>
    <message>
        <location filename="../main.py" line="264"/>
        <source>MenuBarFileCloseOption</source>
        <translation>&amp;Fermer le fichier</translation>
    </message>
    <message>
        <location filename="../main.py" line="271"/>
        <source>MenuBarFileQuickExportOption</source>
        <translation>&amp;Exporter rapidement l&apos;animation</translation>
    </message>
    <message>
        <location filename="../main.py" line="276"/>
        <source>MenuBarFileExportOption</source>
        <translation>Exporter la &amp;séquence d&apos;animation</translation>
    </message>
    <message>
        <location filename="../main.py" line="283"/>
        <source>MenuBarFileQuitOption</source>
        <translation>&amp;Quitter</translation>
    </message>
    <message>
        <location filename="../main.py" line="289"/>
        <source>MenuBarOptionsTitle</source>
        <translation>&amp;Paramètres</translation>
    </message>
    <message>
        <location filename="../main.py" line="291"/>
        <source>MenuBarOptionsLanguageOption</source>
        <translation>&amp;Langue</translation>
    </message>
    <message>
        <location filename="../main.py" line="299"/>
        <source>MenuBarOptionsLanguageSystem</source>
        <translation>&lt;Langue système&gt;</translation>
    </message>
    <message>
        <location filename="../main.py" line="311"/>
        <source>MenuBarOptionsFramerateOption</source>
        <translation>&amp;Fréquence d&apos;image</translation>
    </message>
    <message>
        <location filename="../main.py" line="316"/>
        <location filename="../main.py" line="317"/>
        <source>MenuBarOptionsFramerate</source>
        <translation>{0} fps</translation>
    </message>
    <message>
        <location filename="../main.py" line="330"/>
        <source>MenuBarOptionsMuteOption</source>
        <translation>&amp;Couper l&apos;audio</translation>
    </message>
    <message>
        <location filename="../main.py" line="335"/>
        <source>MenuBarOptionsCheckUpdatesOption</source>
        <translation>&amp;Recherche auto. de mises à jour</translation>
    </message>
    <message>
        <location filename="../main.py" line="340"/>
        <source>MenuBarOptionsEditThemeOption</source>
        <translation>&amp;Modifier le thème</translation>
    </message>
    <message>
        <location filename="../main.py" line="352"/>
        <source>MenuBarHelpTitle</source>
        <translation>&amp;Aide</translation>
    </message>
    <message>
        <location filename="../main.py" line="355"/>
        <source>MenuBarHelpCheckUpdates</source>
        <translation>&amp;Rechercher des mises à jour</translation>
    </message>
    <message>
        <location filename="../main.py" line="453"/>
        <source>ShowBoundingBoxToggle</source>
        <translation>Afficher la bounding box de l&apos;objet</translation>
    </message>
    <message>
        <location filename="../main.py" line="461"/>
        <source>ColorAnimSelectorTitle</source>
        <translation>Animations de couleur :</translation>
    </message>
    <message>
        <location filename="../main.py" line="479"/>
        <source>AnimationTabsSpriteAnimTitle</source>
        <translation>Animation de sprite</translation>
    </message>
    <message>
        <location filename="../main.py" line="480"/>
        <source>AnimationTabsSpriteColorAnimTitle</source>
        <translation>Animation unique de couleur</translation>
    </message>
    <message>
        <location filename="../main.py" line="481"/>
        <source>AnimationTabsSpriteGlobalAnimTitle</source>
        <translation>Animation globale de couleur</translation>
    </message>
    <message>
        <location filename="../main.py" line="496"/>
        <source>SpritePartSetSelectorTitle</source>
        <translation>Paramètre de la partie du sprite actuel :</translation>
    </message>
    <message>
        <location filename="../main.py" line="521"/>
        <source>SpritePartSelectorTitle</source>
        <translation>Partie du sprite actuel :</translation>
    </message>
    <message>
        <location filename="../main.py" line="611"/>
        <source>ObjectSelectorTitle</source>
        <translation>Objet actuel :</translation>
    </message>
    <message>
        <location filename="../main.py" line="616"/>
        <source>AnimationSelectorTitle</source>
        <translation>Animations :</translation>
    </message>
    <message>
        <location filename="../main.py" line="690"/>
        <source>ExportFailNoDataTitle</source>
        <translation>Aucune donnée d&apos;objet</translation>
    </message>
    <message>
        <location filename="../main.py" line="691"/>
        <source>ExportFailNoDataBlurb</source>
        <translation>Il n&apos;y a actuellement aucune donnée d&apos;objet chargée ! Veuillez charger une archive objet avant d&apos;essayer d&apos;exporter un fichier</translation>
    </message>
    <message>
        <location filename="../main.py" line="760"/>
        <source>GameTitleML1</source>
        <translation>Mario &amp; Luigi : Superstar Saga</translation>
    </message>
    <message>
        <location filename="../main.py" line="761"/>
        <source>GameTitleML2</source>
        <translation>Mario &amp; Luigi : Les frères du temps</translation>
    </message>
    <message>
        <location filename="../main.py" line="762"/>
        <source>GameTitleML3</source>
        <translation>Mario &amp; Luigi : Voyage au centre de Bowser</translation>
    </message>
    <message>
        <location filename="../main.py" line="763"/>
        <source>GameTitleML4</source>
        <translation>Mario &amp; Luigi : Dream Team Bros.</translation>
    </message>
    <message>
        <location filename="../main.py" line="764"/>
        <source>GameTitleML5</source>
        <translation>Mario &amp; Luigi : Paper Jam Bros.</translation>
    </message>
    <message>
        <location filename="../main.py" line="765"/>
        <source>GameTitleML1R</source>
        <translation>Mario &amp; Luigi : Superstar Saga + Les sbires de Bowser</translation>
    </message>
    <message>
        <location filename="../main.py" line="766"/>
        <source>GameTitleML3R</source>
        <translation>Mario &amp; Luigi : Voyage au centre de Bowser + L&apos;épopée de Bowser Jr.</translation>
    </message>
    <message>
        <location filename="../main.py" line="770"/>
        <source>GenericBooleanAffirmative</source>
        <translation>oui</translation>
    </message>
    <message>
        <location filename="../main.py" line="771"/>
        <source>GenericBooleanNegative</source>
        <translation>non</translation>
    </message>
    <message>
        <location filename="../main.py" line="772"/>
        <source>GenericDataNone</source>
        <translation>aucun</translation>
    </message>
    <message>
        <location filename="../main.py" line="834"/>
        <source>CheckUpdateQueryLinkString</source>
        <translation>Déclaration de confidentialité</translation>
    </message>
    <message>
        <location filename="../main.py" line="843"/>
        <source>CheckUpdateQueryTitle</source>
        <translation>Vérification de mises à jour automatique</translation>
    </message>
    <message>
        <location filename="../main.py" line="844"/>
        <source>CheckUpdateQueryBlurb</source>
        <translation>Autoriser Spritoglobin DX à se connecter automatiquement à Internet pour rechercher des mises à jour ?

Cela peut toujours être changé dans les paramètres.

Note : Cela créera une requête aux serveurs de GitHub, qui recevront votre adresse IP et l&apos;utiliseront selon leur {0}.</translation>
    </message>
    <message>
        <location filename="../main.py" line="1006"/>
        <source>ColorModeInfo</source>
        <translation>Mode de couleur : {0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="1345"/>
        <source>SpritePartBufferOffset</source>
        <translation>Données de tampon graphique : {0}h - {1}h</translation>
    </message>
    <message>
        <location filename="../main.py" line="1352"/>
        <source>SpritePartSize0</source>
        <translation>0 (petite)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1352"/>
        <source>SpritePartSize1</source>
        <translation>1 (moyenne)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1352"/>
        <source>SpritePartSize2</source>
        <translation>2 (grande)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1352"/>
        <source>SpritePartSize3</source>
        <translation>3 (très grande)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1353"/>
        <source>SpritePartShape0</source>
        <translation>0 (carrée)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1353"/>
        <source>SpritePartShape1</source>
        <translation>1 (large)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1353"/>
        <source>SpritePartShape2</source>
        <translation>2 (haute)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1368"/>
        <source>SpritePartSizeTitle</source>
        <translation>Taille : {0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="1370"/>
        <source>SpritePartShapeTitle</source>
        <translation>Forme : {0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="1372"/>
        <source>SpritePartSizePixels</source>
        <translation>({0} px, {1} px)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1374"/>
        <source>SpritePartFlipHorizontal</source>
        <translation>Ret. horizontal : {0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="1376"/>
        <source>SpritePartFlipVertical</source>
        <translation>Ret. vertical : {0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="1378"/>
        <source>SpritePartOffset</source>
        <translation>Offset : ({0}px, {1}px)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1398"/>
        <source>SpritePartRendererTitle</source>
        <translation>Rendu : {0}</translation>
    </message>
</context>
<context>
    <name>ProgramThemeEditor</name>
    <message>
        <location filename="../popups.py" line="758"/>
        <source>Edit Theme</source>
        <extracomment>Window title.</extracomment>
        <translation>Modifier le thème</translation>
    </message>
    <message>
        <location filename="../popups.py" line="784"/>
        <source>Recolor Icons According to Theme</source>
        <extracomment>Refers to whether or not the icons will be automatically recolored based on the four main theme colors the user has chosen.</extracomment>
        <translation>Changer la couleur des icônes selon le thème</translation>
    </message>
    <message>
        <location filename="../popups.py" line="879"/>
        <source>Apply Theme!</source>
        <translation>Appliquer le thème !</translation>
    </message>
    <message>
        <location filename="../popups.py" line="891"/>
        <source>Theme Settings:</source>
        <translation>Paramètres du thème :</translation>
    </message>
    <message>
        <location filename="../popups.py" line="896"/>
        <source>Theme Presets:</source>
        <extracomment>Referring to buttons you can click to automatically set your theme to a few pre-determined colors.</extracomment>
        <translation>Préconfigurations du thème :</translation>
    </message>
    <message>
        <location filename="../popups.py" line="900"/>
        <source>Preview:</source>
        <translation>Aperçu :</translation>
    </message>
</context>
</TS>
