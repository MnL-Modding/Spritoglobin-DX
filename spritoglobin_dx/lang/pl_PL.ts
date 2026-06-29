<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="pl_PL">
<context>
    <name>ColorAnimationTimeline</name>
    <message>
        <location filename="../gui.py" line="788"/>
        <source>Color:</source>
        <translation>Kolor:</translation>
    </message>
    <message>
        <location filename="../gui.py" line="790"/>
        <source>Alpha:</source>
        <translation>Alfa:</translation>
    </message>
    <message>
        <location filename="../gui.py" line="924"/>
        <source>Global Palette Color: {0}</source>
        <extracomment>This is referring to which color in the global palette (not an official name) is affected by the current color animation.</extracomment>
        <translation>Kolor Globalnej Palety: {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="927"/>
        <source>Persistent: {0}</source>
        <extracomment>Refers to whether a color animation continues to loop independently of the current sprite animation or not.</extracomment>
        <translation>Stała animacja: {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="969"/>
        <source>Start/End Colors:</source>
        <extracomment>Refers to the starting color and the ending color of the current keyframe.</extracomment>
        <translation>Kolor Startowy/Końcowy:</translation>
    </message>
    <message>
        <location filename="../gui.py" line="1023"/>
        <source>Current Animation Layer ({0} Total)</source>
        <translation>Bieżąca Warstwa Animacji ({0} w sumie)</translation>
    </message>
</context>
<context>
    <name>FileImportWindow</name>
    <message>
        <location filename="../popups.py" line="31"/>
        <source>Import Object File</source>
        <extracomment>Window title.</extracomment>
        <translation>Importuj Obiekt</translation>
    </message>
    <message>
        <location filename="../popups.py" line="36"/>
        <source>Choose File</source>
        <translation>Wybierz Plik</translation>
    </message>
    <message>
        <location filename="../popups.py" line="41"/>
        <location filename="../popups.py" line="139"/>
        <source>No File Selected</source>
        <translation>Nie wybrano Pliku</translation>
    </message>
    <message>
        <location filename="../popups.py" line="44"/>
        <source>Alphabetize File Contents After Import</source>
        <translation>Sortuj zawartośc Pliku alfabetycznie po Imporcie</translation>
    </message>
    <message>
        <location filename="../popups.py" line="47"/>
        <source>Import File!</source>
        <translation>Importuj Plik!</translation>
    </message>
    <message>
        <location filename="../popups.py" line="82"/>
        <location filename="../popups.py" line="89"/>
        <source>Choose Object Archive</source>
        <extracomment>Window title.</extracomment>
        <translation>Wybierz Archiwum Obiektów</translation>
    </message>
    <message>
        <location filename="../popups.py" line="84"/>
        <source>Please choose an Object archive from {0}, or {1}.</source>
        <extracomment>&quot;{0}, or {1}&quot; appears as &quot;Paper Jam, Superstar Saga DX, or Bowser&apos;s Inside Story DX&quot; in-program (not exact titles but you get the idea)</extracomment>
        <translation>Proszę wybierz archiwum Obiektów z {0}, lub {1}.</translation>
    </message>
    <message>
        <location filename="../popups.py" line="123"/>
        <source>The file appears to be a valid Object archive, but the data appears to be corrupted or in an unrecognized format.</source>
        <extracomment>For uploading unsupported Obj files. The file had valid CA info, but all tests to check which game it&apos;s from have failed.</extracomment>
        <translation>Plik wygląda na prawidłowe archiwum Obiektów, lecz dane pliku zdają się być uszkodzone lub w nieznanym formacie.</translation>
    </message>
    <message>
        <location filename="../popups.py" line="125"/>
        <source>The file does not appear to be a valid Object archive.</source>
        <extracomment>For uploading files with a valid BG4 magic number, but no CA info. It&apos;s not an Obj archive.</extracomment>
        <translation>Plik nie zdaję się być prawidłowym archiwum Obiektów.</translation>
    </message>
    <message>
        <location filename="../popups.py" line="127"/>
        <source>The file does not appear to be a valid Object archive. Only Object archives from {0}, and {1} are currently supported.</source>
        <extracomment>For uploading any old data file that&apos;s not recognized by any of the program&apos;s tests. Clarifies which games are supported due to the fact that the uploader might be trying to import data from a game that&apos;s planned for future support, like Dream Team (as of writing this note).</extracomment>
        <translation>Plik nie zdaję się być prawidłowym archiwum Obiektów. Obecnie tylko achiwa z {0}, oraz {1} są wspierane.</translation>
    </message>
    <message>
        <location filename="../popups.py" line="131"/>
        <source>Failed to Import File</source>
        <extracomment>Window title.</extracomment>
        <translation>Nie udało się Importować Pliku</translation>
    </message>
    <message>
        <location filename="../popups.py" line="133"/>
        <source>The chosen file raised an error: &quot;{0}&quot;

{1}</source>
        <translation>Wybrany plik zgłosił błąd: &quot;{0}&quot;

{1}</translation>
    </message>
    <message>
        <location filename="../popups.py" line="147"/>
        <location filename="../popups.py" line="149"/>
        <source>BG4 Archive (Version {0}.{1})</source>
        <translation>BG4 Archive (Wersja {0}.{1})</translation>
    </message>
    <message>
        <location filename="../popups.py" line="157"/>
        <source>CellAnime Info</source>
        <extracomment>DO NOT TRANSLATE &quot;CellAnime&quot; AS IT IS AN INTERNAL NAME</extracomment>
        <translation>Informacja CellAnime</translation>
    </message>
    <message>
        <location filename="../popups.py" line="163"/>
        <location filename="../popups.py" line="170"/>
        <source>{0} Valid Entries, {1} Invalid Entries</source>
        <extracomment>Displays the amount of files that are full of CellAnime data, versus how many files are either unused or full of improper data.</extracomment>
        <translation>{0} Prawidłowych Wpisów, {1} Nieprawidłowych Wpisów</translation>
    </message>
</context>
<context>
    <name>GifExportWindow</name>
    <message>
        <location filename="../popups.py" line="194"/>
        <location filename="../popups.py" line="554"/>
        <source>Export File</source>
        <extracomment>Window title.</extracomment>
        <translation>Eksportuj plik</translation>
    </message>
    <message>
        <location filename="../popups.py" line="204"/>
        <location filename="../popups.py" line="205"/>
        <source>{0} fps</source>
        <extracomment>Framerate indicator, displays as &quot;60 / 50 fps&quot; and &quot;30 / 25 fps&quot; in English. Uses two numbers because GIFs have really weird speed limitations, unlike animated PNGs.</extracomment>
        <translation>{0} fps</translation>
    </message>
    <message>
        <location filename="../popups.py" line="253"/>
        <source>Export File!</source>
        <translation>Eksportuj plik!</translation>
    </message>
    <message>
        <location filename="../popups.py" line="297"/>
        <source>Framerate:</source>
        <translation>Klatki na sekundę:</translation>
    </message>
    <message>
        <location filename="../popups.py" line="302"/>
        <source>Color Animation:</source>
        <translation>Animacja koloru:</translation>
    </message>
    <message>
        <location filename="../popups.py" line="307"/>
        <source>Playback Speed:</source>
        <translation>Prędkość odtwarzania:</translation>
    </message>
    <message>
        <location filename="../popups.py" line="312"/>
        <source>Sprite Scale:</source>
        <translation>Skala Sprite&apos;a:</translation>
    </message>
    <message>
        <location filename="../popups.py" line="318"/>
        <source>Animation Sequence:</source>
        <extracomment>Refers to a sequence of animations to play in order.</extracomment>
        <translation>Sekwencja animacji:</translation>
    </message>
    <message>
        <location filename="../popups.py" line="323"/>
        <source>Animation:</source>
        <translation>Animacja:</translation>
    </message>
    <message>
        <location filename="../popups.py" line="328"/>
        <source>Loops:</source>
        <translation>Pętle:</translation>
    </message>
    <message>
        <location filename="../popups.py" line="488"/>
        <source>None</source>
        <extracomment>Used when a file has no color animations.</extracomment>
        <translation>Nic</translation>
    </message>
    <message>
        <location filename="../popups.py" line="513"/>
        <source>Animation {0}</source>
        <translation>Animacja {0}</translation>
    </message>
    <message>
        <location filename="../popups.py" line="515"/>
        <source>Animation {0} ({1} Loops)</source>
        <translation>Animacja {0} ({1} pętli)</translation>
    </message>
    <message>
        <location filename="../popups.py" line="734"/>
        <source>Export Successful</source>
        <extracomment>Window title.</extracomment>
        <translation>Eksport udany</translation>
    </message>
    <message>
        <location filename="../popups.py" line="735"/>
        <source>File {0} has been successfully exported!</source>
        <translation>Plik {0} został skutecznie eksportowany!</translation>
    </message>
</context>
<context>
    <name>GraphicsAnimationTimeline</name>
    <message>
        <location filename="../gui.py" line="565"/>
        <source>Show Animation Bounding Box</source>
        <translation>Pokaż pole ograniczenia animacji</translation>
    </message>
    <message>
        <location filename="../gui.py" line="668"/>
        <location filename="../gui.py" line="670"/>
        <location filename="../gui.py" line="674"/>
        <source>Sprite Part(s) Used: {0}</source>
        <translation>Częsć(i) Sprite&apos;a w użytku: {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="673"/>
        <source>No Sprite Parts Used!</source>
        <translation>Brak użytych części Sprite&apos;a!</translation>
    </message>
    <message>
        <location filename="../gui.py" line="679"/>
        <location filename="../gui.py" line="683"/>
        <source>Transformation Matrix Used: {0}</source>
        <translation>Używany Macierz Transformacji: {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="682"/>
        <source>No Transformation Matrix Used!</source>
        <translation>Brak użytego Macierza Transformacji!</translation>
    </message>
    <message>
        <location filename="../gui.py" line="688"/>
        <source>(Rotation is Inverted)</source>
        <translation>(Obrót jest odwrotny)</translation>
    </message>
    <message>
        <location filename="../gui.py" line="702"/>
        <source>X Scale: {0}</source>
        <translation>Skala X: {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="703"/>
        <source>X Shear: {0}</source>
        <translation>Ścięcie X: {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="704"/>
        <source>X Position: {1}</source>
        <translation>Pozycja X: {1}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="705"/>
        <source>Y Shear: {0}</source>
        <translation>Ścięcie Y: {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="706"/>
        <source>Y Scale: {0}</source>
        <translation>Skala Y: {0}</translation>
    </message>
    <message>
        <location filename="../gui.py" line="707"/>
        <source>Y Position: {1}</source>
        <translation>Pozycja Y: {1}</translation>
    </message>
</context>
<context>
    <name>MainWindow</name>
    <message>
        <location filename="../main.py" line="200"/>
        <source>CheckUpdateErrorTitle</source>
        <translation>Nieudana Kontrola Aktualizacji</translation>
    </message>
    <message>
        <location filename="../main.py" line="201"/>
        <source>CheckUpdateErrorBlurb</source>
        <translation>Wystąpił błąd podczas spawdzania aktualizacji:

{0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="216"/>
        <source>CheckUpdateNewVersionAssurance</source>
        <translation>Nie martw się o ustawieniach programu, one są zapisane między wersjami.</translation>
    </message>
    <message>
        <location filename="../main.py" line="218"/>
        <source>CheckUpdateNewVersionTitle</source>
        <translation>Dostępna jest nowa aktualizacja</translation>
    </message>
    <message>
        <location filename="../main.py" line="219"/>
        <source>CheckUpdateNewVersionBlurb</source>
        <translation>Dostępna jest nowa aktualizacja: {0}
---
{1}
---
Ściągnij ją na stronie {2}</translation>
    </message>
    <message>
        <location filename="../main.py" line="225"/>
        <source>CheckUpdateNewVersionRemindOption</source>
        <translation>Prypomnij mi później</translation>
    </message>
    <message>
        <location filename="../main.py" line="226"/>
        <source>CheckUpdateNewVersionIgnoreOption</source>
        <translation>Pomiń tą wersję</translation>
    </message>
    <message>
        <location filename="../main.py" line="238"/>
        <source>CheckUpdateUpToDateTitle</source>
        <translation>Nie ma nowych aktualizacji</translation>
    </message>
    <message>
        <location filename="../main.py" line="239"/>
        <source>CheckUpdateUpToDateBlurb</source>
        <translation>Już jesteś nadążony! Nie masz więcej nowych aktualizacji to ściągnięcia.</translation>
    </message>
    <message>
        <location filename="../main.py" line="257"/>
        <source>MenuBarFileTitle</source>
        <translation>&amp;Plik</translation>
    </message>
    <message>
        <location filename="../main.py" line="259"/>
        <source>MenuBarFileOpenOption</source>
        <translation>&amp;Otwórz Plik</translation>
    </message>
    <message>
        <location filename="../main.py" line="264"/>
        <source>MenuBarFileCloseOption</source>
        <translation>&amp;Zamknij Plik</translation>
    </message>
    <message>
        <location filename="../main.py" line="271"/>
        <source>MenuBarFileQuickExportOption</source>
        <translation>Szybki &amp;Eksport Animacji</translation>
    </message>
    <message>
        <location filename="../main.py" line="276"/>
        <source>MenuBarFileExportOption</source>
        <translation>Eksportuj &amp;Sekwencje Animacji</translation>
    </message>
    <message>
        <location filename="../main.py" line="283"/>
        <source>MenuBarFileQuitOption</source>
        <translation>&amp;Wyjdź</translation>
    </message>
    <message>
        <location filename="../main.py" line="289"/>
        <source>MenuBarOptionsTitle</source>
        <translation>&amp;Opcje</translation>
    </message>
    <message>
        <location filename="../main.py" line="291"/>
        <source>MenuBarOptionsLanguageOption</source>
        <translation>&amp;Język</translation>
    </message>
    <message>
        <location filename="../main.py" line="299"/>
        <source>MenuBarOptionsLanguageSystem</source>
        <translation>&lt;System Język&gt;</translation>
    </message>
    <message>
        <location filename="../main.py" line="311"/>
        <source>MenuBarOptionsFramerateOption</source>
        <translation>&amp;Framerate</translation>
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
        <translation>&amp;Wycisz Dźwięk</translation>
    </message>
    <message>
        <location filename="../main.py" line="335"/>
        <source>MenuBarOptionsCheckUpdatesOption</source>
        <translation>&amp;Automatyczne Sprawdzanie Aktualizacji</translation>
    </message>
    <message>
        <location filename="../main.py" line="340"/>
        <source>MenuBarOptionsEditThemeOption</source>
        <translation>&amp;Edytuj Motyw</translation>
    </message>
    <message>
        <location filename="../main.py" line="352"/>
        <source>MenuBarHelpTitle</source>
        <translation>Po&amp;moc</translation>
    </message>
    <message>
        <location filename="../main.py" line="355"/>
        <source>MenuBarHelpCheckUpdates</source>
        <translation>&amp;Sprawdź aktualizacje</translation>
    </message>
    <message>
        <location filename="../main.py" line="453"/>
        <source>ShowBoundingBoxToggle</source>
        <translation>Pokaż pole ograniczenia Obiektu</translation>
    </message>
    <message>
        <location filename="../main.py" line="461"/>
        <source>ColorAnimSelectorTitle</source>
        <translation>Animacje Koloru:</translation>
    </message>
    <message>
        <location filename="../main.py" line="479"/>
        <source>AnimationTabsSpriteAnimTitle</source>
        <translation>Animacje Sprite&apos;a</translation>
    </message>
    <message>
        <location filename="../main.py" line="480"/>
        <source>AnimationTabsSpriteColorAnimTitle</source>
        <translation>Pojedyncza Animacja Koloru</translation>
    </message>
    <message>
        <location filename="../main.py" line="481"/>
        <source>AnimationTabsSpriteGlobalAnimTitle</source>
        <translation>Globalna Animacja Koloru</translation>
    </message>
    <message>
        <location filename="../main.py" line="496"/>
        <source>SpritePartSetSelectorTitle</source>
        <translation>Biężący Zestaw Części Sprite&apos;a:</translation>
    </message>
    <message>
        <location filename="../main.py" line="521"/>
        <source>SpritePartSelectorTitle</source>
        <translation>Bieżąca część Sprite&apos;a:</translation>
    </message>
    <message>
        <location filename="../main.py" line="611"/>
        <source>ObjectSelectorTitle</source>
        <translation>Bieżący Obiekt:</translation>
    </message>
    <message>
        <location filename="../main.py" line="616"/>
        <source>AnimationSelectorTitle</source>
        <translation>Animacje:</translation>
    </message>
    <message>
        <location filename="../main.py" line="690"/>
        <source>ExportFailNoDataTitle</source>
        <translation>Brak Danych Obiektu</translation>
    </message>
    <message>
        <location filename="../main.py" line="691"/>
        <source>ExportFailNoDataBlurb</source>
        <translation>Nie ma żadnych aktualnie załadowanych danych Obiektu! Proszę załaduj archiwum Obiektów zanim spóbujesz eksportować plik.</translation>
    </message>
    <message>
        <location filename="../main.py" line="760"/>
        <source>GameTitleML1</source>
        <translation>Mario &amp; Luigi: Superstar Saga</translation>
    </message>
    <message>
        <location filename="../main.py" line="761"/>
        <source>GameTitleML2</source>
        <translation>Mario &amp; Luigi: Partners in Time</translation>
    </message>
    <message>
        <location filename="../main.py" line="762"/>
        <source>GameTitleML3</source>
        <translation>Mario &amp; Luigi: Bowser&apos;s Inside Story</translation>
    </message>
    <message>
        <location filename="../main.py" line="763"/>
        <source>GameTitleML4</source>
        <translation>Mario &amp; Luigi: Dream Team Bros.</translation>
    </message>
    <message>
        <location filename="../main.py" line="764"/>
        <source>GameTitleML5</source>
        <translation>Mario &amp; Luigi: Paper Jam Bros.</translation>
    </message>
    <message>
        <location filename="../main.py" line="765"/>
        <source>GameTitleML1R</source>
        <translation>Mario &amp; Luigi: Superstar Saga + Bowser&apos;s Minions</translation>
    </message>
    <message>
        <location filename="../main.py" line="766"/>
        <source>GameTitleML3R</source>
        <translation>Mario &amp; Luigi: Bowser&apos;s Inside Story + Bowser Jr.&apos;s Journey</translation>
    </message>
    <message>
        <location filename="../main.py" line="770"/>
        <source>GenericBooleanAffirmative</source>
        <translation>Prawda</translation>
    </message>
    <message>
        <location filename="../main.py" line="771"/>
        <source>GenericBooleanNegative</source>
        <translation>Fałsz</translation>
    </message>
    <message>
        <location filename="../main.py" line="772"/>
        <source>GenericDataNone</source>
        <translation>Nic</translation>
    </message>
    <message>
        <location filename="../main.py" line="834"/>
        <source>CheckUpdateQueryLinkString</source>
        <translation>Privacy Statement</translation>
    </message>
    <message>
        <location filename="../main.py" line="843"/>
        <source>CheckUpdateQueryTitle</source>
        <translation>Automatyczna Kontrola Aktualizacji</translation>
    </message>
    <message>
        <location filename="../main.py" line="844"/>
        <source>CheckUpdateQueryBlurb</source>
        <translation>Czy chciałbyś zezwolić Spritoglobin DX na automatyczne połączączenie do internetu I sprawdzanie aktualizacji?

Zawszę możesz to zmienić w opcjach.

Uwaga: Ten proces składa wniosek do serwerów Github, które dostaną i przetworzą twój adres IP według ich {0}.</translation>
    </message>
    <message>
        <location filename="../main.py" line="1006"/>
        <source>ColorModeInfo</source>
        <translation>Tryb Koloru: {0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="1345"/>
        <source>SpritePartBufferOffset</source>
        <translation>Dane Buforu Grafiki: {0}h - {1}h</translation>
    </message>
    <message>
        <location filename="../main.py" line="1352"/>
        <source>SpritePartSize0</source>
        <translation>0 (Mały)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1352"/>
        <source>SpritePartSize1</source>
        <translation>1 (Średni)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1352"/>
        <source>SpritePartSize2</source>
        <translation>2 (Duży)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1352"/>
        <source>SpritePartSize3</source>
        <translation>3 (Bardzo Duży)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1353"/>
        <source>SpritePartShape0</source>
        <translation>0 (Kwadrat)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1353"/>
        <source>SpritePartShape1</source>
        <translation>1 (Szeroki)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1353"/>
        <source>SpritePartShape2</source>
        <translation>2 (Wysoki)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1368"/>
        <source>SpritePartSizeTitle</source>
        <translation>Rozmiar: {0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="1370"/>
        <source>SpritePartShapeTitle</source>
        <translation>Kształt: {0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="1372"/>
        <source>SpritePartSizePixels</source>
        <translation>({0}px, {1}px)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1374"/>
        <source>SpritePartFlipHorizontal</source>
        <translation>Obrót Poziomy:{0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="1376"/>
        <source>SpritePartFlipVertical</source>
        <translation>Obrót Pionowy: {0}</translation>
    </message>
    <message>
        <location filename="../main.py" line="1378"/>
        <source>SpritePartOffset</source>
        <translation>Offset: ({0}px, {1}px)</translation>
    </message>
    <message>
        <location filename="../main.py" line="1398"/>
        <source>SpritePartRendererTitle</source>
        <translation>Renderer: {0}</translation>
    </message>
</context>
<context>
    <name>ProgramThemeEditor</name>
    <message>
        <location filename="../popups.py" line="758"/>
        <source>Edit Theme</source>
        <extracomment>Window title.</extracomment>
        <translation>Edytuj Motyw</translation>
    </message>
    <message>
        <location filename="../popups.py" line="784"/>
        <source>Recolor Icons According to Theme</source>
        <extracomment>Refers to whether or not the icons will be automatically recolored based on the four main theme colors the user has chosen.</extracomment>
        <translation>Zmień Kolor Ikon według Motywu</translation>
    </message>
    <message>
        <location filename="../popups.py" line="879"/>
        <source>Apply Theme!</source>
        <translation>Zastosuj Motyw!</translation>
    </message>
    <message>
        <location filename="../popups.py" line="891"/>
        <source>Theme Settings:</source>
        <translation>Ustawienia Motywu:</translation>
    </message>
    <message>
        <location filename="../popups.py" line="896"/>
        <source>Theme Presets:</source>
        <extracomment>Referring to buttons you can click to automatically set your theme to a few pre-determined colors.</extracomment>
        <translation>Ustalone Motywy:</translation>
    </message>
    <message>
        <location filename="../popups.py" line="900"/>
        <source>Preview:</source>
        <translation>Podgląd:</translation>
    </message>
</context>
</TS>
