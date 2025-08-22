import argparse
import os
from flask import Flask, request, render_template, flash, redirect, url_for
from detect import main
from PIL import Image
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # 设置 Flask secret_key

# 全局变量存储上传后的图片路径和分类信息
saved_images = []


@app.route('/home')
def home():
    """首页，包含项目介绍和跳转到目标检测页面的按钮"""
    return render_template('home.html')


@app.route('/', methods=['GET'])
def root():
    """根路由，重定向到首页"""
    return redirect(url_for('home'))


@app.route('/detect', methods=['GET', 'POST'])
def upload():
    global saved_images  # 声明为全局变量，以便后续使用
    saved_images = []  # 每次上传时清空之前的结果

    if request.method == 'POST':
        files = request.files.getlist('files')  # 获取多个文件
        supported_formats = ('.bmp', '.dng', '.jpeg', '.jpg', '.mpo', '.png', '.tif', '.tiff', '.webp', '.pfm',
                             '.asf', '.avi', '.gif', '.m4v', '.mkv', '.mov', '.mp4', '.mpeg', '.mpg', '.ts', '.wmv')

        if files:
            for f in files:
                if f and f.filename:
                    # 获取文件扩展名
                    file_ext = os.path.splitext(f.filename)[1].lower()

                    # 排除不支持的文件
                    if f.filename.lower() == 'desktop.ini' or file_ext not in supported_formats:
                        flash(f"文件 {f.filename} 不被支持或是系统文件。")
                        continue

                    # 生成唯一的文件名以防止冲突
                    unique_suffix = secrets.token_hex(8)
                    filename = f"{os.path.splitext(f.filename)[0]}_{unique_suffix}{file_ext}"
                    file_path = os.path.join(os.getcwd(), filename)

                    # 检查并创建目录
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    f.save(file_path)

                    # 进行目标检测
                    opt = parse_opt(file_path)
                    print("Starting detection with options:", opt)  # 调试信息
                    results = main(opt)  # 获取检测结果

                    print("Detection results:", results)  # 调试信息
                    # 确保 results 是有效的
                    if results is not None:
                        # 保存检测结果并获取保存的图像路径
                        saved_images.extend(save_results(results, filename))

            # 重定向到 showimage 页面显示结果
            return redirect(url_for('showimage'))
        else:
            flash("没有上传文件或文件无效。")
            return render_template('detect.html')
    return render_template('detect.html')


@app.route('/showimage')
def showimage():
    """展示所有分类文件夹"""
    detect_folder = 'detect'  # 检测结果的根文件夹
    folders = []  # 用于存储文件夹名称
    first_images = {}  # 存储每个类别的第一张图片路径

    # 检查 'detect' 文件夹是否存在
    if os.path.exists(detect_folder):
        # 遍历根文件夹中的所有子文件夹
        for class_folder in os.listdir(detect_folder):
            class_path = os.path.join(detect_folder, class_folder)
            if os.path.isdir(class_path):  # 确保是文件夹
                folders.append(class_folder)  # 记录文件夹名称
                
                # 获取该类别的第一张图片
                images = [f for f in os.listdir(class_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
                if images:
                    first_images[class_folder] = images[0]  # 存储第一张图片

    return render_template('showimage.html', folders=folders, first_images=first_images)

@app.route('/original_image')
def original_image():
    """展示所有分类文件夹"""
    detect_folder = 'detect_original'  # 检测结果的根文件夹
    folders = []  # 用于存储文件夹名称
    first_images = {}  # 存储每个类别的第一张图片路径

    # 检查 'detect' 文件夹是否存在
    if os.path.exists(detect_folder):
        # 遍历根文件夹中的所有子文件夹
        for class_folder in os.listdir(detect_folder):
            class_path = os.path.join(detect_folder, class_folder)
            if os.path.isdir(class_path):  # 确保是文件夹
                folders.append(class_folder)  # 记录文件夹名称
                
                # 获取该类别的第一张图片
                images = [f for f in os.listdir(class_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
                if images:
                    first_images[class_folder] = images[0]  # 存储第一张图片

    return render_template('original_image.html', folders=folders, first_images=first_images)

@app.route('/showimage/<class_name>')
def show_class_images(class_name):
    """展示特定分类下的所有图片"""
    detect_folder = 'detect'  # 检测结果的根文件夹
    class_path = os.path.join(detect_folder, class_name)
    images = []

    if os.path.isdir(class_path):  # 确保该分类文件夹存在
        images = [f for f in os.listdir(class_path) if f.endswith(('.jpg', '.jpeg', '.png'))]

    return render_template('class_images.html', class_name=class_name, images=images)

@app.route('/original_image/<class_name>')
def class_original_images(class_name):
    """展示特定分类下的所有原图"""
    detect_folder = 'detect_original'  # 原图的根文件夹
    class_path = os.path.join(detect_folder, class_name)
    images = []

    if os.path.isdir(class_path):  # 确保该分类文件夹存在
        images = [f for f in os.listdir(class_path) if f.endswith(('.jpg', '.jpeg', '.png'))]

    return render_template('class_original_images.html', class_name=class_name, images=images)


def save_results(results, filename):
    saved_images = []  # 用于存储保存的图片路径和类名信息
    img = Image.open(filename)

    print("Detection results:", results)  # 打印检测结果

    for result in results:
        class_name = result.get('class', 'unknown')  # 获取类别
        bbox = result.get('bbox')  # 获取检测框坐标

        print(f"Class: {class_name}, BBox: {bbox}")  # 打印类别和边界框信息

        # 检查并创建原图类别文件夹
        original_class_folder = os.path.join('detect_original', class_name)
        os.makedirs(original_class_folder, exist_ok=True)  # 创建类别文件夹

        # 保存原图到对应类别文件夹
        original_image_name = f"{os.path.splitext(os.path.basename(filename))[0]}_original.jpg"
        original_image_path = os.path.join(original_class_folder, original_image_name)

        # 转换为 RGB 模式（如果需要）
        if img.mode != 'RGB':
            img = img.convert('RGB')

        img.save(original_image_path, 'JPEG')
        print(f"Original image saved to: {original_image_path}")

        if bbox:  # 如果检测到了边界框
            class_folder = os.path.join('detect', class_name)

            print(f"Creating folder: {class_folder}")  # 打印创建文件夹的路径

            # 检查并创建类别文件夹
            os.makedirs(class_folder, exist_ok=True)

            # 裁剪图像
            cropped_img = img.crop((bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]))

            # 转换裁剪后的图像为 RGB 模式（如果需要）
            if cropped_img.mode != 'RGB':
                cropped_img = cropped_img.convert('RGB')

            # 生成保存的文件路径，保证不会重复
            cropped_img_name = f"{os.path.splitext(os.path.basename(filename))[0]}_{class_name}_{secrets.token_hex(4)}.jpg"
            result_image_path = os.path.join(class_folder, cropped_img_name)
            print(f"Saving cropped image to: {result_image_path}")  # 打印保存图像的路径

            # 保存裁剪后的图像
            try:
                cropped_img.save(result_image_path, 'JPEG')
                print(f"Image saved successfully: {result_image_path}")  # 保存成功的信息
            except Exception as e:
                print(f"Error saving image: {e}")

            relative_path = os.path.relpath(result_image_path, start=os.getcwd())
            saved_images.append({
                'path': relative_path.replace('\\', '/'),  # 替换反斜杠为斜杠，兼容Windows
                'class_name': class_name
            })

    return saved_images  # 返回保存的图片路径和类别信息


def parse_opt(file_path):
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='best.pt', help='模型路径或 Triton URL')
    parser.add_argument('--source', type=str, default=file_path, help='文件/目录/URL/glob/屏幕/0（摄像头）')
    parser.add_argument('--data', type=str, default='models/yolov5s.yaml', help='（可选）数据集.yaml路径')
    parser.add_argument('--imgsz', '--img', '--img-size', nargs='+', type=int, default=[640], help='推理大小 h,w')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='置信度阈值')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='NMS IoU 阈值')
    parser.add_argument('--max-det', type=int, default=1000, help='每张图片的最大检测数')
    parser.add_argument('--device', default='', help='CUDA 设备，例如 0 或 0,1,2,3 或 cpu')
    parser.add_argument('--project', default='detect', help='保存结果到项目/名称')
    parser.add_argument('--name', default='', help='保存结果到项目/名称')  # 清空名称，避免子文件夹
    parser.add_argument('--exist-ok', action='store_true', help='现有项目/名称可以，不要递增')
    parser.add_argument('--vid-stride', type=int, default=1, help='视频帧速率步幅')

    opt = parser.parse_args()
    opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1
    return opt


if __name__ == '__main__':
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.run(host='0.0.0.0', port=5000)