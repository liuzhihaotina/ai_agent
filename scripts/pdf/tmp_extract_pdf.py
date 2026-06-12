from PyPDF2 import PdfReader
p=r'D:\_tina\learning\ArmPi Ultra机械臂\tina\源码手搓_从容器提出来\home\ubuntu\docs\pdf\机械臂深度相机应用课程.pdf'
r=PdfReader(p)
print('pages=', len(r.pages))
for i in range(min(8, len(r.pages))):
    t=r.pages[i].extract_text() or ''
    print('\n=== PAGE', i+1, 'LEN', len(t), '===')
    print(t[:2000])
