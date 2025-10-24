
import os
import difflib
from pathlib import Path
import filecmp

import hashlib



def calculate_full_hash(file_path):
    """Вычисляет полную MD5 хеш-сумму файла"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except (IOError, OSError):
        return None

def get_file_info(file_path):
    """Получает информацию о файле: размер, время модификации и быструю контрольную сумму"""
    stat = file_path.stat()
    file_info = {
        'size': stat.st_size,
        'mtime': stat.st_mtime,
        'path': file_path
    }
        
    # Для быстрого сравнения используем первые 4KB файла + размер
    #quick_hash = None
    #try:
    #    with open(file_path, 'rb') as f:
    #        # Читаем первые 4KB для быстрого хеширования
    #        chunk = f.read(4096)
    #        if chunk:
    #            # Создаем быстрый хеш из первых 4KB + размера файла
    #            quick_hash = hashlib.md5(chunk + str(stat.st_size).encode()).hexdigest()
    #except (IOError, OSError):
    #    pass
    #
    #file_info['quick_hash'] = quick_hash
    return file_info


def compare_directories(dir1, dir2, output_dir):
    
    dir1 = Path(dir1)
    dir2 = Path(dir2)
    output_dir = Path(output_dir)
    
    # Создаем выходной каталог
    output_dir.mkdir(exist_ok=True)
    
    # Получаем список всех файлов
    files1 = {f.relative_to(dir1) for f in dir1.rglob('*.bsl') if f.is_file()}
    files2 = {f.relative_to(dir2) for f in dir2.rglob('*.bsl') if f.is_file()}

    all_files = files1 & files2

    for file_rel in all_files:
        # err full path!!!
        file1 = dir1 / file_rel
        file2 = dir2 / file_rel
        output_file = output_dir / file_rel

        #output_file.parent.mkdir(parents=True, exist_ok=True)

        compare_files(file1, file2, output_file)

def compare_files(file1, file2, output_file):
    try:
        # Проверяем существование файлов
        exists1 = file1.exists()
        exists2 = file2.exists()

        if not exists1 or not exists2:
            return
        with open(file1, 'r', encoding='utf-8') as f1:
            lines1 = f1.readlines()
        with open(file2, 'r', encoding='utf-8') as f2:
            lines2 = f2.readlines()
        
    except Exception as e:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Ошибка при сравнении: {str(e)}\n")

def compare_code_blocks(file1, file2, output_file):
    return

def main():
    dir1 = "D:\\Progr\\test\\cmp\\base"
    dir2 = "D:\\Progr\\test\\cmp\\2nd" 
    output_dir = "D:\\Progr\\test\\cmp\\rez"
    
    compare_directories(dir1, dir2, output_dir)
    print(f"Сравнение завершено. Результаты в {output_dir}")

if __name__ == "__main__":
    main()