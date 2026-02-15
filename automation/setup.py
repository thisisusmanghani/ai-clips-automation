"""
Initial Setup Script.
Run this ONCE locally to authenticate and get tokens for GitHub Actions.
"""

import os
import sys
import json
import base64
import pickle
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from config import CLIENT_SECRETS_FILE, OAUTH_TOKEN_FILE, ALL_SCOPES, AUTOMATION_DIR


def setup_oauth():
    """Run OAuth flow and save token."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    print("=== OAuth Setup ===")
    print(f"Using client secrets: {CLIENT_SECRETS_FILE}")
    
    if not CLIENT_SECRETS_FILE.exists():
        print(f"ERROR: Client secrets file not found!")
        print(f"Expected at: {CLIENT_SECRETS_FILE}")
        return False
    
    # Run OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRETS_FILE), ALL_SCOPES
    )
    
    print("\nOpening browser for authentication...")
    print("Please sign in with your Google account that has the YouTube channel.\n")
    
    creds = flow.run_local_server(port=8080)
    
    # Save token
    os.makedirs(AUTOMATION_DIR, exist_ok=True)
    with open(OAUTH_TOKEN_FILE, 'wb') as token:
        pickle.dump(creds, token)
    
    print(f"\n✓ Token saved to: {OAUTH_TOKEN_FILE}")
    
    # Generate base64 for GitHub secrets
    with open(OAUTH_TOKEN_FILE, 'rb') as f:
        token_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    print("\n" + "="*60)
    print("GITHUB SECRETS TO SET:")
    print("="*60)
    
    # Read client secrets for GitHub
    with open(CLIENT_SECRETS_FILE, 'r') as f:
        client_secrets = json.load(f)
    
    secrets = {
        'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY', '<your-api-key>'),
        'GOOGLE_CLIENT_ID': client_secrets['installed']['client_id'],
        'GOOGLE_CLIENT_SECRET': client_secrets['installed']['client_secret'],
        'CLIENT_SECRETS_JSON': json.dumps(client_secrets),
        'OAUTH_TOKEN_PICKLE_B64': token_b64
    }
    
    for name, value in secrets.items():
        print(f"\n{name}:")
        if len(value) > 100:
            print(f"  {value[:50]}...{value[-20:]} (length: {len(value)})")
        else:
            print(f"  {value}")
    
    print("\n" + "="*60)
    print("QUICK SETUP COMMANDS (run in repository root):")
    print("="*60)
    print("""
gh secret set GOOGLE_API_KEY
gh secret set GOOGLE_CLIENT_ID
gh secret set GOOGLE_CLIENT_SECRET
gh secret set CLIENT_SECRETS_JSON < client_secret_path.json
gh secret set OAUTH_TOKEN_PICKLE_B64
""")
    
    return True


def test_youtube():
    """Test YouTube API connection."""
    print("\n=== Testing YouTube API ===")
    
    try:
        from youtube_uploader import YouTubeUploader
        uploader = YouTubeUploader()
        channel = uploader.get_channel_info()
        
        if channel:
            print(f"✓ Connected to channel: {channel.get('title')}")
            print(f"  Channel ID: {channel.get('id')}")
            print(f"  Subscribers: {channel.get('subscribers')}")
            return True
        else:
            print("✗ Could not get channel info")
            return False
    except Exception as e:
        print(f"✗ YouTube test failed: {e}")
        return False


def test_sheets():
    """Test Google Sheets connection."""
    print("\n=== Testing Google Sheets ===")
    
    try:
        from sheets_tracker import SheetsTracker
        tracker = SheetsTracker()
        sheet_id = tracker.setup_spreadsheet()
        
        print(f"✓ Spreadsheet ready: https://docs.google.com/spreadsheets/d/{sheet_id}")
        
        # Save spreadsheet ID to .env
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path, 'r') as f:
                content = f.read()
            
            if 'SPREADSHEET_ID=' in content:
                import re
                content = re.sub(r'SPREADSHEET_ID=.*', f'SPREADSHEET_ID={sheet_id}', content)
            else:
                content += f'\nSPREADSHEET_ID={sheet_id}'
            
            with open(env_path, 'w') as f:
                f.write(content)
            
            print(f"✓ Updated .env with SPREADSHEET_ID")
        
        return sheet_id
    except Exception as e:
        print(f"✗ Sheets test failed: {e}")
        return None


def main():
    """Run full setup."""
    print("="*60)
    print("YouTube Automation Pipeline - Initial Setup")
    print("="*60)
    
    # Step 1: OAuth
    if not OAUTH_TOKEN_FILE.exists():
        print("\nStep 1: OAuth Authentication")
        if not setup_oauth():
            return
    else:
        print(f"\n✓ OAuth token exists: {OAUTH_TOKEN_FILE}")
    
    # Step 2: Test YouTube
    print("\nStep 2: Testing YouTube Connection")
    test_youtube()
    
    # Step 3: Test Sheets
    print("\nStep 3: Testing Google Sheets")
    sheet_id = test_sheets()
    
    # Summary
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("""
Next steps:
1. Set GitHub secrets (see above)
2. Push to GitHub: git push origin main
3. Enable GitHub Actions in repository settings
4. Manually trigger first upload: gh workflow run daily-upload.yml

Or test locally:
  python automation/pipeline.py --count 1 --no-schedule
""")


if __name__ == "__main__":
    main()
