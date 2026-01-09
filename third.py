"""
Сравнивает файлы в текущей папке с GitHub репозиторием.
Показывает какие файлы есть только в одном месте и разницу в содержимом.
"""

import os
import difflib
import requests
import tempfile
import subprocess
import shutil

def get_github_files(repo_url):
    """Получает файлы с GitHub"""
    if not repo_url.startswith(('http://', 'https://')):
        repo_url = f'https://github.com/{repo_url}.git'  # убраны пробелы

    temp_dir = tempfile.mkdtemp()
    try:
        subprocess.run(['git', 'clone', '--depth', '1', repo_url, temp_dir],
                      check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка клонирования: {e}")
        return {}

    files = {}
    for root, _, filenames in os.walk(temp_dir):
        if '.git' in root:
            continue
        for f in filenames:
            path = os.path.join(root, f)
            rel = os.path.relpath(path, temp_dir)
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    files[rel] = file.read()
            except (UnicodeDecodeError, OSError):
                files[rel] = 'BINARY'

    # Удаляем временную папку — КРОССПЛАТФОРМЕННО
    shutil.rmtree(temp_dir, ignore_errors=True)
    return files

def get_local_files():
    """Получает файлы из текущей папки"""
    files = {}
    for root, _, filenames in os.walk('.'):
        if '.git' in root:
            continue
        for f in filenames:
            path = os.path.join(root, f)
            rel = os.path.relpath(path, '.')
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    files[rel] = file.read()
            except:
                files[rel] = 'BINARY'
    return files

def compare_files(local, github):
    """Сравнивает два набора файлов"""
    print("СРАВНЕНИЕ:")
    print("=" * 60)
    
    # Файлы только на GitHub
    only_github = set(github.keys()) - set(local.keys())
    if only_github:
        print("\nТОЛЬКО НА GITHUB:")
        for f in sorted(only_github)[:5]:
            print(f"  + {f}")
        if len(only_github) > 5:
            print(f"  ... и еще {len(only_github)-5} файлов")
    
    # Файлы только локально
    only_local = set(local.keys()) - set(github.keys())
    if only_local:
        print("\nТОЛЬКО ЛОКАЛЬНО:")
        for f in sorted(only_local)[:5]:
            print(f"  - {f}")
        if len(only_local) > 5:
            print(f"  ... и еще {len(only_local)-5} файлов")
    
    # Общие файлы
    common = set(local.keys()) & set(github.keys())
    
    print(f"\nОБЩАЯ СТАТИСТИКА:")
    print(f"  Файлов на GitHub: {len(github)}")
    print(f"  Файлов локально: {len(local)}")
    print(f"  Общих файлов: {len(common)}")
    
    # Сравниваем содержимое общих файлов
    different = []
    for f in common:
        if local[f] != github[f]:
            different.append(f)
    
    if different:
        print(f"\nИЗМЕНЕННЫЕ ФАЙЛЫ:")
        for f in sorted(different)[:3]:  # Показываем только 3 файла
            print(f"\n{f}:")
            if local[f] == 'BINARY' or github[f] == 'BINARY':
                print("  [бинарный файл]")
            else:
                # Показываем разницу
                diff = difflib.unified_diff(
                    local[f].splitlines(keepends=True),
                    github[f].splitlines(keepends=True),
                    fromfile='локально',
                    tofile='GitHub'
                )
                lines = list(diff)
                if len(lines) > 20:  # Ограничиваем вывод
                    lines = lines[:20]
                    lines.append("... [еще изменения скрыты] ...\n")
                for line in lines:
                    if line.startswith('---') or line.startswith('+++'):
                        continue
                    print(f"  {line.rstrip()}")
        
        if len(different) > 3:
            print(f"\n... и еще {len(different)-3} измененных файлов")

def main():
    """Основная функция"""
    import sys
    
    print("СРАВНЕНИЕ С GITHUB")
    print("=" * 60)
    
    # Получаем репозиторий
    if len(sys.argv) > 1:
        repo = sys.argv[1]
    else:
        repo = input("Введите GitHub репозиторий (user/repo): ").strip()
        if not repo:
            print("Не указан репозиторий")
            return
    
    # Добавляем .git если нужно
    if not repo.endswith('.git'):
        repo = f'https://github.com/{repo}.git'
    
    # Получаем файлы
    print("Получаю файлы с GitHub...")
    github_files = get_github_files(repo)
    
    print("Читаю локальные файлы...")
    local_files = get_local_files()
    
    # Сравниваем
    compare_files(local_files, github_files)
    
    print("\nСравнение завершено!")

if __name__ == "__main__":
    # cd /ваш/проект
    # python github_compare.py username/repository
    # python github_compare.py
    main()