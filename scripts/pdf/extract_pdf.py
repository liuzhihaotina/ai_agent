from PyPDF2 import PdfReader
from pathlib import Path
pdf = Path(r'D:\_tina\learning\ArmPi Ultra机械臂\tina\源码手搓_从容器提出来\home\ubuntu\docs\pdf\机械臂深度相机应用课程.pdf')
out = Path('tmp/pdf_text.txt')
out.parent.mkdir(exist_ok=True)
reader = PdfReader(str(pdf))
with out.open('w', encoding='utf-8') as f:
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ''
        f.write(f'\n\n===== PAGE {i} =====\n')
        f.write(text)
print('pages', len(reader.pages))
print('wrote', out)
