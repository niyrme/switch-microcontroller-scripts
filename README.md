[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/niyrme/switch-microcontroller-scripts/main.svg)](https://results.pre-commit.ci/latest/github/niyrme/switch-microcontroller-scripts/main)

# switch microcontroller scripts

A repo containing my scripts running on the base of [this](https://github.com/asottile/switch-microcontroller)

## Requirements
- Everything from the repo linked above (buzzer is optional)
- Python (I'm using 3.9, but 3.8+ _should_ work)
- A capture card (to get a video signal from the Switch to the PC)


# How to use
1. Rename `sample.config.json` to `config.json`
2. Update the `serialPort` in `config.json` to the desired serial port
3. Run any of the scripts as python modules: `python3 -m gen4`
	- add `-h` or `--help` as an argument to get a bit more info about each file (example: `python3 -m gen4 --help`)


# Script list

## Pokémon Brilliant Diamon/Shining Pearl
Run as `python3 -m gen4 <script>` (or add `-h`/`--help` flag for more info)
- `cresselia` for Cresselia [WIP]
- `legendary` for Dialga/Palkia
- `pixie` for Uxie and Azelf
	- not Mesprit because it roams around the map
- `random` for random encounters in orthogonal directions
- `shaymin` for Shaymin
- `starter` for a starter
