import requests
import zipfile
import io, os, config
import logging, sys
import pandas as pd

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  
handler = logging.StreamHandler()  
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_INPUT_FILE_PATH = os.path.join(_MODULE_DIR, "input_files")

def download_files(urls, excel_file, output_path):
    """Downloads zip files from URLs, unzips them, and copies an Excel file to the output path.

    Args:
        urls: A list of URLs of zip files.
        excel_file: The path to the Excel file.
        output_path: The directory where all files will be saved.
    """
    try:
        os.makedirs(output_path, exist_ok=True)  

        for url in urls:
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()

                with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                    for file_info in zip_file.infolist():
                        file_name = os.path.basename(file_info.filename)
                        if not file_name or ("components-change" in file_name or "population-by-broad-age-group" in file_name):
                            continue
                        file_path = os.path.join(output_path, file_name)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with zip_file.open(file_info) as source, open(file_path, "wb") as target:
                            target.write(source.read())

                logger.info(f"Zip file from {url} downloaded and unzipped.")

            except requests.exceptions.RequestException as e:
                logger.fatal(f"Error downloading {url}: {e}")
            except zipfile.BadZipFile as e:
                logger.fatal(f"Error: Invalid zip file from {url}: {e}")
            except Exception as e:
                logger.fatal(f"An unexpected error occurred processing {url}: {e}")

        try:
            df = pd.read_excel(excel_file)
            processed_df = process_excel_data(df)
            new_excel_path = os.path.join(output_path, os.path.basename(excel_file))
            if processed_df is not None:
                processed_df.to_excel(new_excel_path, index=False)
            logger.info(f"Excel file copied to: {new_excel_path}")
        except FileNotFoundError:
            logger.fatal(f"Error: Excel file not found at: {excel_file}")
        except Exception as e:
            logger.fatal(f"Error processing Excel file: {e}")

        logger.info("File processing complete.")

    except Exception as e:
        logger.fatal(f"A general error occurred: {e}")  


def process_excel_data(df):
    """
    Processes an Excel file to combine values based on single-column prefix rows.

    Args:
        df: The DataFrame to be processed.

    Returns:
        A pandas DataFrame with the processed data.
    """

    result = []
    current_prefix = None

    for index, row in df.iterrows():
        row_values = row.tolist()
        if pd.isna(row_values[1]) and pd.isna(row_values[2]) and pd.isna(row_values[3]) and not pd.isna(row_values[0]):
            current_prefix = row_values[0]
            result.append(row_values)
        elif current_prefix is not None:
            new_row = [f"{current_prefix}:{row_values[0]}"] + row_values[1:]
            result.append(new_row)
        else:
            result.append(row_values)

    return pd.DataFrame(result)


if __name__ == "__main__":  
    download_files(config.urls, config.excel_file, _INPUT_FILE_PATH)
