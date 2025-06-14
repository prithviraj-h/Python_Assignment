from flask import Flask, render_template, request, redirect, url_for, flash
import boto3
import os
import re
from botocore.exceptions import ClientError
import secrets

app = Flask(__name__)
# Generate a strong secret key. For production, load from environment variable.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(24))

# AWS S3 Configuration
# It's good practice to specify a region. boto3 will also look for credentials
# in environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY),
# shared credential files (~/.aws/credentials), or IAM roles.
# For local testing, ensure your AWS CLI is configured or set environment variables.
s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'ap-south-1')) # Defaulting to Mumbai region

@app.route('/')
def index():
    """
    Lists all S3 buckets available to the configured AWS credentials.
    """
    try:
        buckets = s3.list_buckets().get('Buckets', [])
        return render_template('index.html', buckets=buckets)
    except ClientError as e:
        flash(f"Error listing buckets: {e}", "danger")
        return render_template('index.html', buckets=[]) # Render with empty list on error
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
        return render_template('index.html', buckets=[])

@app.route('/bucket/<bucket_name>')
def list_bucket(bucket_name):
    """
    Lists objects (files) and common prefixes (folders) within a specified S3 bucket.
    Supports basic folder navigation using the 'prefix' query parameter and pagination.
    """
    prefix = request.args.get('prefix', '')  # Optional folder path
    next_token = request.args.get('next_token') # For pagination

    params = {'Bucket': bucket_name, 'Prefix': prefix, 'Delimiter': '/'}
    if next_token:
        params['ContinuationToken'] = next_token

    folders = []
    files = []
    current_next_token = None
    is_truncated = False

    try:
        response = s3.list_objects_v2(**params)
        folders = response.get('CommonPrefixes', [])
        files = response.get('Contents', [])
        current_next_token = response.get('NextContinuationToken')
        is_truncated = response.get('IsTruncated', False) # True if there are more results

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == 'NoSuchBucket':
            flash(f"Bucket '{bucket_name}' does not exist.", "danger")
            return redirect(url_for('index'))
        else:
            flash(f"Error listing contents of bucket '{bucket_name}': {e}", "danger")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")

    return render_template('list_bucket.html', bucket_name=bucket_name, objects=files,
                           folders=folders, current_prefix=prefix,
                           next_token=current_next_token, is_truncated=is_truncated)


@app.route('/create_bucket', methods=['POST'])
def create_bucket():
    """
    Handles the creation of a new S3 bucket. Includes basic validation for bucket names
    and specific error handling for S3 ClientErrors.
    """
    bucket_name = request.form['bucket_name'].strip()

    # Basic bucket name validation (S3 has strict rules)
    # Must be lowercase, start/end with a letter/number, contain only lowercase letters, numbers, and hyphens/dots.
    # Length between 3 and 63 characters.
    if not re.match(r'^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$', bucket_name):
        flash("Invalid bucket name. Bucket names must be lowercase, start and end with a letter or number, contain only lowercase letters, numbers, and hyphens, and be between 3 and 63 characters long.", "danger")
        return redirect(url_for('index'))
    
    try:
        # Get the region from the s3 client object for consistency.
        # For non-us-east-1 regions, LocationConstraint is required.
        region = s3.meta.region_name
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
        
        flash(f"Bucket '{bucket_name}' created successfully.", "success")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == 'BucketAlreadyOwnedByYou':
            flash(f"Bucket '{bucket_name}' already exists and is owned by you.", "warning")
        elif error_code == 'BucketAlreadyExists':
            flash(f"Bucket '{bucket_name}' already exists and is owned by another account.", "danger")
        elif error_code == 'IllegalLocationConstraintException':
            flash(f"Error: Bucket name '{bucket_name}' is valid, but the specified region '{region}' might be incorrect or you need to try a different region for bucket creation.", "danger")
        else:
            flash(f"Error creating bucket: {e}", "danger")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
    return redirect(url_for('index'))

@app.route('/delete_bucket/<bucket_name>', methods=['POST'])
def delete_bucket(bucket_name):
    """
    Deletes an S3 bucket. A bucket must be empty before it can be deleted.
    Provides user feedback if the bucket is not empty.
    """
    try:
        # Check if the bucket is empty before attempting deletion
        # MaxKeys=1 is efficient for checking if *any* contents exist
        response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        if 'Contents' in response and len(response['Contents']) > 0:
            flash(f"Bucket '{bucket_name}' is not empty. Please delete all files and folders first.", "danger")
        else:
            s3.delete_bucket(Bucket=bucket_name)
            flash(f"Bucket '{bucket_name}' deleted successfully.", "success")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == 'NoSuchBucket':
            flash(f"Bucket '{bucket_name}' does not exist.", "warning")
        elif error_code == 'BucketNotEmpty': # This error might be raised directly by S3 if it's not empty
            flash(f"Bucket '{bucket_name}' is not empty. Please delete all files and folders first.", "danger")
        else:
            flash(f"Error deleting bucket: {e}", "danger")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
    return redirect(url_for('index'))

@app.route('/upload/<bucket_name>', methods=['POST'])
def upload_file(bucket_name):
    """
    Handles file uploads to a specific S3 bucket.
    Allows specifying an optional 'key' (path/filename) for the uploaded file.
    Redirects back to the relevant folder view after upload.
    """
    if 'file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(request.referrer or url_for('list_bucket', bucket_name=bucket_name))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file.', 'danger')
        return redirect(request.referrer or url_for('list_bucket', bucket_name=bucket_name))

    key = request.form.get('key', file.filename).strip()
    if not key: # If user submits an empty optional key, use original filename
        key = file.filename
    
    try:
        s3.upload_fileobj(file, bucket_name, key)
        flash(f"File '{key}' uploaded successfully.", "success")
    except ClientError as e:
        flash(f"Error uploading file: {e}", "danger")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
    
    # Redirect to the folder where the file was uploaded
    parent_prefix = os.path.dirname(key)
    if parent_prefix and not parent_prefix.endswith('/'):
        parent_prefix += '/'
    return redirect(url_for('list_bucket', bucket_name=bucket_name, prefix=parent_prefix))


@app.route('/delete_file/<bucket_name>/<path:key>', methods=['POST'])
def delete_file(bucket_name, key):
    """
    Deletes a specific file (object) from an S3 bucket.
    Redirects back to the current folder view.
    """
    try:
        s3.delete_object(Bucket=bucket_name, Key=key)
        flash(f"File '{key}' deleted successfully.", "success")
    except ClientError as e:
        flash(f"Error deleting file: {e}", "danger")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
    
    # Redirect to the current folder view
    parent_prefix = os.path.dirname(key)
    if parent_prefix and not parent_prefix.endswith('/'):
        parent_prefix += '/'
    return redirect(url_for('list_bucket', bucket_name=bucket_name, prefix=parent_prefix))


@app.route('/delete_folder/<bucket_name>', methods=['POST'])
def delete_folder(bucket_name):
    """
    Deletes a "folder" (all objects sharing a common prefix) from an S3 bucket.
    S3 does not have true folders, so this operation deletes all objects that
    start with the given prefix.
    """
    prefix = request.form['prefix'].strip()
    
    # Ensure prefix ends with '/' if it's meant to be a folder prefix
    if prefix and not prefix.endswith('/'):
        prefix += '/'

    try:
        # List all objects with this prefix (including sub-files/folders)
        objects_to_delete = []
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        for page in pages:
            if 'Contents' in page:
                objects_to_delete.extend([{'Key': obj['Key']} for obj in page['Contents']])

        if not objects_to_delete:
            flash(f"Folder '{prefix}' is already empty or does not exist.", "warning")
        else:
            # S3's delete_objects can delete up to 1000 objects in one call.
            # For larger folders, you would need to loop and make multiple calls.
            # For this assignment, a single call is likely sufficient.
            s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects_to_delete})
            flash(f"Folder '{prefix}' and all its contents deleted successfully.", "success")

    except ClientError as e:
        flash(f"Error deleting folder: {e}", "danger")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
    
    # Redirect to the parent directory after deletion
    # This logic aims to go up one level from the deleted folder's parent
    parent_prefix = os.path.dirname(os.path.dirname(prefix.rstrip('/'))) # Go up two levels, e.g., 'a/b/' becomes 'a/'
    if parent_prefix:
        parent_prefix += '/'
    return redirect(url_for('list_bucket', bucket_name=bucket_name, prefix=parent_prefix))


@app.route('/create_folder/<bucket_name>', methods=['POST'])
def create_folder(bucket_name):
    """
    Creates a "folder" in S3 by creating a zero-byte object with a key ending in '/'.
    """
    folder_name = request.form['folder_name'].strip()
    if not folder_name:
        flash("Folder name cannot be empty.", "danger")
        # request.referrer provides the URL of the previous page
        return redirect(request.referrer or url_for('list_bucket', bucket_name=bucket_name))

    if not folder_name.endswith('/'):
        folder_name += '/'
    
    # Get current prefix to return to the same view (if the request came from a subfolder)
    current_prefix = request.args.get('current_prefix', '') 

    try:
        # Check if a folder/object with this key already exists
        # This is for better user feedback, put_object will just overwrite if it exists
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=folder_name, MaxKeys=1)
        if 'Contents' in response and response['Contents'][0]['Key'] == folder_name:
            flash(f"Folder '{folder_name}' already exists.", "warning")
        else:
            s3.put_object(Bucket=bucket_name, Key=folder_name)
            flash(f"Folder '{folder_name}' created successfully.", "success")
    except ClientError as e:
        flash(f"Error creating folder: {e}", "danger")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")

    return redirect(url_for('list_bucket', bucket_name=bucket_name, prefix=current_prefix))

@app.route('/copy_move/<bucket_name>', methods=['POST'])
def copy_move_file(bucket_name):
    """
    Copies or moves a file within the same S3 bucket.
    Moving is implemented as a copy followed by a delete of the source file.
    """
    source_key = request.form['source_key'].strip()
    destination_key = request.form['destination_key'].strip()
    operation = request.form['operation']  # 'copy' or 'move'

    if not source_key or not destination_key:
        flash("Source and destination keys cannot be empty.", "danger")
        return redirect(request.referrer or url_for('list_bucket', bucket_name=bucket_name))

    try:
        # Verify source object exists before attempting copy/move
        try:
            s3.head_object(Bucket=bucket_name, Key=source_key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                flash(f"Source file '{source_key}' does not exist.", "danger")
                return redirect(request.referrer or url_for('list_bucket', bucket_name=bucket_name))
            else:
                raise # Re-raise if it's another type of ClientError

        copy_source = {'Bucket': bucket_name, 'Key': source_key}
        s3.copy_object(CopySource=copy_source, Bucket=bucket_name, Key=destination_key)

        if operation == 'move':
            s3.delete_object(Bucket=bucket_name, Key=source_key)
            flash(f"File '{source_key}' moved to '{destination_key}' successfully.", "success")
        else: # operation == 'copy'
            flash(f"File '{source_key}' copied to '{destination_key}' successfully.", "success")
    except ClientError as e:
        flash(f"Error during {operation} operation: {e}", "danger")
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
    
    # Redirect to the current folder where the operation was initiated (based on source_key's parent)
    current_prefix = os.path.dirname(source_key)
    if current_prefix and not current_prefix.endswith('/'):
        current_prefix += '/'
    return redirect(url_for('list_bucket', bucket_name=bucket_name, prefix=current_prefix))

if __name__ == '__main__':
    # Run the Flask application.
    # debug=True enables reloader and debugger, useful for development.
    # In a production environment, set debug=False and use a WSGI server like Gunicorn or uWSGI.
    # host='0.0.0.0' makes the server accessible from other machines on the network.
    app.run(debug=True, host='0.0.0.0')