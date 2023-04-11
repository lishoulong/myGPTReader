from paddleocr import PaddleOCR
import os

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
data_file_path = os.path.join(current_dir, "imgs", "00006737.jpg")

ocr = PaddleOCR(use_angle_cls=True, lang='ch')
result = ocr.ocr(data_file_path, cls=True)
filtered_results = []
for res in result:
    for line in res:
        confidence = line[1][1]
        print(f"line[1]line[0]->{line[1][0]}")
        if confidence > 0.8:
            # 修改这里，将文本列表转换为字符串
            filtered_results.append(line[1][0])

# 使用 join 方法将 filtered_results 列表拼接为带换行符的字符串
text_with_newlines = '\n'.join(filtered_results)

print(text_with_newlines)
