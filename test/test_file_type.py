from app.utils.filesystem import get_file_extension
import sys
sys.path.append('/Users/lishoulong/Documents/toutiao/lib/openai/myGPTReader')

# 示例
filename = "example_document.pdf"
file_extension = get_file_extension(filename)
print("File type:", file_extension)
