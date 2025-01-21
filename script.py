import os

def collect_files(directories, output_file):
    """
    Collect .py and .html files only from the given directories (not subdirectories)
    and write their contents to a single .txt file.

    :param directories: A list of directories to search in.
    :param output_file: The file where the collected content will be saved.
    """
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for directory in directories:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and (file.endswith('.py') or file.endswith('.html')):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(f"\n{'-'*40}\nFile: {file_path}\n{'-'*40}\n")
                            outfile.write(infile.read())
                            outfile.write("\n")
                    except Exception as e:
                        print(f"Could not read file {file_path}: {e}")

if __name__ == "__main__":
    # Specify the directories for .py and .html files
    python_files_directory = "D:\\programing Base\\Retail_Cosmo-main\\Retail_Cosmo-main"
    html_files_directory = "D:\\programing Base\\Retail_Cosmo-main\\Retail_Cosmo-main\\templates"

    # Output file to store the collected content
    output_txt_file = "collected_files.txt"

    # Call the function with both directories
    collect_files(
        directories=[python_files_directory, html_files_directory],
        output_file=output_txt_file
    )

    print(f"Collected contents of .py and .html files into {output_txt_file}")
