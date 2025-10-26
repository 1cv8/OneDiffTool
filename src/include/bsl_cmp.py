
import re


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


def code_equal(list1, list2):
    if len(list1) != len(list2):
        return False

    indx = 0
    for str1 in list1:
        if str1 != list2[indx]:
            return False
        indx += 1

    return True

def block_wo_comments(block):
    if block['type'] == 'f':
        if block['csize'] > 0:
            return block['block'][block['csize']:]
        else:
            return block['block']
    return block['block']


def bsl_match(lines1, lines2, wo_comments = False):
    bbl1 = get_bsl_blocks(lines1)
    bbl2 = get_bsl_blocks(lines2)
    cmprs = bsl_blocks_match(bbl1, bbl2)
    diff_blks = []
    for cmpr in cmprs:
         if cmpr['i1'] != -1 and  cmpr['i2'] != -1:
            blok_desc1 = bbl1[cmpr['i1']]
            blok_desc2 = bbl2[cmpr['i2']]
            
            block1 = None
            block2 = None
            if wo_comments:
                block1 = block_wo_comments(blok_desc1)
                block2 = block_wo_comments(blok_desc2)
            else:
                block1 = blok_desc1['block']
                block2 = blok_desc2['block']
            
            fname = ''
            if blok_desc1['type'] == 'f':
                fname = blok_desc1['desc']['fname']

            if not code_equal(block1, block2):
                 diff_blks.append({'b1': block1, 'b2': block2, 'type': blok_desc1['type'], 'fname': fname})
    return diff_blks


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
    comments_size = 0
    
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
            comments_size = len(comments)
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
            rez.append({"block": cur_block, "type": btype, "desc": cur_fname, "start_pos": start_code, 'csize': comments_size})
    
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

def bsl_blocks_match(bbl1, bbl2):
    
    # Словарь для поиска по наименованию
    fnames2 = {}
    indx = 0
    for block1 in bbl2:
        if block1['type'] == 'f' and block1['desc']['fname'] != '':
            fnames2[block1['desc']['fname']] = indx
        indx += 1

    cmps = []
    founded = []
    # Первый проход. Точное совпадение
    indx = 0
    for block1 in bbl1:
        indx2 = -1
        if block1['type'] == 'f' and block1['desc']['fname'] != '':
            indx2 = fnames2.get(block1['desc']['fname'], -1)
        
        if indx2 >= 0  and indx2 in founded:
            indx2 = -1
        
        if indx2 >= 0:
            founded.append(indx2)

        cmps.append({"i1": indx, "i2": indx2})
        indx += 1
    
    for cmp in cmps:
        if cmp['i2'] == -1:
            indx2 = 0
            block1 = bbl1[cmp['i1']]
            for block2 in bbl2:
                if not(indx2 in founded):
                    if code_equal(block1['block'], block2['block']):
                        cmp['i2'] = indx2
                        founded.append(indx2)
                        break
                
                indx2 += 1

    indx2 = 0
    for block2 in bbl2:
        if not(indx2 in founded):
            cmps.append({"i1": -1, "i2": indx2})
        indx2 += 1

    return cmps
