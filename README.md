# FURS Taxes

This is a Python script that calculates the tax on dividends, interest and gains according to the regulations of the Financial Administration of the Republic of Slovenia (FURS).
Currently only `xlsx` exports from Saxo Bank are supported.

## Prerequisites

- Python 3.x

## Installation

1. Clone the repository or download the .zip archive of the code
2. Install the dependencies using `pip install -r requirements.txt`

## Usage

1. Navigate to the directory where the `taxes.py` file is located in your terminal
2. Run the script using the following command:

```shell
usage: taxes.py [-h] (--saxo-dividends SAXO_DIVIDENDS | --saxo-gains SAXO_GAINS | --saxo-interest SAXO_INTEREST) [--period PERIOD]
                [--additional-info ADDITIONAL_INFO] [--output OUTPUT] [--correction] [--taxpayer TAXPAYER]
```

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
