#!/usr/bin/env python3
"""
Check S3 for recently processed files to verify .log extension
"""

import boto3
from datetime import datetime, timedelta
import pytz

# S3 client
s3 = boto3.client('s3')

# Bucket name
PROCESSED_BUCKET = 'redact-processed-documents-32a4ee51'

def check_recent_files(hours=24):
    """Check for files processed in the last N hours"""
    cutoff_time = datetime.now(pytz.UTC) - timedelta(hours=hours)
    
    print(f"Checking for files processed after: {cutoff_time}")
    print("=" * 60)
    
    try:
        # List objects in processed bucket
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(
            Bucket=PROCESSED_BUCKET,
            Prefix='processed/'
        )
        
        recent_files = []
        all_files_count = 0
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    all_files_count += 1
                    if obj['LastModified'] > cutoff_time:
                        recent_files.append(obj)
        
        print(f"Total files in bucket: {all_files_count}")
        print(f"Files processed in last {hours} hours: {len(recent_files)}")
        print()
        
        if recent_files:
            print("Recent files:")
            print("-" * 60)
            
            log_files = 0
            txt_files = 0
            other_files = 0
            
            for file in sorted(recent_files, key=lambda x: x['LastModified'], reverse=True)[:20]:
                filename = file['Key'].split('/')[-1]
                timestamp = file['LastModified'].strftime('%Y-%m-%d %H:%M:%S UTC')
                size = file['Size']
                
                # Check extension
                if filename.endswith('.log'):
                    log_files += 1
                    ext_marker = "✓ .log"
                elif filename.endswith('.txt'):
                    txt_files += 1
                    ext_marker = "✗ .txt"
                else:
                    other_files += 1
                    ext_marker = "? other"
                
                print(f"{timestamp} | {ext_marker} | {size:>8} bytes | {filename}")
            
            print("\nExtension Summary:")
            print(f"  .log files: {log_files}")
            print(f"  .txt files: {txt_files}")
            print(f"  Other: {other_files}")
            
            if log_files > 0 and txt_files == 0:
                print("\n✓ SUCCESS: All recent files use .log extension!")
            elif txt_files > 0:
                print("\n⚠️  WARNING: Some files still using .txt extension")
                print("   The Lambda function may need to be redeployed.")
        else:
            print("No files processed in the specified time period.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    check_recent_files(hours)