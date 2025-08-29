import json
import base64
import os
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.auth import get_current_user
from models.user import Profile
from services.gmail_service import gmail_service, GmailConfig

router = APIRouter(prefix="/api/gmail", tags=["gmail"])

@router.get("/oauth/url")
async def get_gmail_oauth_url(
    current_user: Profile = Depends(get_current_user)
):
    """Generate Gmail OAuth URL for admin to connect Gmail account"""
    
    # Only admins can configure Gmail
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can configure Gmail integration"
        )
    
    try:
        oauth_url = await gmail_service.generate_oauth_url(
            user_id=str(current_user.id),
            company_id=str(current_user.company_id)
        )
        
        return {
            "success": True,
            "oauth_url": oauth_url,
            "message": "Redirect user to this URL to authorize Gmail access"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate OAuth URL: {str(e)}"
        )

@router.get("/oauth/callback")
async def gmail_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter with user info"),
    error: Optional[str] = Query(None, description="Error from OAuth"),
    db: AsyncSession = Depends(get_db)
):
    """Handle Gmail OAuth callback from Google"""
    
    # Check for OAuth errors
    if error:
        # Load and return error HTML page
        html_path = os.path.join(os.path.dirname(__file__), 'oauth_success.html')
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Replace success content with error content
        html_content = html_content.replace('✅', '❌')
        html_content = html_content.replace('Gmail Connected Successfully!', 'Gmail Connection Failed')
        html_content = html_content.replace('Your Gmail account has been connected.', f'OAuth error: {error}')
        
        error_url = f"http://localhost:5173/email-config?error={error}"
        html_content = html_content.replace('/email-config', error_url)
        
        return HTMLResponse(content=html_content, status_code=200)
    
    try:
        # Decode state parameter
        state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
        user_id = state_data['user_id']
        company_id = state_data['company_id']
        
        # Exchange code for tokens
        tokens = await gmail_service.exchange_code_for_tokens(code)
        
        # Get user's Gmail information
        user_info = await gmail_service.get_user_info(tokens['access_token'])
        
        # Test Gmail connection
        connection_ok = await gmail_service.test_gmail_connection(tokens['access_token'])
        if not connection_ok:
            raise Exception("Failed to connect to Gmail API")
        
        # Save Gmail configuration
        config = await gmail_service.save_gmail_config(
            db=db,
            user_id=user_id,
            company_id=company_id,
            gmail_address=user_info['email'],
            display_name=user_info.get('name', user_info['email']),
            tokens=tokens
        )
        
        # Load and return success HTML page
        html_path = os.path.join(os.path.dirname(__file__), 'oauth_success.html')
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Get the frontend URL from environment or use a default
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        print(f"🔍 [Backend OAuth] Frontend URL: {frontend_url}")
        
        # Inject the success data directly into the HTML
        html_content = html_content.replace('const success = urlParams.get(\'success\');', f'const success = \'true\';')
        html_content = html_content.replace('const email = urlParams.get(\'email\');', f'const email = \'{user_info["email"]}\';')
        html_content = html_content.replace('const error = urlParams.get(\'error\');', 'const error = null;')
        
        print(f"🔍 [Backend OAuth] Injected success=true, email={user_info['email']}")
        print(f"🔍 [Backend OAuth] Returning HTML response with success")
        return HTMLResponse(content=html_content, status_code=200)
        
    except Exception as e:
        print(f"Gmail OAuth callback error: {e}")
        
        # Load and return error HTML page
        html_path = os.path.join(os.path.dirname(__file__), 'oauth_success.html')
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Get the frontend URL from environment or use a default
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        print(f"🔍 [Backend OAuth] Error case - Frontend URL: {frontend_url}")
        
        # Replace success content with error content
        html_content = html_content.replace('✅', '❌')
        html_content = html_content.replace('Gmail Connected Successfully!', 'Gmail Connection Failed')
        html_content = html_content.replace('Your Gmail account has been connected.', 'Failed to connect your Gmail account.')
        
        # Inject the error data directly into the HTML
        html_content = html_content.replace('const success = urlParams.get(\'success\');', 'const success = \'false\';')
        html_content = html_content.replace('const email = urlParams.get(\'email\');', 'const email = null;')
        html_content = html_content.replace('const error = urlParams.get(\'error\');', 'const error = \'callback_failed\';')
        
        print(f"🔍 [Backend OAuth] Injected success=false, error=callback_failed")
        print(f"🔍 [Backend OAuth] Returning HTML response with error")
        return HTMLResponse(content=html_content, status_code=200)

@router.get("/configs", response_model=List[dict])
async def get_gmail_configs(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all Gmail configurations for the current company"""
    
    try:
        configs = await gmail_service.get_company_gmail_configs(
            db=db,
            company_id=str(current_user.company_id)
        )
        
        # Convert to dict format for response
        config_list = []
        for config in configs:
            config_dict = {
                "id": str(config.id),
                "gmail_address": config.gmail_address,
                "display_name": config.display_name,
                "is_active": config.is_active,
                "last_sync": config.last_sync.isoformat() if config.last_sync else None,
                "sync_frequency_minutes": config.sync_frequency_minutes,
                "granted_scopes": config.granted_scopes,
                "created_at": config.created_at.isoformat(),
                "updated_at": config.updated_at.isoformat()
            }
            config_list.append(config_dict)
        
        return config_list
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Gmail configurations: {str(e)}"
        )

@router.post("/configs/{config_id}/test")
async def test_gmail_config(
    config_id: str,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test Gmail configuration connection"""
    
    # Only admins can test configurations
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can test Gmail configurations"
        )
    
    try:
        # Get configuration with decrypted tokens
        config = await gmail_service.get_gmail_config_by_id(db, config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gmail configuration not found"
            )
        
        # Test connection
        connection_ok = await gmail_service.test_gmail_connection(config.access_token)
        
        return {
            "success": True,
            "connected": connection_ok,
            "gmail_address": config.gmail_address,
            "message": "Connection successful" if connection_ok else "Connection failed"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test Gmail configuration: {str(e)}"
        )

@router.delete("/configs/{config_id}")
async def delete_gmail_config(
    config_id: str,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete Gmail configuration"""
    
    # Only admins can delete configurations
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete Gmail configurations"
        )
    
    try:
        from sqlalchemy import text
        
        # Soft delete by setting is_active to false
        result = await db.execute(
            text("UPDATE gmail_configs SET is_active = false, updated_at = NOW() WHERE id = :config_id AND company_id = :company_id"),
            {'config_id': config_id, 'company_id': str(current_user.company_id)}
        )
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gmail configuration not found"
            )
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Gmail configuration deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete Gmail configuration: {str(e)}"
        )

@router.post("/configs/{config_id}/toggle")
async def toggle_gmail_config(
    config_id: str,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle Gmail configuration active status"""
    
    # Only admins can toggle configurations
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can toggle Gmail configurations"
        )
    
    try:
        from sqlalchemy import text
        
        # Toggle is_active status
        result = await db.execute(
            text("""
                UPDATE gmail_configs 
                SET is_active = NOT is_active, updated_at = NOW() 
                WHERE id = :config_id AND company_id = :company_id
                RETURNING is_active
            """),
            {'config_id': config_id, 'company_id': str(current_user.company_id)}
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gmail configuration not found"
            )
        
        await db.commit()
        
        return {
            "success": True,
            "is_active": row[0],
            "message": f"Gmail configuration {'activated' if row[0] else 'deactivated'}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle Gmail configuration: {str(e)}"
        )
