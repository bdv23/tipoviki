"""
Скрипт для автоматического создания резервных копий файлов.
Создает zip-архив с указанными файлами/директориями,
сохраняет с датой в имени и удаляет старые бэкапы.
"""
import zipfile
import os
from pathlib import Path
from datetime import datetime, timedelta
import logging
import argparse

def create_backup(sources, backup_dir, backup_name=None):
    """
    Создает резервную копию указанных файлов/директорий 
    Args:
        sources (list): Список путей для бэкапа
        backup_dir (str): Директория для сохранения бэкапов
        backup_name (str): Базовое имя для архива
    """
    # Создаем директорию для бэкапов, если не существует
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    # Генерируем имя файла с timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if not backup_name:
        backup_name = 'backup'
    archive_name = f"{backup_name}_{timestamp}.zip"
    archive_path = backup_path / archive_name
    # Создаем zip-архив
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for source in sources:
            source_path = Path(source)
            if not source_path.exists():
                print(f"Предупреждение: {source} не существует. Пропускаем.")
                continue
            if source_path.is_file():
                # Добавляем файл
                zipf.write(source_path, source_path.name)
                print(f"Добавлен файл: {source_path}")
            elif source_path.is_dir():
                # Рекурсивно добавляем директорию
                for file_path in source_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source_path.parent)
                        zipf.write(file_path, arcname)
                        print(f"Добавлен: {file_path}")
    # Получаем информацию о созданном архиве
    archive_size = archive_path.stat().st_size / (1024 * 1024)  # в MB
    report = f"""
    Бэкап успешно создан!
    Архив: {archive_path}
    Размер: {archive_size:.2f} MB
    Включено элементов: {len(sources)}
    """
    print(report)
    return archive_path
def cleanup_old_backups(backup_dir, keep_days=30):
    """
    Удаляет старые бэкапы, оставляя только последние N дней
    Args:
        backup_dir (str): Директория с бэкапами
        keep_days (int): Сколько дней хранить бэкапы
    """
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    deleted_count = 0
    for backup_file in backup_path.glob('*.zip'):
        # Получаем дату создания файла
        file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
        if file_time < cutoff_date:
            try:
                file_size = backup_file.stat().st_size / (1024 * 1024)
                backup_file.unlink()
                deleted_count += 1
                print(f"Удален старый бэкап: {backup_file.name} ({file_size:.2f} MB)")
            except Exception as e:
                print(f"Ошибка при удалении {backup_file}: {e}")
    if deleted_count > 0:
        print(f"Удалено старых бэкапов: {deleted_count}")

def list_backups(backup_dir):
    """
    Выводит список доступных бэкапов
    """
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        print("Директория с бэкапами не найдена.")
        return
    backups = list(backup_path.glob('*.zip'))
    if not backups:
        print("Бэкапы не найдены.")
        return
    print(f"\nДоступные бэкапы в {backup_dir}:")
    print("-" * 80)
    for backup in sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True):
        file_time = datetime.fromtimestamp(backup.stat().st_mtime)
        file_size = backup.stat().st_size / (1024 * 1024)
        age_days = (datetime.now() - file_time).days
        age_info = f"{age_days} дней назад"
        if age_days == 0:
            age_info = "сегодня"
        elif age_days == 1:
            age_info = "вчера"
        print(f"{backup.name}")
        print(f"  Размер: {file_size:.2f} MB | Создан: {file_time.strftime('%Y-%m-%d %H:%M')} ({age_info})")
        print()

def main():
    """Основная функция с обработкой аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Утилита для создания резервных копий')
    parser.add_argument('action', choices=['create', 'list', 'cleanup'], help='Действие: create, list или cleanup')
    parser.add_argument('--sources', nargs='+', help='Файлы/директории для бэкапа (только для create)')
    parser.add_argument('--backup-dir', default='C:\\Users\\danil\\backups', help='Директория для хранения бэкапов')
    parser.add_argument('--name', default='backup', help='Имя для архива')
    parser.add_argument('--keep-days', type=int, default=30, help='Сколько дней хранить бэкапы (для cleanup)')
    args = parser.parse_args()
    if args.action == 'create':
        if not args.sources:
            print("Ошибка: необходимо указать файлы для бэкапа (--sources)")
            return
        print(f"Создание бэкапа для: {args.sources}")
        archive_path = create_backup(
            args.sources,
            args.backup_dir,
            args.name
        )
        print(f"Бэкап создан: {archive_path}")
    elif args.action == 'list':
        list_backups(args.backup_dir)
    elif args.action == 'cleanup':
        print(f"Очистка старых бэкапов (старше {args.keep_days} дней)...")
        cleanup_old_backups(args.backup_dir, args.keep_days)
        print("Очистка завершена")

if __name__ == "__main__":
    # 1. Создать бэкап важных файлов:
    # python first.py create --sources C:\Users\danil\Documents C:\Users\danil\Pictures --backup-dir C:\Users\danil\backups --name my_backup1
    # 2. Показать список бэкапов:
    # python first.py list --backup-dir C:\Users\danil\backups
    # 3. Очистить старые бэкапы:
    # python first.py cleanup --backup-dir C:\Users\danil\backups --keep-days 7
    main()