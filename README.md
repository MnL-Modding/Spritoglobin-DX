# Spritoglobin DX
Spritoglobin DX is a sprite viewer for Mario and Luigi: Bowser's Inside Story + Bowser Jr.'s Journey, as well as a growing list of other Mario & Luigi titles.

![Screenshot of Spritoglobin DX v0.1.0 prerelease](docs/0.1.0pre.png)

# Credits
[ThePurpleAnon](https://bsky.app/profile/thepurpleanon.bsky.social) ![Bluesky](spritoglobin_dx/files/img_soc_bsky.png) - Python Code, UI Design, and Program Sounds

[DimiDimit](https://github.com/DimiDimit) ![Github](spritoglobin_dx/files/img_soc_github.png) - Additional Python Code and Cleanup

[MiiK](https://bsky.app/profile/miikheaven.bsky.social) ![Bluesky](spritoglobin_dx/files/img_soc_bsky.png) - Spritoglobin DX Icon and Program UI Icons

[8y8x](https://github.com/8y8x) ![Github](spritoglobin_dx/files/img_soc_github.png) - Assistance with 3D Renderer Code

Translators:
- Español (ES) ![es_ES Flag](spritoglobin_dx/lang/es_ES.png) - [Danius](https://github.com/Dani88alv) ![Github](spritoglobin_dx/files/img_soc_github.png)
- Français (FR) ![fr_FR Flag](spritoglobin_dx/lang/fr_FR.png) - [Yo-New 3DS](## "Discord: yo_2ds") ![Discord](spritoglobin_dx/files/img_soc_discord.png)
- Português ![pt_PT Flag](spritoglobin_dx/lang/pt_PT.png) - [Shaino](https://www.instagram.com/im__shine_o?igsh=Mjl3YmZlaWswaW5x) ![Instagram](spritoglobin_dx/files/img_soc_instagram.png)

# Running the Program
There are 4 ways to run this program, from easiest to most complicated:

1. Download the binary from [Releases](https://github.com/MnL-Modding/Spritoglobin-DX/releases) and run it. (Use the `.exe` for Windows, and the `.bin` for Linux)

2. Install the package with
```bash
python3 -m pip install --force-reinstall git+https://github.com/MnL-Modding/Spritoglobin-DX
```
and run it with `spritoglobin_dx` or `python3 -m spritoglobin_dx`.

3. Clone the repository, install the dependencies with Poetry (assuming you already have Poetry installed with `python3 -m pip install poetry`):
```bash
poetry install
```
and run the program through Poetry:
```bash
poetry run spritoglobin-dx
```

4. Clone the repository, install the dependencies through `pip` with:
```bash
python3 -m pip install -r requirements.txt
```
and run it from the current directory with `python3 -m spritoglobin_dx`. Alternatively, it can be run through the `run.bat` if you use Windows.
