"""
Скрипт для массового переименования файлов по заданному шаблону.
Решает проблему ручного переименования множества файлов по шаблону.
Поддерживает поиск по регулярным выражениям, нумерацию и добавление префиксов/суффиксов.
"""

import os
import re
import argparse
from pathlib import Path
from datetime import datetime
import logging

def rename_files_by_pattern(directory, pattern, replacement, 
                          prefix="", suffix="", start_number=1,
                          dry_run=False, recursive=False):
    """
    Переименовывает файлы по регулярному выражению
    
    Args:
        directory (str): Директория с файлами
        pattern (str): Регулярное выражение для поиска
        replacement (str): Строка для замены
        prefix (str): Префикс для нового имени
        suffix (str): Суффикс для нового имени (до расширения)
        start_number (int): Начальный номер для нумерации
        dry_run (bool): Пробный запуск без изменений
        recursive (bool): Рекурсивный поиск в поддиректориях
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Директория не существует: {directory}")
        return
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        filename='rename_log.txt'
    )
    
    # Собираем все файлы
    if recursive:
        file_list = list(dir_path.rglob('*'))
    else:
        file_list = list(dir_path.glob('*'))
    
    # Фильтруем только файлы (не директории)
    files = [f for f in file_list if f.is_file()]
    
    if not files:
        print(f"⚠ Файлы не найдены в директории: {directory}")
        return
    
    print(f"Найдено файлов для обработки: {len(files)}")
    print(f"Шаблон поиска: '{pattern}' → Замена: '{replacement}'")
    print(f"Префикс: '{prefix}', Суффикс: '{suffix}', Начальный номер: {start_number}")
    print("-" * 60)
    
    renamed_count = 0
    numbered_count = 0
    
    for idx, file_path in enumerate(sorted(files), start=start_number):
        # Получаем имя файла и расширение
        name = file_path.name
        stem = file_path.stem
        extension = file_path.suffix
        
        # Применяем регулярное выражение
        new_stem = re.sub(pattern, replacement, stem)
        
        # Добавляем префикс и суффикс
        new_stem = f"{prefix}{new_stem}{suffix}"
        
        # Если нужно нумеровать
        if prefix == "" and suffix == "" and new_stem == stem:
            new_stem = f"{new_stem}_{idx}"
            numbered_count += 1
        
        # Формируем новое имя
        new_name = f"{new_stem}{extension}"
        new_path = file_path.parent / new_name
        
        # Проверяем, не существует ли файл с таким именем
        if new_path.exists():
            # Генерируем уникальное имя
            counter = 1
            while new_path.exists():
                new_name = f"{new_stem}_{counter}{extension}"
                new_path = file_path.parent / new_name
                counter += 1
        
        # Переименовываем или выводим информацию
        if file_path != new_path:
            if dry_run:
                print(f"[ПРОБНЫЙ] {name} → {new_name}")
            else:
                try:
                    file_path.rename(new_path)
                    print(f"✓ {name} → {new_name}")
                    logging.info(f"Переименован: {name} → {new_name}")
                    renamed_count += 1
                except Exception as e:
                    print(f"Ошибка при переименовании {name}: {e}")
                    logging.error(f"Ошибка: {name} → {e}")
    
    # Выводим отчет
    print("\n" + "=" * 60)
    print("ОТЧЕТ О ПЕРЕИМЕНОВАНИИ:")
    print(f"Всего файлов обработано: {len(files)}")
    print(f"Переименовано файлов: {renamed_count}")
    print(f"Добавлена нумерация: {numbered_count}")
    
    if dry_run:
        print("\n⚠ Это был пробный запуск. Файлы не были изменены.")
        print("Для реального переименования запустите скрипт без флага --dry-run")

def batch_rename_with_template(directory, template, start_number=1, dry_run=False):
    """
    Переименовывает файлы по шаблону с нумерацией
    Пример шаблона: "photo_##.jpg" или "document_###"
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Директория не существует: {directory}")
        return
    
    files = sorted([f for f in dir_path.glob('*') if f.is_file()])
    
    if not files:
        print("Файлы не найдены")
        return
    
    # Находим символы для нумерации в шаблоне
    if '#' in template:
        # Определяем количество символов для нумерации
        num_hashes = template.count('#')
        
        for i, file_path in enumerate(files, start=start_number):
            # Форматируем номер с ведущими нулями
            number_str = str(i).zfill(num_hashes)
            
            # Заменяем ### на номер
            new_name = template.replace('#' * num_hashes, number_str)
            
            # Сохраняем расширение оригинального файла
            if '.' not in new_name:
                new_name = f"{new_name}{file_path.suffix}"
            
            new_path = file_path.parent / new_name
            
            if dry_run:
                print(f"[ПРОБНЫЙ] {file_path.name} → {new_name}")
            else:
                try:
                    file_path.rename(new_path)
                    print(f"✓ {file_path.name} → {new_name}")
                except Exception as e:
                    print(f"Ошибка: {file_path.name} → {e}")

def main():
    parser = argparse.ArgumentParser(description='Утилита для массового переименования файлов')
    
    subparsers = parser.add_subparsers(dest='command', help='Команда')
    
    # Парсер для переименования по регулярному выражению
    parser_regex = subparsers.add_parser('regex', help='Переименование по регулярному выражению')
    parser_regex.add_argument('directory', help='Директория с файлами')
    parser_regex.add_argument('pattern', help='Регулярное выражение для поиска')
    parser_regex.add_argument('replacement', help='Строка для замены')
    parser_regex.add_argument('--prefix', default='', help='Префикс для нового имени')
    parser_regex.add_argument('--suffix', default='', help='Суффикс для нового имени')
    parser_regex.add_argument('--start', type=int, default=1, help='Начальный номер')
    parser_regex.add_argument('--dry-run', action='store_true', help='Пробный запуск')
    parser_regex.add_argument('--recursive', '-r', action='store_true', help='Рекурсивный поиск')
    
    # Парсер для переименования по шаблону
    parser_template = subparsers.add_parser('template', help='Переименование по шаблону с нумерацией')
    parser_template.add_argument('directory', help='Директория с файлами')
    parser_template.add_argument('template', help='Шаблон имени (например: photo_##.jpg)')
    parser_template.add_argument('--start', type=int, default=1, help='Начальный номер')
    parser_template.add_argument('--dry-run', action='store_true', help='Пробный запуск')
    
    args = parser.parse_args()
    
    if args.command == 'regex':
        rename_files_by_pattern(
            directory=args.directory,
            pattern=args.pattern,
            replacement=args.replacement,
            prefix=args.prefix,
            suffix=args.suffix,
            start_number=args.start,
            dry_run=args.dry_run,
            recursive=args.recursive
        )
    elif args.command == 'template':
        batch_rename_with_template(
            directory=args.directory,
            template=args.template,
            start_number=args.start,
            dry_run=args.dry_run
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    # 1. Удалить "IMG_" из всех имен файлов:
    # python3 second.py regex ./photos "IMG_" "" --dry-run
    # 2. Добавить префикс "vacation_" ко всем jpg файлам:
    # python3 second.py regex ./photos ".*" "$0" --prefix "vacation_" --recursive
    # 3. Переименовать по шаблону с нумерацией:
    # python3 second.py template ./photos "photo_##.jpg"
    # 4. Заменить пробелы на подчеркивания:
    # python3 second.py regex ./docs "\s+" "_"
    main()