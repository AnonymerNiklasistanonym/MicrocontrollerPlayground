import os


def append_to_csv(file_path, header, rows, seperator=',', file_path_prefix="/"):
    """
    Appends a row to a CSV file. If the file doesn't exist, creates it and writes the header.
    
    Args:
        file_path (str): Path to the CSV file.
        header (list): A list of column names to be used as a header.
        rows (list of lists): A list of list of values to be added as rows.
    """
    file_exists = False
    
    try:
        file_exists = file_path in os.listdir(file_path_prefix)
    except OSError:
        pass

    mode = 'a' if file_exists else 'w'
    
    with open(f"{file_path_prefix}/{file_path}", mode) as csv_file:
        if not file_exists:
            csv_file.write(seperator.join(header) + '\n')
        for row in rows:
            csv_file.write(seperator.join(map(str, row)) + '\n')