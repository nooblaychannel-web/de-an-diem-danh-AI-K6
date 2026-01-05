from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_FOLDER = os.path.join(BASE_DIR, 'storage')
os.makedirs(STORAGE_FOLDER, exist_ok=True)

SUBJECTS = ["Python", "C++", "Toán cao cấp", "Khoa học dữ liệu", "Tin học ứng dụng", "Tiếng Anh chuyên ngành"]

@app.route('/')
def index():
    files = [f.replace('.xlsx', '') for f in os.listdir(STORAGE_FOLDER) if f.endswith('.xlsx')]
    existing_classes = []
    for f in files:
        if "--" in f:
            parts = f.split("--")
            existing_classes.append({"id": f, "class": parts[0], "subject": parts[1]})
    return render_template('index.html', subjects=SUBJECTS, existing_classes=existing_classes)

@app.route('/create_class', methods=['POST'])
def create_class():
    try:
        class_name = secure_filename(request.form.get('class_name').strip())
        subject_name = secure_filename(request.form.get('subject_name').strip())
        file = request.files.get('file')
        
        if not class_name or not file: 
            return jsonify({"error": "Thiếu tên lớp hoặc file danh sách"}), 400
        
        file_name = f"{class_name}--{subject_name}.xlsx"
        file_path = os.path.join(STORAGE_FOLDER, file_name)
        file.save(file_path)
        return jsonify({"message": f"Đã tạo lớp {class_name} thành công!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_class_data/<file_id>')
def get_class_data(file_id):
    try:
        file_path = os.path.join(STORAGE_FOLDER, f"{file_id}.xlsx")
        df_raw = pd.read_excel(file_path, header=None)
        
        header_row = 0
        for i, row in df_raw.iterrows():
            row_str = row.astype(str).str.upper().tolist()
            if any("MÃ SV" in s or "HỌ TÊN" in s for s in row_str):
                header_row = i
                break
        
        df = pd.read_excel(file_path, header=header_row)
        df = df.dropna(how='all').dropna(axis=1, how='all')
        df.columns = [str(c).strip() for c in df.columns]

        col_ma_sv = next((c for c in df.columns if "MÃ SV" in c.upper()), None)
        col_ho_ten = next((c for c in df.columns if "HỌ TÊN" in c.upper()), None)
        
        if not col_ma_sv or not col_ho_ten:
            return jsonify({"error": "Không tìm thấy cột Mã SV hoặc Họ tên trong file"}), 400

        date_pattern = re.compile(r'^\d{1,2}/\d{1,2}$')
        date_cols = [c for c in df.columns if date_pattern.match(str(c))]
        
        today = datetime.now().strftime("%d/%m")
        
        if today not in date_cols:
            df[today] = False
            date_cols.append(today)
        else:
            df[today] = df[today].apply(lambda x: True if str(x).upper() == 'X' or x is True else False)

        clean_columns = []
        if "STT" in df.columns: clean_columns.append("STT")
        clean_columns.append(col_ma_sv)
        clean_columns.append(col_ho_ten)
        clean_columns.extend(date_cols)

        final_df = df[clean_columns].copy()
        
        return jsonify({
            "columns": final_df.columns.tolist(),
            "data": final_df.fillna("").to_dict(orient='records'),
            "key_ma_sv": col_ma_sv,
            "key_ho_ten": col_ho_ten
        })
    except Exception as e:
        return jsonify({"error": f"Lỗi hệ thống: {str(e)}"}), 500

@app.route('/save_class_data', methods=['POST'])
def save_class_data():
    try:
        content = request.json
        file_id = content.get('file_id')
        data = content.get('data')
        
        df = pd.DataFrame(data)
        for col in df.columns:
            if "/" in str(col):
                df[col] = df[col].apply(lambda x: "X" if x is True or str(x).upper() == 'X' else "")
        
        file_path = os.path.join(STORAGE_FOLDER, f"{file_id}.xlsx")
        df.to_excel(file_path, index=False, engine='openpyxl')
        return jsonify({"message": "Đã lưu dữ liệu an toàn!"})
    except Exception as e:
        return jsonify({"error": f"Lỗi lưu file: {str(e)}"}), 500

@app.route('/download/<file_id>')
def download_file(file_id):
    return send_from_directory(STORAGE_FOLDER, f"{file_id}.xlsx", as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)