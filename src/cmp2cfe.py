
import os
import argparse
import uuid
import xml.etree.ElementTree as ET

from pathlib import Path

from include.bsl_cmp import bsl_match

import difflib

import hashlib

TEMPLATES_DIR = Path(__file__).parent / 'templates'


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

    # Получаем список всех файлов
    files1 = {f.relative_to(dir1) for f in dir1.rglob('*.bsl') if f.is_file()}
    files2 = {f.relative_to(dir2) for f in dir2.rglob('*.bsl') if f.is_file()}

    all_files = files1 & files2
    changed_files = []

    for file_rel in sorted(all_files, key=lambda path: str(path).lower()):
        file1 = dir1 / file_rel
        file2 = dir2 / file_rel
        output_file = output_dir / file_rel

        if compare_files(file1, file2, output_file, r_prefix):
            changed_files.append(file_rel)

    return changed_files

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
            diff_text.append('#Удаление\n')
            diff_text.extend(blck['block'])
            diff_text.append('#КонецУдаления\n')
        elif blck['tp'] == '+ ':
            diff_text.append('#Вставка\n')
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
            return False
        with open(file1, 'r', encoding='utf-8') as f1:
            lines1 = f1.readlines()
        with open(file2, 'r', encoding='utf-8') as f2:
            lines2 = f2.readlines()
        
        if lines1 == lines2:
            return False

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

        return True

    #except Exception as e:
    #    with open(output_file, 'w', encoding='utf-8') as f:
    #        f.write(f"Ошибка при сравнении: {str(e)}\n")

def read_template(template_name):
    return (TEMPLATES_DIR / template_name).read_text(encoding='utf-8')


def render_template(template_name, values):
    text = read_template(template_name)
    for key, value in values.items():
        text = text.replace('{' + key + '}', value)
    return text


def generate_guid():
    return str(uuid.uuid4())


def calculate_sha1(file_path):
    hash_sha1 = hashlib.sha1()
    with open(file_path, 'rb') as file_data:
        for chunk in iter(lambda: file_data.read(8192), b''):
            hash_sha1.update(chunk)
    return hash_sha1.hexdigest()


def write_text_file(file_path, content):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')


def find_child_text(parent, tag_name, default=''):
    if parent is None:
        return default

    for child in parent:
        child_tag_name = child.tag.split('}', 1)[-1]
        if child_tag_name == tag_name:
            return child.text or default

    return default


def load_xml_root(file_path):
    return ET.parse(file_path).getroot()


def load_configuration_metadata(config_dir):
    root = load_xml_root(Path(config_dir) / 'Configuration.xml')
    config_node = root.find('.//{*}Configuration')
    props_node = config_node.find('{*}Properties')

    compatibility_mode = find_child_text(props_node, 'CompatibilityMode')
    if compatibility_mode == '':
        raise ValueError(
            f'В исходной конфигурации не найден параметр CompatibilityMode: {Path(config_dir) / "Configuration.xml"}'
        )
    script_variant = find_child_text(props_node, 'ScriptVariant', 'Russian')

    return {
        'base_name': find_child_text(props_node, 'Name'),
        'compatibility_mode': compatibility_mode,
        'script_variant': script_variant
    }


def load_languages_metadata(config_dir):
    languages_dir = Path(config_dir) / 'Languages'
    languages = []

    if not languages_dir.exists():
        return languages

    for lang_file in sorted(languages_dir.glob('*.xml'), key=lambda path: path.name.lower()):
        root = load_xml_root(lang_file)
        lang_node = root.find('.//{*}Language')
        props_node = lang_node.find('{*}Properties')

        languages.append({
            'base_uuid': lang_node.attrib['uuid'],
            'name': find_child_text(props_node, 'Name'),
            'language_code': find_child_text(props_node, 'LanguageCode', 'ru')
        })

    return languages


def load_common_module_metadata(config_dir, module_name):
    module_meta_path = Path(config_dir) / 'CommonModules' / f'{module_name}.xml'
    root = load_xml_root(module_meta_path)
    module_node = root.find('.//{*}CommonModule')
    props_node = module_node.find('{*}Properties')

    return {
        'base_uuid': module_node.attrib['uuid'],
        'name': find_child_text(props_node, 'Name')
    }


def collect_changed_common_modules(config_dir, changed_files):
    modules = []
    module_names = set()
    unsupported_files = []

    for changed_file in changed_files:
        parts = changed_file.parts
        if len(parts) >= 4 and parts[0] == 'CommonModules' and parts[2] == 'Ext' and parts[-1].lower() == 'module.bsl':
            module_name = parts[1]
            if module_name not in module_names:
                modules.append(load_common_module_metadata(config_dir, module_name))
                module_names.add(module_name)
        else:
            unsupported_files.append(changed_file)

    return modules, unsupported_files


def build_child_objects_text(languages, common_modules):
    child_objects = []
    for language in languages:
        child_objects.append(f'\t\t\t<Language>{language["name"]}</Language>\n')
    for common_module in common_modules:
        child_objects.append(f'\t\t\t<CommonModule>{common_module["name"]}</CommonModule>\n')
    return ''.join(child_objects)


def build_extension_name(prefix):
    return f'Расширение_{prefix}'


def build_extension_synonym(prefix):
    return f'Расширение {prefix}'


def write_languages_files(output_dir, languages):
    language_entries = []
    for language in languages:
        language['new_uuid'] = generate_guid()
        language_output = output_dir / 'Languages' / f'{language["name"]}.xml'
        language_text = render_template('Languages.xml', {
            'new_uuid': language['new_uuid'],
            'base_Name': language['name'],
            'base_uuid': language['base_uuid'],
            'language_code': language['language_code']
        })
        write_text_file(language_output, language_text)
        language['config_version_hash'] = calculate_sha1(language_output)
        language_entries.append(
            f'\t\t<Metadata name="Language.{language["name"]}" id="{language["new_uuid"]}" '
            f'configVersion="{language["config_version_hash"]}"/>\n'
        )

    return ''.join(language_entries)


def write_common_modules_files(output_dir, common_modules):
    common_module_entries = []
    for common_module in common_modules:
        common_module['new_uuid'] = generate_guid()
        module_xml_output = output_dir / 'CommonModules' / f'{common_module["name"]}.xml'
        module_bsl_output = output_dir / 'CommonModules' / common_module['name'] / 'Ext' / 'Module.bsl'

        module_text = render_template('CommonModules.xml', {
            'new_uuid': common_module['new_uuid'],
            'base_Name': common_module['name'],
            'base_uuid': common_module['base_uuid']
        })
        write_text_file(module_xml_output, module_text)

        common_module['config_version_hash'] = calculate_sha1(module_xml_output)
        common_module['module_version_hash'] = calculate_sha1(module_bsl_output)

        common_module_entries.append(
            f'\t\t<Metadata name="CommonModule.{common_module["name"]}" id="{common_module["new_uuid"]}" '
            f'configVersion="{common_module["config_version_hash"]}"/>\n'
        )
        common_module_entries.append(
            f'\t\t<Metadata name="CommonModule.{common_module["name"]}.Module" id="{common_module["new_uuid"]}.0" '
            f'configVersion="{common_module["module_version_hash"]}"/>\n'
        )

    return ''.join(common_module_entries)


def write_configuration_files(dir1, output_dir, prefix, common_modules):
    config_meta = load_configuration_metadata(dir1)
    languages = load_languages_metadata(dir1)
    config_uuid = generate_guid()
    config_name = build_extension_name(prefix)
    config_text = render_template('Configuration.xml', {
        'new_uuid': config_uuid,
        'new_uuid1': generate_guid(),
        'new_uuid2': generate_guid(),
        'new_uuid3': generate_guid(),
        'new_uuid4': generate_guid(),
        'new_uuid5': generate_guid(),
        'new_uuid6': generate_guid(),
        'new_uuid7': generate_guid(),
        'Name': config_name,
        'Synonim': build_extension_synonym(prefix),
        'Prefix': prefix,
        'CompatibilityMode': config_meta['compatibility_mode'],
        'ScriptVariant': config_meta['script_variant'],
        'ChildObjects': build_child_objects_text(languages, common_modules)
    })

    configuration_output = output_dir / 'Configuration.xml'
    write_text_file(configuration_output, config_text)

    common_module_entries = write_common_modules_files(output_dir, common_modules)
    language_entries = write_languages_files(output_dir, languages)
    config_version_hash = calculate_sha1(configuration_output)

    config_dump_text = render_template('ConfigDumpInfo.xml', {
        'CommonModuleEntries': common_module_entries,
        'config_Name': config_name,
        'new_config_uuid': config_uuid,
        'config_version_hash': config_version_hash,
        'LanguageEntries': language_entries
    })
    write_text_file(output_dir / 'ConfigDumpInfo.xml', config_dump_text)


def generate_extension(dir1, output_dir, prefix, changed_files):
    if not changed_files:
        return []

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    common_modules, unsupported_files = collect_changed_common_modules(dir1, changed_files)
    write_configuration_files(dir1, output_dir, prefix, common_modules)

    return unsupported_files

def compare_code_blocks(file1, file2, output_file):
    return

def main():

    parser = argparse.ArgumentParser(description='Обработка по сравнению конфигураций 1С и сохранению изменений в расширение')
    
    parser.add_argument('-d1', '--dir1', required=True, help='Каталог с исходной конфигурацией')
    parser.add_argument('-d2', '--dir2', required=True, help='Каталог с целевой конфигурацией')
    parser.add_argument('-o', '--dir_out', required=True, help='Каталог для формирования расширения')
    parser.add_argument('-p', '--prefix', required=True, help='Префикс расширения')

    args = parser.parse_args()

    output_dir = Path(args.dir_out) / args.prefix
    changed_files = compare_directories(args.dir1, args.dir2, output_dir, args.prefix)
    unsupported_files = generate_extension(args.dir1, output_dir, args.prefix, changed_files)

    if unsupported_files:
        print('Предупреждение: метаданные расширения созданы только для CommonModules, другие измененные файлы пока не описываются:')
        for unsupported_file in unsupported_files:
            print(f'  {unsupported_file}')

    print(f"Сравнение завершено. Результаты в {args.dir_out}")

if __name__ == "__main__":
    main()
