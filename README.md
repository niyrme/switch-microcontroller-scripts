[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/niyrme/switch-microcontroller-scripts/main.svg)](https://results.pre-commit.ci/latest/github/niyrme/switch-microcontroller-scripts/main)

# switch microcontroller scripts

A repo containing my scripts running on the base of [this repository](https://github.com/asottile/switch-microcontroller)

## Requirements
- Everything from the repo linked above (buzzer is optional)
- Python 3.9 (maybe 3.8 works too)
- A capture card (to get a video signal from the Switch to the PC)


# How to use
1. Rename `sample.config.json` to `config.json`
2. Update the settings in `config.json` (if so desired)
3. Run any of the scripts as a python module: `python3 -m scripts <game> <"module"> <script>`
  - Example: `python3 -m scripts pokemon bdsp arceus`
  - for more information add the `-h` flag after any of the arguments
    - Example: `python3 -m scripts pokemon bdsp -h`

## Script list
- To see all available games run `python3 -m scripts -h`
- To see all available modules run `python3 -m scripts <module> -h`
- To see all available scripts run `python3 -m scripts <game> <module> -h`
- To see the requirements for a script to run (successfully), add the `-r`/`--requirements` flag after the script
  - Example: `python3 -m scripts pokemon bdsp arceus -r`
