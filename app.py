from flask import Flask, render_template, request, redirect, url_for, flash
import boto3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

# AWS S3 Configuration
s3 = boto3.client('s3')

@app.route('/')
def index():
    buckets = s3.list_buckets().get('Buckets', [])
    return render_template('index.html', buckets=buckets)

@app.route('/bucket/<bucket_name>')
def list_bucket(bucket_name):
    objects = s3.list_objects_v2(Bucket=bucket_name).get('Contents', [])
    return render_template('list_bucket.html', bucket_name=bucket_name, objects=objects)

@app.route('/create_bucket', methods=['POST'])
def create_bucket():
    bucket_name = request.form['bucket_name']
    try:
        s3.create_bucket(Bucket=bucket_name)
        flash(f"Bucket '{bucket_name}' created successfully.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('index'))

@app.route('/delete_bucket/<bucket_name>', methods=['POST'])
def delete_bucket(bucket_name):
    try:
        s3.delete_bucket(Bucket=bucket_name)
        flash(f"Bucket '{bucket_name}' deleted successfully.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('index'))

@app.route('/upload/<bucket_name>', methods=['POST'])
def upload_file(bucket_name):
    file = request.files['file']
    key = request.form.get('key', file.filename)

    try:
        s3.upload_fileobj(file, bucket_name, key)
        flash(f"File '{key}' uploaded successfully.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('list_bucket', bucket_name=bucket_name))

@app.route('/delete_file/<bucket_name>/<path:key>', methods=['POST'])
def delete_file(bucket_name, key):
    try:
        s3.delete_object(Bucket=bucket_name, Key=key)
        flash(f"File '{key}' deleted successfully.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('list_bucket', bucket_name=bucket_name))

@app.route('/create_folder/<bucket_name>', methods=['POST'])
def create_folder(bucket_name):
    folder_name = request.form['folder_name']
    if not folder_name.endswith('/'):
        folder_name += '/'
    try:
        s3.put_object(Bucket=bucket_name, Key=folder_name)
        flash(f"Folder '{folder_name}' created successfully.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('list_bucket', bucket_name=bucket_name))

@app.route('/copy_move/<bucket_name>', methods=['POST'])
def copy_move_file(bucket_name):
    source_key = request.form['source_key']
    destination_key = request.form['destination_key']
    operation = request.form['operation']  # copy or move

    try:
        copy_source = {'Bucket': bucket_name, 'Key': source_key}
        s3.copy_object(CopySource=copy_source, Bucket=bucket_name, Key=destination_key)
        if operation == 'move':
            s3.delete_object(Bucket=bucket_name, Key=source_key)
        flash(f"File '{operation}' operation successful.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for('list_bucket', bucket_name=bucket_name))

if __name__ == '__main__':
    app.run(debug=True)
