# 🗂️ Amazon S3 File Manager (FastAPI)

This project implements a simple Amazon S3 file manager using **FastAPI** and **Boto3** with a minimal web interface (HTML + Jinja2).

---

## ✅ Assignment Requirements

> **Question:**  
Implement S3 file manager using any Python web framework (Flask/Django/etc).  

**Functions:**
1. List contents of S3  
2. Create/Delete folder and bucket  
3. Upload/Delete files in S3  
4. Copy/Move files within S3  

**Notes:**
- Ensure code is readable ✅  
- App must function properly ✅  
- Basic UI should be available ✅  

---

## ⚙️ Features Implemented

| Feature                     | Status |
|-----------------------------|--------|
| List S3 Buckets             | ✅     |
| List Files in Bucket        | ✅     |
| Create Bucket               | ✅     |
| Delete Bucket (only if empty) | ✅   |
| Upload Files (with optional path/key) | ✅ |
| Delete File                 | ✅     |
| Create Folder               | ✅     |
| Delete Folder (if empty)    | ✅     |
| Copy File                   | ✅     |
| Move File                   | ✅     |
| Basic UI using Jinja2       | ✅     |

---

## 🚀 Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/s3-file-manager-fastapi.git
cd s3-file-manager-fastapi
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

If `pip` installation is restricted by your system:

```bash
sudo apt install python3.12-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### 3. Configure AWS CLI
```bash
aws configure
```

Use your own AWS credentials and a **free-tier region** like `us-east-1`.  
Set values for:
- Access Key ID
- Secret Access Key
- Default region (e.g., `us-east-1`)
- Default output format (you can leave this blank or set to `json`)

---

### 4. Run the App
```bash
uvicorn main:app --reload
```

Then open your browser and visit:  
📍 **http://localhost:8000**

---

## 🖥️ UI Overview

- **Create New Bucket**  
- **View and Browse Files in Buckets**  
- **Upload Files (with optional key path)**  
- **Create Folders (virtual)**  
- **Delete Files or Folders**  
- **Copy or Move Files (with input for source and destination keys and buckets)**  

---

## 🔁 Copy / Move File Example

To **copy** `reports/file1.pdf` to `backup/file1.pdf` inside the same bucket:

| Field              | Example Value             |
|-------------------|---------------------------|
| Source Key         | `reports/file1.pdf`       |
| Destination Key    | `backup/file1.pdf`        |
| Destination Bucket | `<same bucket>`           |
| Move checkbox      | ❌ (unchecked = copy)     |

To **move** instead: check the **Move** checkbox ✅.

---

## 📁 Project Structure

```
.
├── main.py                 # FastAPI app
├── templates/
│   └── index.html          # Jinja2 HTML UI
├── requirements.txt
└── README.md
```

---

## 🔒 Notes

- Buckets must be globally unique (AWS S3 restriction)
- Buckets must be empty before deletion
- Folder creation is simulated by creating zero-byte keys ending with `/`
- Moving = Copying then deleting the original

---

## 🆓 AWS Free Tier Tips

- Stick to **us-east-1** or **us-west-2** to avoid charges  
- Avoid uploading large files  
- Delete unused buckets and objects when done  

---

## 📄 License

MIT License

---

## 🙌 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Amazon S3](https://aws.amazon.com/s3/)
- [Jinja2](https://jinja.palletsprojects.com/)
