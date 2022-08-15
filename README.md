[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/niyrme/switch-microcontroller-scripts/main.svg)](https://results.pre-commit.ci/latest/github/niyrme/switch-microcontroller-scripts/main)

# switch microcontroller scripts

A repo containing my scripts running on the base of [this](https://github.com/asottile/switch-microcontroller)

## Requirements
- Everything from the repo linked above (buzzer is optional)
- Python (I'm using 3.9; maybe older ones work as well, but don't complain if they don't)
- A capture card (to get a video signal from the Switch to the PC)


# How to use
1. Rename `sample.config.json` to `config.json`
2. Update the settings in `config.json` (if so desired)
3. Run any of the packages as python modules: `python3 -m pokemon.bdsp`
	- add `-h` or `--help` as an argument to get a bit more info about each script (example: `python3 -m pokemon.bdsp --help <script>`)


# Script list

## Pokémon Brilliant Diamon/Shining Pearl
Run as `python3 -m pokemon.bdsp <script>` (or add `-h`/`--help` flag for more info)
- `arceus` for Arceus
  - Requirements:
    - Stand at the last step before the platform
- `cresselia` for Cresselia
   - Requirements:
      - Stand in front of cresselia
      - Map app active in poketch
      - Repel in first slot in bag
      - First pokemon in party Level < 50 but > 10 (so that only cresselia will encounter with repel)
      - X menu:
         - Map tile position: Row 2 Col 1
         - Bag tile position: Row 1 Col 3
- `darkrai` for Darkrai
   - Requirements:
     - Stand in front of Darkrai
- `giratina` for Giratina
  - Requirements:
    - Stand in front of Giratina
- `heatran` for Heatran
  - Requirements:
    - Stand in front of Heatran
- `legendary` for Dialga/Palkia
   - Requirements:
     - Stand in front of Legendary
- `pixie` for Uxie and Azelf
   - not Mesprit because it roams around the map
   - Requirements:
     - Stand in front of Pixie
- `random` for random encounters in orthogonal directions
- `regigigas` for Regigigas
  - Reqiremens:
    - Stand in front of Regigigas
- `shaymin` for Shaymin
   - Requirements:
     - Stand in front of Shaymin
- `starter` for a starter
   - Requirements:
     - Stand in front of Transition into Lake Verity

# Contribute
Additions to `lib/pokemon/langs` is welcome. But please try to keep special symbols out of the names (like ♀/♂ from Nidoran)

# v2

## How to use
1. Rename `sample.config.json` to `config.json`
2. Update the settings in `config.json` (if so desired)
3. Run any of the scripts as a python module: `python3 -m v2 <game> <"module"> <script>`
  - Example: `python3 -m v2 pokemon bdsp arceus`
  - for more information add the `-h` flag after any of the arguments (doesn't quite work after `script`)
    - Example: `python3 -m v2 pokemon bdsp -h`

## Script list
- To see all available games run `python3 -m v2 -h`
- To see all available modules run `python3 -m v2 <module> -h`
- To see all available scripts run `python3 -m v2 <game> <module> -h`
