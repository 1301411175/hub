import fitz  # PyMuPDF

import re

def replace_excessive_newlines(text):
    # 使用正则表达式替换超过三个的连续换行符为两个换行符
    # 先去除掉所有\n之间的的空格，\s*: 匹配任意数量的空白字符，包括零个
    res = re.sub(r'\n\s*\n', '\n\n', text)
    res = re.sub(r'\n\n{2,}', '\n\n', res)
    return res

def replace_chinese_punctuation(input_data):
    # 定义中文符号和对应的英文符号
    chinese_punctuation = "，。！？：；“”‘’（）【】《》"
    english_punctuation = ",.!?;\"\"''()[]<>"

    # 替换函数
    def replace_punctuation(text):
        # 特别处理中文右单引号
        text = text.replace("’", "'")
        for ch, en in zip(chinese_punctuation, english_punctuation):
            text = text.replace(ch, en)
        return text

    # 根据输入类型进行处理
    if isinstance(input_data, str):
        return replace_punctuation(input_data)
    elif isinstance(input_data, list):
        return [replace_punctuation(item) for item in input_data]
    else:
        raise ValueError("输入必须是字符串或字符串列表")

def is_number(s):
    try:
        float(s)  # 尝试将字符串转换为浮点数
        return True
    except ValueError:
        return False

def search_first_page(pdf_path, title_for_search = None):
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    doc.close()
    if toc and title_for_search is None:
        for level, title, page in toc:
            return page
    if toc and title_for_search is not None:
        for level, title, page in toc:
            if title_for_search == replace_chinese_punctuation(title):
                return page
    return None

def get_font_size(pdf_path):
    # 打开PDF文件
    doc = fitz.open(pdf_path)
    text = []
    font_size_set = set()
    font_size_dict = {}
    first_page_number = search_first_page(pdf_path)
    for page in doc:
        if page.number+1 < first_page_number:
            continue
        # 提取页面中的文本块及其字体信息
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        # 根据字体大小判断是否为标题或正文
                        font_size_set.add(round(s["size"], 4))
                        font_size_dict[round(s["size"], 4)] = font_size_dict.get(round(s["size"], 4), 0) + 1      
    print(font_size_dict)
    return font_size_dict

# 根据字体大小提取文本
def extract_text_by_font(pdf_path, font_size_dict=None):
    doc = fitz.open(pdf_path)
    text = []
    if not font_size_dict:
        font_size_dict = get_font_size(pdf_path)
    first_page_number = search_first_page(pdf_path)
    main_body_font_size = max(font_size_dict, key=font_size_dict.get)
    for page in doc:
        if page.number+1 < first_page_number:
            continue
        blocks = page.get_text("dict")["blocks"]
        # char_stack = []
        for b in blocks:
            # 一个block默认为一段
            block_text = ""
            if "lines" in b:
                for l in b["lines"]:
                    # 每行单独处理，除去页码等干扰信息
                    line_char = []
                    # main_body_line_flag = False
                    for s in l["spans"]:
                        if abs(s["size"] - main_body_font_size) <= 0.001:
                            line_char.append(s["text"])
                        # if main_body_line_flag is False and s["size"] == main_body_font_size:
                        #     main_body_line_flag = True
                    if line_char and not is_number("".join(line_char)):
                        block_text += "".join(line_char)
                
                    if "".join(line_char).find("THE EUROPEAN") != -1:
                        print(-1)
            text.append(block_text)                              
    doc.close()
    return "\n".join(text)

def extract_text_by_font_and_title(pdf_path, font_size_dict, title, titles_list):
    doc = fitz.open(pdf_path)
    text = []
    if not font_size_dict:
        font_size_dict = get_font_size(pdf_path)
    main_body_font_size = max(font_size_dict, key=font_size_dict.get)
    first_page_number = search_first_page(pdf_path, title)
    if titles_list.index(title) < len(titles_list)-1:
        next_page_number = search_first_page(pdf_path, titles_list[titles_list.index(title)+1])
    else:
        next_page_number = -1
    for page in doc:
        if page.number+1 < first_page_number:
            continue
        if page.number+1 > next_page_number:
            break
        blocks = page.get_text("dict")["blocks"]
        # char_stack = []
        for b in blocks:
            # 一个block默认为一段
            block_text = ""
            if "lines" in b:
                for l in b["lines"]:
                    # 每行单独处理，除去页码等干扰信息
                    line_char = []
                    # main_body_line_flag = False
                    for s in l["spans"]:
                        if abs(s["size"] - main_body_font_size) <= 0.001:
                            line_char.append(s["text"])
                        # if main_body_line_flag is False and s["size"] == main_body_font_size:
                        #     main_body_line_flag = True
                    if line_char and not is_number("".join(line_char)):
                        block_text += "".join(line_char)
            text.append(block_text)                              
    doc.close()
    return "\n".join(text)


def get_node_titles(node):
    temp_titles = []
    temp_titles.append(node['title'])
    if len(node['children']) > 0:
        for child in node['children']:
            temp_titles += get_node_titles(child)
    return temp_titles

def build_outline_tree(pdf_path):
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    doc.close()
    tree = []
    stack = [(tree, 0)]  # 使用栈来存储目录树的当前路径和层级
    for level, title, page in toc:
        # 为当前项创建一个节点
        title = replace_chinese_punctuation(title)
        node = {"title": title, "page": page, "children": []}
        # 找到正确的父级项
        while level <= stack[-1][1]:
            stack.pop()
        # 将当前节点添加到父级的children中
        stack[-1][0].append(node)
        # 更新栈
        stack.append((node["children"], level))
    return tree

# 根据目录树细粒度填充内容（确定到段）
def fill_in_outline_tree_divide_by_para(root_node, extracted_text, titles_list, start_pos = 0):
    lower_extracted_text = extracted_text.lower()
    for node in root_node:
        current_title = node['title']   
        lower_current_title = current_title.lower()
        pos1 = lower_extracted_text.find(lower_current_title, start_pos)
        if titles_list.index(current_title) == len(titles_list)-1:
            pos2 = -1
        else:                
            next_title = titles_list[titles_list.index(current_title)+1]
            lower_next_title = next_title.lower()
            pos2 = lower_extracted_text.find(lower_next_title, start_pos) 
        # print(node['title'], node['page'])
        node["content"] = extracted_text[pos1:pos2]
        start_pos = pos2
        if len(node['children']) > 0:
            start_pos = fill_in_outline_tree_divide_by_para(node['children'], extracted_text, titles_list, start_pos)
    return start_pos
            
# 根据目录树粗粒度填充内容（确定到页）
def fill_in_outline_tree_divide_by_page(root_node, pdf_path, titles_list):
    font_size_dict = get_font_size(pdf_path)
    for node in root_node:
        current_title = node['title']   
        node["content"] = extract_text_by_font_and_title(pdf_path, font_size_dict, current_title, titles_list)
        if len(node['children']) > 0:
            fill_in_outline_tree_divide_by_page(node['children'], pdf_path, titles_list)
    return
   
   
   
def get_doc_tree(file_path="/home/phm/code/python/Laws/电池法律/SR-2023-15_EN.pdf"):
    extracted_text = extract_text_by_font(file_path)
    # 去除多余的换行符
    extracted_text = replace_excessive_newlines(extracted_text)
    # 提取目录树
    outline_tree = build_outline_tree(file_path)
    titles_list = []
    for node in outline_tree:
        titles_list += get_node_titles(node)
    titles_list = replace_chinese_punctuation(titles_list)
    extracted_text = replace_chinese_punctuation(extracted_text)
    titles_index = {}
    for title in titles_list:
        titles_index[title] = extracted_text.find(title)
    def cal_right_rate(titles_index):
        count = 0
        for key, value in titles_index.items():
            if value != -1:
                count += 1
        return count/len(titles_index)
    if cal_right_rate(titles_index) == 1:
        fill_in_outline_tree_divide_by_para(outline_tree, extracted_text, titles_list, start_pos=0)
    else:
        fill_in_outline_tree_divide_by_page(outline_tree, file_path, titles_list)
    return outline_tree            
# 使用示例
pdf_path = "/home/phm/code/python/Laws/电池法律/SR-2023-15_EN.pdf"

doc_tree = get_doc_tree(file_path=pdf_path)
import json

with open("test.json", "w") as f:
    json.dump(doc_tree, f, indent=4, ensure_ascii=False)
