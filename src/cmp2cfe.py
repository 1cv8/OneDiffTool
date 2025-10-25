
import os
import difflib
from pathlib import Path
import filecmp
import re


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

def func_description(block, start_pos = 0):

    line1 = block[0]
    #key_line1 = line1.lower()
    fname = ""

    pattern = r'функция\s*(.*?)\s*\('
    match = re.search(pattern, line1, re.IGNORECASE)
    
    if match:
        fname = match.group(1)
    if fname == "":
        pattern = r'процедура\s*(.*?)\s*\('
        match = re.search(pattern, line1, re.IGNORECASE)
        if match:
            fname = match.group(1)

    return {"fname": fname}

def remove_comments(cur_block):

    i = len(cur_block)-1
    comments = []

    while i >= 0:
        
        line = cur_block[i]
        key_line = line.lstrip()[0:4].lower()
        if key_line.startswith('//'):
            comments.insert(0, line)
            cur_block.pop(i)
            i -= 1
        else:
            break

    return comments


def block_exist_ne_lines(cur_block):

    for line in cur_block:
        if line.lstrip() != '':
            return True
    return False



def get_bsl_blocks(lines):
    
    n_words = ['функция', 'процедура', 'procedure', 'function']
    e_words = ['конецфункции', 'конецпроцедуры', 'endprocedure', 'endfunction']

    
    i = 0

    rez = []

    # init block
    start_i = i
    exist_ne_lines = False
    cur_block = []
    cur_fname = ''
    start_code = 0
    in_func = False
    
    while i < len(lines):
        line = lines[i]
        key_line = line.lstrip()[0:20].lower()
        if key_line == '':
            i += 1
            cur_block.append(line)
            continue
        
        if any(key_line.startswith(keyword) for keyword in  n_words):
            
            comments = []
            if len(cur_block) > 0 and exist_ne_lines:
                comments = remove_comments(cur_block)
                exist_ne_lines = block_exist_ne_lines(cur_block)

            if len(cur_block) > 0 and exist_ne_lines:
                #yield {"block": cur_block, "type": "c"}
                rez.append({"block": cur_block, "type": "c"})
            
            # init block
            in_func = True
            start_i = i
            cur_block = []
            start_code = 0
            if len(comments) > 0:
                cur_block = comments
                start_code = len(comments) 
            exist_ne_lines = True
            cur_fname = func_description([line])
            cur_block.append(line)

        elif any(key_line.startswith(keyword) for keyword in e_words):
            cur_block.append(line)
            btype = "f"
            if start_i >= i:
                btype = "c"
            #yield {"block": cur_block, "type": btype, "desc": func_description(cur_block)}
            #rez.append({"block": cur_block, "type": btype, "desc": func_description(cur_block)})
            rez.append({"block": cur_block, "type": btype, "desc": cur_fname, "start_pos": start_code})
    
            # init block
            in_func = False
            start_i = i+1
            exist_ne_lines = False
            cur_block = []

        elif (not in_func) and any(key_line.startswith(keyword) for keyword in  ['#область', '#region']):
            
            if len(cur_block) > 0 and exist_ne_lines:
                rez.append({"block": cur_block, "type": "c"})
            
            rez.append({"block": [line], "type": "r"})

            # init block
            start_i = i+1
            exist_ne_lines = False
            cur_block = []

        elif (not in_func) and any(key_line.startswith(keyword) for keyword in  ['#конецобласти', '#endregion']):

            if len(cur_block) > 0 and exist_ne_lines:
                rez.append({"block": cur_block, "type": "c"})

            rez.append({"block": [line], "type": "re"})
            
            # init block
            start_i = i+1
            exist_ne_lines = False
            cur_block = []

        else:
            exist_ne_lines = True
            cur_block.append(line)
        i += 1

    if len(cur_block) > 0 and exist_ne_lines:
        #yield {"block": cur_block, "type": "c"}
        rez.append({"block": cur_block, "type": "c"})

    return rez



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

        #bbl2 = get_bsl_blocks(lines2)

        for block1 in get_bsl_blocks(lines1):
            if block1['type'] not in ['c', 'r', 're']:
                print(f"type: {block1['type']} desc: {block1['desc']['fname']} code: {block1['block'][0:3]}")
            else:
                print(f"type: {block1['type']} code: {block1['block'][0:3]}")
        #for block2 in bbl2:
        #    print(block2['type'])
        
        output_file.parent.mkdir(parents=True, exist_ok=True)

 

    #except Exception as e:
    #    with open(output_file, 'w', encoding='utf-8') as f:
    #        f.write(f"Ошибка при сравнении: {str(e)}\n")

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