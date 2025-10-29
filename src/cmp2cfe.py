
import os
import argparse

from pathlib import Path

from include.bsl_cmp import bsl_match

import difflib

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


def compare_directories(dir1, dir2, output_dir, r_prefix):
    
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

        compare_files(file1, file2, output_file, r_prefix)

def find_last_tp_block(diff_blocks, tp, cur_l_pos):
    
    for ind in range(len(diff_blocks)-1, max(len(diff_blocks)-3, -1), -1):
        diff_blk = diff_blocks[ind]
        blok_tp = diff_blk['tp']
        if blok_tp != '- ' and blok_tp != '+ ':
            return None
        if blok_tp == tp:
            if cur_l_pos == diff_blk['l_pos']:
                return diff_blk['block']
            else:
                return None
    return None
    

def new_diff_text(diff_blk, differ, prefix):
    block1 = diff_blk['b1']
    block2 = diff_blk['b2']

    diff_text = []
    if diff_blk['type'] == 'f':
        if block1[0] != block2[0]:
            raise ValueError('Не поддерживаются изменения определения процедур и функций')
        diff_text.append(f'&ИзменениеИКонтроль("{diff_blk['fname']}")\n')
        diff_text.append(block1[0].replace(diff_blk['fname'], f'{prefix}_{diff_blk['fname']}', 1))
        block1 = block1[1:]
        block2 = block2[1:]

    last_tp = ''
    diff_blocks = []
    cur_bl = []
    cur_l_pos = 0
    for diff_line in differ.compare(block1, block2):
        tp = diff_line[0:2]
        if tp =='? ':
            continue
        if last_tp != tp:
            cur_bl = None
            if tp == '  ' or tp == '? ':
                cur_l_pos += 1
            else:
                cur_bl = find_last_tp_block(diff_blocks, tp, cur_l_pos)

            last_tp = tp
            if cur_bl == None:
                diff_blk = {'tp':tp, 'block': [], 'l_pos': cur_l_pos}
                diff_blocks.append(diff_blk)
                cur_bl = diff_blk['block']
            
        cur_bl.append(diff_line[2:])
    
    for blck in diff_blocks:
        if blck['tp'] == '  ':
            diff_text.extend(blck['block'])
        elif blck['tp'] == '- ':
            diff_text.append('#НачалоУдаления\n')
            diff_text.extend(blck['block'])
            diff_text.append('#КонецУдаления\n')
        elif blck['tp'] == '+ ':
            diff_text.append('#НачалоВставки\n')
            diff_text.extend(blck['block'])
            diff_text.append('#КонецВставки\n')
        elif blck['tp'] == '? ':
            diff_text.extend(blck['block'])
    
    return diff_text

def compare_files(file1, file2, output_file, r_prefix):
    #try:
        # Проверяем существование файлов
        exists1 = file1.exists()
        exists2 = file2.exists()

        if not exists1 or not exists2:
            return
        with open(file1, 'r', encoding='utf-8') as f1:
            lines1 = f1.readlines()
        with open(file2, 'r', encoding='utf-8') as f2:
            lines2 = f2.readlines()
        
        if lines1 == lines2:
            return;

        new_text = []
        differ = difflib.Differ()
        diff_blks = bsl_match(lines1, lines2, True)
        for diff_blk in diff_blks:
            diff_text = new_diff_text(diff_blk, differ, r_prefix)
            new_text.extend(diff_text)
            new_text.append('\n')
                
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w+', encoding='utf-8') as f1:
            f1.writelines(new_text)

    #except Exception as e:
    #    with open(output_file, 'w', encoding='utf-8') as f:
    #        f.write(f"Ошибка при сравнении: {str(e)}\n")

def compare_code_blocks(file1, file2, output_file):
    return

def main():

    #parser = argparse.ArgumentParser(description='Обработка по сравнению конфигураций 1С и сохранению изменений в расширение')
    
    #parser.add_argument('-d1', '--dir1', required=True, help='Каталог с исходной конфигурацией')
    #parser.add_argument('-d2', '--dir2', required=True, help='Каталог с целевой конфигурацией')
    #parser.add_argument('-o', '--dir_out', required=True, help='Каталог для формирования расширения')
    #parser.add_argument('-p', '--prefix', required=True, help='Префикс расширения')

    #args = parser.parse_args()

    prefix = 'NEW'

    dir1 = "D:\\Progr\\test\\cmp\\base"
    dir2 = "D:\\Progr\\test\\cmp\\2nd"
    dir_out = "D:\\Progr\\test\\cmp\\rez"

    output_dir = dir_out + "\\" + args.prefix
    
    compare_directories(dir1, dir2, output_dir, prefix)
    print(f"Сравнение завершено. Результаты в {args.dir_out}")

if __name__ == "__main__":
    main()