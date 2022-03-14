# switch microcontroller scripts

A repo containing my scripts running on the base of [this](https://github.com/asottile/switch-microcontroller)

## Requirements
- Everything from the repo linked above (buzzer is optional)
- Python (I'm using 3.9 but 3.8+ _should_ work)
- A capture card (to get a video signal from the Switch to the PC)


# How to use
1. Rename `sample.config.json` to `config.json`
2. Update the `serialPort` in `config.json` to the desired serial port
3. Run any of the `.py` files with python.
	- add `-h` or `--help` as an argument to get a bit more info about each file (example: `python3 gen4_pixie_reset.py --help`)


# Script list

## General Pokémon
- `shiny_grind.py` for running around up-down or left-right

## Pokémon Brilliant Diamon/Shining Pearl
- `gen4_pixie_reset.py` for resetting 2 of the 3 pixies (Uxie and Azelf)
	- not Mesprit because it roams around the map
- `gen4_legendary_reset` for Dialga/Palkia
- `gen4_starter_reset.py` for resetting the starter pokemon
