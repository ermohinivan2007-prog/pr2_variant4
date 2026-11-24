"""Утилита командной строки для вычисления SHA-256 хеш-сумм файлов."""
import argparse
import hashlib
import json
import os
import sys

READ_CHUNK_SIZE = 65536
DEFAULT_OUTPUT = "result.json"
EXIT_ERROR = 1


def calculate_sha256(file_path: str) -> str:
    """Вычисляет SHA-256 хеш файла."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for byte_block in iter(lambda: file.read(READ_CHUNK_SIZE), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def process_file(input_path: str, output_path: str) -> None:
    """Обрабатывает файл и сохраняет результат в JSON."""
    try:
        file_size = os.path.getsize(input_path)
        file_hash = calculate_sha256(input_path)
    except FileNotFoundError:
        print(f"Ошибка: Файл {input_path} не найден.", file=sys.stderr)
        sys.exit(EXIT_ERROR)
    except PermissionError:
        print(f"Ошибка: Нет прав на чтение {input_path}.", file=sys.stderr)
        sys.exit(EXIT_ERROR)

    result = {
        "file_name": os.path.basename(input_path),
        "file_size_bytes": file_size,
        "sha256": file_hash
    }

    with open(output_path, "w", encoding="utf-8") as out_file:
        json.dump(result, out_file, ensure_ascii=False, indent=4)

    print(f"Успешно. Хеш сохранен в {output_path}")


def main() -> None:
    """Точка входа для утилиты командной строки."""
    parser = argparse.ArgumentParser(
        description="Вычисление SHA-256 хеш-суммы файла."
    )
    parser.add_argument("input", help="Путь к входному файлу")
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT,
        help=f"Путь к выходному JSON (по умолчанию {DEFAULT_OUTPUT})"
    )
    args = parser.parse_args()
    process_file(args.input, args.output)


if __name__ == "__main__":
    main()
