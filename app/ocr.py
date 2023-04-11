from paddleocr import PaddleOCR
import numpy as np
from io import BytesIO
from PIL import Image
import torch
from lavis.models import load_model_and_preprocess

# current_file_path = os.path.abspath(__file__)
# current_dir = os.path.dirname(current_file_path)
# data_file_path = os.path.join(current_dir, "imgs", "00006737.jpg")

# # 以二进制方式打开图像文件并读取为 buffer
# with open(data_file_path, 'rb') as img_file:
#     img_buffer = io.BytesIO(img_file.read())

def image_ocr(img_buffer):
	# 使用 PIL.Image.open 从 buffer 中打开图像
	# 使用 io.BytesIO 将字节串转换为一个类文件对象
	img_file = BytesIO(img_buffer)
	img = Image.open(img_file)
# 将图像转换为 RGB 格式
	img_rgb = img.convert('RGB')
	# 将图像对象转换为 NumPy 数组
	img_np = np.asarray(img_rgb)

	ocr = PaddleOCR(use_angle_cls=True, lang='ch')
	result = ocr.ocr(img_np, cls=True)  # 将 NumPy 数组传递给 ocr 函数
	filtered_results = []
	for res in result:
			for line in res:
					confidence = line[1][1]
					if confidence > 0.8:
							filtered_results.append(line[1][0])

	# text_with_newlines = '\n'.join(filtered_results)

	# print(text_with_newlines)
	return filtered_results

def image_meme(img_buffer):
	img_file = BytesIO(img_buffer)

	print(f"img_fileimg_file->{img_file}")
	# load sample image
	raw_image = Image.open(img_file).convert("RGB")
	# loads BLIP caption base model, with finetuned checkpoints on MSCOCO captioning dataset.
	# this also loads the associated image processors
	# setup device to use
	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
	model, vis_processors, _ = load_model_and_preprocess(name="blip_caption", model_type="base_coco", is_eval=True, device=device)
	# preprocess the image
	# vis_processors stores image transforms for "train" and "eval" (validation / testing / inference)
	image = vis_processors["eval"](raw_image).unsqueeze(0).to(device)
	# generate caption
	return model.generate({"image": image})
	# ['a large fountain spewing water into the air']