# Dividends FURS

This is a Python script that calculates the tax on dividends according to the regulations of the Financial Administration of the Republic of Slovenia (FURS).
Currently only `xlsx` exports from Saxo Bank are supported.

## Prerequisites

- Python 3.x

## Installation

1. Clone the repository or download the .zip archive of the code
2. Run `make bootstrap`

## Usage

1. Navigate to the directory where the `dividends_furs.py` file is located in your terminal
2. Run the script using the following command:

  ```shell
  python3 dividends_furs.py <dividends.xlsx> --additional-info <additional_info.xlsx> --taxpayer <taxpayer.xml> --output <doh_div.xml>
  ```

## Description of options

- `<dividends.xlsx>`: This is the input file containing the dividends data. Replace `<dividends.xlsx>` with the actual path or name of your dividends file. For example, `python3 dividends_furs.py dividends_data.xlsx`.

- `--additional-info <additional_info.xlsx>`: This option is used to provide additional information related to the dividends (like ISIN numbers). Replace `<additional_info.xlsx>` with the actual path or name of your additional info file. For example, `--additional-info info.xlsx`.

- `--taxpayer <taxpayer.xml>`: This option specifies the taxpayer information file in XML format. Replace `<taxpayer.xml>` with the actual path or name of your taxpayer file. For example, `--taxpayer taxpayer_info.xml`. You can see an example in `taxpayer_fake.xml`.

- `--output <doh_div.xml>`: This option determines the output file name for the calculated tax data in XML format. Replace `<doh_div.xml>` with the desired name of your output file. For example, `--output tax_data.xml`.

## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
