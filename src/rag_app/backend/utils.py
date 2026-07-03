from pathlib import Path


def is_text_file(file_path: Path | str) -> bool:
    """Function to check if file is a text or binary file - not 100% reliable"""

    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)

        if not chunk:
            return True

        # if the file contains null byte - it is binary
        if b"\x00" in chunk:
            return False

        text = chunk.decode("utf-8", errors="ignore")

        text_chars = sum(1 for char in text if char.isprintable() or char in "\n\r\t")

        text_binary_ratio = text_chars / len(chunk)

        # check if at least 85% of the file is text
        return text_binary_ratio > 0.85

    except FileNotFoundError:
        return False
