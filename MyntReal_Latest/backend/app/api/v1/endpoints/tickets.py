"""
Support Ticketing System API Endpoints
User and Admin ticket management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, File, UploadFile, Body, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_hybrid, get_current_admin_user
from app.models.user import User
from app.models.staff_accounts import OfficialPartner
from app.models.ticket import ServiceTicket, TicketComment, ServiceTicketPartnerHistory, TicketLog


from app.schemas.ticket import (
    TicketCreate, TicketResponse, TicketDetailResponse, TicketUpdate,
    TicketAssign, TicketResolve, TicketClose,
    CommentCreate, CommentResponse,
    TicketTimelineResponse, TicketTimelineStats,
    ServiceTicketAcknowledge, ServiceTicketDiagnose, ServiceTicketComplete, ServiceTicketClose
)
from app.services.ticket_service import TicketService
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/tickets", tags=["Support Tickets"])


from app.api.v1.endpoints.partner_auth import get_current_partner as get_current_partner_dependency


# ===== USER ENDPOINTS =====

@router.post("/create", response_model=TicketResponse)
async def create_ticket(
    ticket_data: TicketCreate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Create new support ticket (User)"""
    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    
    ticket = TicketService.create_ticket(
        db=db,
        user_id=current_user.id,
        issue_category=ticket_data.issue_category,
        issue_description=ticket_data.issue_description,
        priority=ticket_data.priority,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return ticket


@router.get("/my-tickets", response_model=List[TicketResponse])
async def get_my_tickets(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get all tickets for current user"""
    tickets = TicketService.get_user_tickets(
        db=db,
        user_id=current_user.id,
        status_filter=status
    )
    return tickets


@router.get("/service-centers")
async def get_service_centers_list(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get list of service centers/partners for filter dropdown"""
    from app.models.staff_accounts import OfficialPartner
    
    try:
        partners = db.query(OfficialPartner).filter(
            OfficialPartner.is_active == True
        ).order_by(OfficialPartner.partner_name).all()
        
        return [
            {
                "id": p.id,
                "name": p.partner_name,
                "partner_name": p.partner_name,
                "category": p.category,
                "city": getattr(p, 'city', None)
            }
            for p in partners
        ]
    except Exception as e:
        return []


@router.get("/partners")
async def get_partners_list(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get partners filtered by category and/or search term
    
    DC Protocol Jan 2026: Enhanced to support all partner types for service tickets
    - category: Optional filter (dealer, distributor, vendor, service_center, or 'all'/None for all)
    - search: Optional search term for partner name, code, or contact
    """
    from app.models.staff_accounts import OfficialPartner
    from sqlalchemy import or_
    
    query = db.query(OfficialPartner).filter(OfficialPartner.is_active == True)
    
    # Category filter (skip if 'all' or empty)
    if category and category.lower() != 'all':
        query = query.filter(OfficialPartner.category.ilike(f"%{category}%"))
    
    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                OfficialPartner.partner_name.ilike(search_term),
                OfficialPartner.partner_code.ilike(search_term),
                OfficialPartner.contact_person.ilike(search_term),
                OfficialPartner.phone.ilike(search_term)
            )
        )
    
    partners = query.order_by(OfficialPartner.partner_name).limit(100).all()
    
    # DC Protocol: Return partner type label for badge display
    category_labels = {
        'DEALER': 'Dealer',
        'DISTRIBUTOR': 'Distributor',
        'VENDOR': 'Vendor',
        'SERVICE_CENTER': 'Service Center',
        'REAL_DREAM_PARTNER': 'Real Dreams'
    }
    
    return [
        {
            "id": p.id,
            "partner_code": p.partner_code,
            "partner_name": p.partner_name,
            "category": p.category,
            "category_label": category_labels.get(p.category, p.category),
            "contact_person": getattr(p, 'contact_person', None),
            "phone": getattr(p, 'phone', None),
            "city": getattr(p, 'city', None),
            "state": getattr(p, 'state', None)
        }
        for p in partners
    ]


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket_details(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get ticket details with comments and history"""
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Verify user has access (owner, admin, or staff)
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    is_admin = hasattr(current_user, 'is_admin') and callable(getattr(current_user, 'is_admin', None)) and current_user.is_admin()
    if ticket.user_id != current_user.id and not is_admin and not is_staff:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ticket


@router.post("/{ticket_id}/comment", response_model=CommentResponse)
async def add_comment(
    ticket_id: int,
    comment: CommentCreate = Body(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Add comment to ticket"""
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Verify user has access (owner, admin, or staff)
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    is_admin = hasattr(current_user, 'is_admin') and callable(getattr(current_user, 'is_admin', None)) and current_user.is_admin()
    if ticket.user_id != current_user.id and not is_admin and not is_staff:
        raise HTTPException(status_code=403, detail="Access denied")
    
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Determine comment type
    comment_type = 'admin_response' if is_admin or is_staff else 'user_response'
    
    new_comment = TicketService.add_comment(
        db=db,
        ticket_id=ticket_id,
        user_id=current_user.id,
        comment_text=comment.comment_text,
        comment_type=comment_type,
        is_internal=False,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return new_comment


@router.post("/{ticket_id}/close")
async def close_ticket(
    ticket_id: int,
    close_data: TicketClose,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Close resolved ticket (User)"""
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    _force = close_data.force_close
    if _force:
        _is_admin = hasattr(current_user, 'is_admin') and callable(getattr(current_user, 'is_admin', None)) and current_user.is_admin()
        if not _is_admin:
            raise HTTPException(status_code=403, detail="Only admins can force-close tickets with pending spares")
    
    result = TicketService.close_ticket(
        db=db,
        ticket_id=ticket_id,
        closed_by=current_user.id,
        customer_satisfaction=close_data.customer_satisfaction,
        force_close=_force
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/{ticket_id}/upload-attachment")
async def upload_ticket_attachment(
    ticket_id: int,
    attachment: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Upload attachment to ticket (Universal Upload: max 5 MB, auto-compression)
    Available to ticket owner and admins
    """
    from app.models.ticket import TicketAttachment
    
    # Verify ticket exists
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Verify user has access (owner, admin, or staff)
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    is_admin = hasattr(current_user, 'is_admin') and callable(getattr(current_user, 'is_admin', None)) and current_user.is_admin()
    if ticket.user_id != current_user.id and not is_admin and not is_staff:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # DC Protocol: Validate file size BEFORE creating DB records
    file_content = await attachment.read()
    file_size = len(file_content)
    attachment.file.seek(0)  # Reset for UniversalUploadService (synchronous seek)
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Universal Upload System: Type-specific limits (aligned with UniversalUploadService)
    mime_type = attachment.content_type or 'application/octet-stream'
    is_video = mime_type.startswith('video/')
    
    MAX_IMAGE_SIZE = 5 * 1024 * 1024    # 5MB for images
    MAX_VIDEO_SIZE = 20 * 1024 * 1024   # 20MB for videos (ffmpeg compressed)
    
    max_size = MAX_VIDEO_SIZE if is_video else MAX_IMAGE_SIZE
    max_label = "20MB" if is_video else "5MB"
    
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({round(file_size/(1024*1024), 2)}MB) exceeds maximum allowed size ({max_label})"
        )
    
    # Universal Upload System: DC Protocol atomic transaction
    from app.services.universal_upload_service import UniversalUploadService
    
    try:
        # Create attachment record first to get ID
        ticket_attachment = TicketAttachment(
            ticket_id=ticket_id,
            file_path="pending",  # Temporary
            original_filename=attachment.filename,
            file_size=file_size,
            mime_type=attachment.content_type or 'application/octet-stream',
            uploaded_by=current_user.id,
            is_scanned=False,
            scan_status='Pending'
        )
        db.add(ticket_attachment)
        db.flush()  # Get attachment ID
        
        # Upload file using Universal Upload System
        # DC Protocol: defer_scheduler=True ensures compression job only scheduled AFTER db.commit()
        upload_result = await UniversalUploadService.handle_upload(
            file=attachment,
            table_name='ticket_attachment',
            record_id=ticket_attachment.id,
            uploaded_by_id=current_user.id,
            uploaded_by_type='user',
            storage_dir=f'ticket_attachments/{ticket_id}',
            db=db,
            defer_scheduler=True  # DC: Transaction safety - schedule job AFTER commit
        )
        
        # Update attachment with file path
        ticket_attachment.file_path = upload_result['file_path']
        
        # DC PROTOCOL: Generate semantic download filename (NEW - Nov 29, 2025)
        try:
            import pytz
            from datetime import datetime
            
            ist_tz = pytz.timezone('Asia/Kolkata')
            uploaded_at_ist = datetime.now(ist_tz)
            
            download_name = UniversalUploadService.generate_download_filename(
                segment_key='ticket_attachment',
                entity_type='ticket',
                entity_id=ticket_id,
                attachment_id=ticket_attachment.id,
                uploader_code=current_user.id,  # User.id IS the MNR ID
                original_filename=attachment.filename,
                uploaded_at=uploaded_at_ist
            )
            
            ticket_attachment.download_filename = download_name
            ticket_attachment.uses_new_naming = True
        except HTTPException:
            raise
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to generate download filename for ticket {ticket_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate semantic filename: {str(e)}")
        
        # Log ticket action
        from app.models.ticket import TicketLog
        from datetime import datetime as dt
        user_id_str = str(current_user.id) if current_user else None
        log = TicketLog(
            ticket_id=ticket_id,
            action_type='Updated',
            action_description='File attached',
            performed_by=user_id_str if user_id_str and user_id_str.startswith('MNR') else None,
            performed_at=dt.utcnow(),
            old_value=None,
            new_value=upload_result['file_name'],
            comments=f"Uploaded: {attachment.filename}"
        )
        db.add(log)
        
        # DC Protocol: Single commit for ALL changes (atomic operation)
        # PostCommitScheduler will automatically enqueue deferred jobs AFTER this commit
        db.commit()
        db.refresh(ticket_attachment)
        
        return {
            "success": True,
            "message": "Attachment uploaded successfully",
            "attachment": {
                "id": ticket_attachment.id,
                "file_name": upload_result['file_name'],
                "original_filename": ticket_attachment.original_filename,
                "file_size": ticket_attachment.file_size,
                "uploaded_at": ticket_attachment.uploaded_at.isoformat()
            }
        }
        
    except HTTPException as e:
        # DC PROTOCOL: Preserve validation errors
        db.rollback()
        raise e
    except Exception as upload_error:
        # DC Protocol: Transaction rollback
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to upload attachment: {str(upload_error)}"
        )


# ===== DC PROTOCOL JAN 2026: MULTI-MEDIA UPLOAD FOR SERVICE TICKETS =====

@router.post("/service/{ticket_id}/upload-media")
async def upload_service_ticket_media(
    ticket_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Upload media (images/video) to service ticket with compression.
    DC Protocol Jan 2026: Supports up to 10 images OR 1 video (max 3 mins).
    
    Limits:
    - Images: Max 10 files, each max 10MB (compressed to ~500KB)
    - Video: Max 1 file, max 50MB, max 3 minutes (compressed to ~8MB)
    """
    from app.models.ticket import TicketAttachment, TicketLog
    from app.services.universal_upload_service import UniversalUploadService
    from app.core.security import get_current_staff_user_from_hybrid
    
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    is_staff = staff is not None
    
    existing_attachments = db.query(TicketAttachment).filter(
        TicketAttachment.ticket_id == ticket_id
    ).count()
    
    MAX_IMAGES = 10
    MAX_VIDEO_COUNT = 1
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB per image
    MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB per video
    MAX_VIDEO_DURATION = 180  # 3 minutes in seconds
    
    has_video = False
    image_count = 0
    uploaded_media = []
    
    for file in files:
        mime_type = file.content_type or 'application/octet-stream'
        is_video = mime_type.startswith('video/')
        is_image = mime_type.startswith('image/')
        
        if not is_video and not is_image:
            raise HTTPException(status_code=400, detail=f"File {file.filename} must be an image or video")
        
        file_content = await file.read()
        file_size = len(file_content)
        await file.seek(0)
        
        if is_video:
            if has_video:
                raise HTTPException(status_code=400, detail="Only 1 video allowed per ticket")
            if existing_attachments > 0:
                existing_videos = db.query(TicketAttachment).filter(
                    TicketAttachment.ticket_id == ticket_id,
                    TicketAttachment.media_type == 'video'
                ).count()
                if existing_videos > 0:
                    raise HTTPException(status_code=400, detail="Ticket already has a video attachment")
            if file_size > MAX_VIDEO_SIZE:
                raise HTTPException(status_code=400, detail=f"Video {file.filename} exceeds 50MB limit")
            has_video = True
        else:
            image_count += 1
            if existing_attachments + image_count > MAX_IMAGES:
                raise HTTPException(status_code=400, detail=f"Maximum {MAX_IMAGES} images allowed per ticket")
            if file_size > MAX_IMAGE_SIZE:
                raise HTTPException(status_code=400, detail=f"Image {file.filename} exceeds 10MB limit")
        
        if has_video and image_count > 0:
            raise HTTPException(status_code=400, detail="Cannot upload both video and images in same request")
    
    for file in files:
        try:
            await file.seek(0)
            file_content = await file.read()
            file_size = len(file_content)
            await file.seek(0)
            
            mime_type = file.content_type or 'application/octet-stream'
            is_video = mime_type.startswith('video/')
            media_type = 'video' if is_video else 'image'
            
            attachment = TicketAttachment(
                ticket_id=ticket_id,
                file_path="pending",
                original_filename=file.filename,
                file_size=file_size,
                mime_type=mime_type,
                media_type=media_type,
                uploaded_by=current_user.id if hasattr(current_user, 'id') and isinstance(current_user.id, str) else None,
                uploaded_by_staff_id=staff.id if staff else None,
                is_scanned=False,
                scan_status='Pending',
                processing_status='pending'
            )
            db.add(attachment)
            db.flush()
            
            upload_result = await UniversalUploadService.handle_upload(
                file=file,
                table_name='ticket_attachment',
                record_id=attachment.id,
                uploaded_by_id=staff.id if staff else current_user.id,
                uploaded_by_type='staff' if staff else 'user',
                storage_dir=f'service_ticket_media/{ticket_id}',
                db=db,
                defer_scheduler=True
            )
            
            attachment.file_path = upload_result['file_path']
            attachment.original_checksum = upload_result.get('original_checksum')
            attachment.processing_status = 'pending' if upload_result.get('needs_compression') else 'completed'
            
            import pytz
            ist_tz = pytz.timezone('Asia/Kolkata')
            uploaded_at_ist = datetime.now(ist_tz)
            
            download_name = UniversalUploadService.generate_download_filename(
                segment_key='service_media',
                entity_type='ticket',
                entity_id=ticket_id,
                attachment_id=attachment.id,
                uploader_code=staff.emp_code if staff else str(current_user.id),
                original_filename=file.filename,
                uploaded_at=uploaded_at_ist
            )
            attachment.download_filename = download_name
            attachment.uses_new_naming = True
            
            uploaded_media.append(attachment.to_dict())
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Failed to upload {file.filename}: {str(e)}")
    
    log = TicketLog(
        ticket_id=ticket_id,
        action_type='media_uploaded',
        action_description=f'{len(uploaded_media)} media file(s) uploaded',
        staff_performer_id=staff.id if staff else None,
        performed_by=current_user.id if hasattr(current_user, 'id') and isinstance(current_user.id, str) else None
    )
    db.add(log)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"{len(uploaded_media)} media file(s) uploaded successfully",
        "media": uploaded_media
    }


@router.get("/service/{ticket_id}/media")
async def get_service_ticket_media(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get all media attachments for a service ticket.
    DC Protocol: Returns compressed file paths where available.
    """
    from app.models.ticket import TicketAttachment
    
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    attachments = db.query(TicketAttachment).filter(
        TicketAttachment.ticket_id == ticket_id,
        TicketAttachment.media_type.in_(['image', 'video'])
    ).order_by(TicketAttachment.uploaded_at.desc()).all()
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "media": [att.to_dict() for att in attachments],
        "counts": {
            "images": sum(1 for a in attachments if a.media_type == 'image'),
            "videos": sum(1 for a in attachments if a.media_type == 'video')
        }
    }


@router.get("/{ticket_id}/attachment/{attachment_id}")
async def get_ticket_attachment(
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Retrieve ticket attachment file
    Access: Ticket owner and admins
    """
    from pathlib import Path
    from fastapi.responses import FileResponse
    from app.models.ticket import TicketAttachment
    
    # Verify ticket exists
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Verify user has access (owner, admin, or staff)
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    is_admin = hasattr(current_user, 'is_admin') and callable(getattr(current_user, 'is_admin', None)) and current_user.is_admin()
    if ticket.user_id != current_user.id and not is_admin and not is_staff:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get attachment
    attachment = db.query(TicketAttachment).filter(
        TicketAttachment.id == attachment_id,
        TicketAttachment.ticket_id == ticket_id
    ).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Build file path
    file_path = Path(attachment.file_path)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found")
    
    # Determine content type
    ext = attachment.original_filename.rsplit('.', 1)[-1].lower() if '.' in attachment.original_filename else ''
    content_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain'
    }
    media_type = content_types.get(ext, attachment.mime_type)
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=attachment.original_filename
    )


@router.get("/{ticket_id}/attachments")
async def list_ticket_attachments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    List all attachments for a ticket
    DC Protocol Jan 2026: View Attachments feature
    """
    from app.models.ticket import TicketAttachment
    
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    attachments = db.query(TicketAttachment).filter(
        TicketAttachment.ticket_id == ticket_id
    ).order_by(TicketAttachment.uploaded_at.desc()).all()
    
    return {
        "ticket_id": ticket_id,
        "ticket_number": ticket.ticket_id,
        "attachments": [
            {
                "id": att.id,
                "original_filename": att.original_filename,
                "file_size": att.file_size,
                "mime_type": att.mime_type,
                "uploaded_at": att.uploaded_at.isoformat() if att.uploaded_at else None,
                "url": f"/api/v1/tickets/{ticket_id}/attachment/{att.id}"
            }
            for att in attachments
        ]
    }


# ===== ADMIN ENDPOINTS =====

@router.get("/admin/all", response_model=List[TicketResponse])
async def get_all_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all tickets (Admin)"""
    tickets = TicketService.get_admin_tickets(
        db=db,
        status_filter=status,
        priority_filter=priority,
        assigned_to=assigned_to
    )
    return tickets


@router.post("/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: int,
    assignment: TicketAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Assign ticket to admin (Admin)"""
    result = TicketService.assign_ticket(
        db=db,
        ticket_id=ticket_id,
        assigned_to=assignment.assigned_to,
        assigned_by=current_user.id,
        reason=assignment.assignment_reason
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.put("/{ticket_id}/update")
async def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update ticket details (Admin)"""
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Update fields
    _update_fields = ticket_update.dict(exclude_unset=True)
    for key, value in _update_fields.items():
        setattr(ticket, key, value)

    # [DC_DAR_003 / Task #53] If any assignment-bearing field was touched,
    # recompute company_id and assign unconditionally (even None) so a
    # cleared/orphaned assignment never retains a stale company tag.
    if any(k in _update_fields for k in ('partner_id', 'service_manager_id', 'service_technician_id')):
        from app.services.ticket_service import _derive_ticket_company_id
        ticket.company_id = _derive_ticket_company_id(
            db,
            service_technician_id=ticket.service_technician_id,
            service_manager_id=ticket.service_manager_id,
            partner_id=ticket.partner_id,
        )

    db.commit()
    db.refresh(ticket)
    
    return {"success": True, "message": "Ticket updated successfully"}


@router.post("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: int,
    resolution: TicketResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Resolve ticket (Admin)"""
    result = TicketService.resolve_ticket(
        db=db,
        ticket_id=ticket_id,
        resolved_by=current_user.id,
        resolution_summary=resolution.resolution_summary,
        admin_response=resolution.admin_response
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.put("/{ticket_id}/reassign-partner")
async def reassign_partner(
    ticket_id: int,
    request: Request,
    new_partner_id: int = Body(...),
    change_reason: str = Body(..., min_length=5),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Reassign ticket to a different business partner
    Creates audit trail in ServiceTicketPartnerHistory
    Reason is mandatory for accountability
    """
    from app.models.staff_accounts import OfficialPartner, StaffEmployee
    
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    new_partner = db.query(OfficialPartner).filter(OfficialPartner.id == new_partner_id).first()
    if not new_partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    old_partner_id = ticket.partner_id
    
    if old_partner_id == new_partner_id:
        raise HTTPException(status_code=400, detail="Ticket is already assigned to this partner")
    
    staff_id = None
    user_id_str = None
    if hasattr(current_user, 'emp_code') and current_user.emp_code:
        staff_id = current_user.id
    else:
        user_id_str = current_user.id
    
    history_record = ServiceTicketPartnerHistory(
        ticket_id=ticket.id,
        old_partner_id=old_partner_id,
        new_partner_id=new_partner_id,
        change_reason=change_reason,
        changed_by_staff_id=staff_id,
        changed_by_user_id=user_id_str,
        ip_address=request.client.host if request.client else None
    )
    db.add(history_record)
    
    ticket.partner_id = new_partner_id

    # [DC_DAR_003 / Task #53] Recompute company_id and assign uncondi-
    # tionally (even None) so DAR counts move to the new partner's company
    # and never retain a stale tag.
    from app.services.ticket_service import _derive_ticket_company_id
    ticket.company_id = _derive_ticket_company_id(
        db,
        service_technician_id=ticket.service_technician_id,
        service_manager_id=ticket.service_manager_id,
        partner_id=new_partner_id,
    )

    db.commit()
    
    return {
        "success": True,
        "message": f"Partner reassigned to {new_partner.partner_name}",
        "old_partner_id": old_partner_id,
        "new_partner_id": new_partner_id,
        "history_id": history_record.id
    }


@router.get("/{ticket_id}/partner-history")
async def get_partner_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get partner reassignment history for a ticket"""
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    history = db.query(ServiceTicketPartnerHistory).filter(
        ServiceTicketPartnerHistory.ticket_id == ticket_id
    ).order_by(ServiceTicketPartnerHistory.changed_at.desc()).all()
    
    return {
        "ticket_id": ticket_id,
        "history": [h.to_dict() for h in history],
        "count": len(history)
    }


@router.put("/{ticket_id}/reassign-staff")
async def reassign_staff(
    ticket_id: int,
    request: Request,
    service_manager_id: Optional[int] = Body(None, description="New service manager ID"),
    service_technician_id: Optional[int] = Body(None, description="New service technician ID"),
    reason: str = Body(..., min_length=3, description="Reason for reassignment"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Reassign ticket to different staff (manager/technician)
    DC Protocol Jan 2026: Allows reporting managers to change assigned staff
    Creates audit trail in ticket_log
    """
    from app.models.staff import StaffEmployee
    
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if not service_manager_id and not service_technician_id:
        raise HTTPException(status_code=400, detail="At least one staff ID (manager or technician) is required")
    
    changes = []
    old_values = {}
    new_values = {}
    
    if service_manager_id is not None:
        new_manager = db.query(StaffEmployee).filter(StaffEmployee.id == service_manager_id).first()
        if not new_manager:
            raise HTTPException(status_code=404, detail="Manager not found")
        old_values['service_manager_id'] = ticket.service_manager_id
        old_values['service_manager_name'] = ticket.service_manager.full_name if ticket.service_manager else None
        ticket.service_manager_id = service_manager_id
        new_values['service_manager_id'] = service_manager_id
        new_values['service_manager_name'] = new_manager.full_name
        changes.append(f"Manager changed to {new_manager.full_name}")
    
    if service_technician_id is not None:
        new_technician = db.query(StaffEmployee).filter(StaffEmployee.id == service_technician_id).first()
        if not new_technician:
            raise HTTPException(status_code=404, detail="Technician not found")
        old_values['service_technician_id'] = ticket.service_technician_id
        old_values['service_technician_name'] = ticket.service_technician.full_name if ticket.service_technician else None
        ticket.service_technician_id = service_technician_id
        new_values['service_technician_id'] = service_technician_id
        new_values['service_technician_name'] = new_technician.full_name
        changes.append(f"Technician changed to {new_technician.full_name}")
    
    staff_id = None
    user_id_str = None
    performer_name = "Unknown"
    if hasattr(current_user, 'emp_code') and current_user.emp_code:
        staff_id = current_user.id
        performer_name = current_user.full_name if hasattr(current_user, 'full_name') else current_user.emp_code
    else:
        user_id_str = current_user.id
        performer_name = current_user.name if hasattr(current_user, 'name') else user_id_str
    
    log_entry = TicketLog(
        ticket_id=ticket.id,
        action_type='Staff Reassigned',
        action_description=f"{'; '.join(changes)}. Reason: {reason}",
        performed_by=user_id_str,
        staff_performer_id=staff_id,
        old_value=str(old_values),
        new_value=str(new_values),
        ip_address=request.client.host if request.client else None
    )
    db.add(log_entry)

    # [DC_DAR_003 / Task #53] Recompute company_id and assign uncondi-
    # tionally (even None) so DAR counts follow the reassignment and never
    # retain a stale tag from a prior assignment.
    from app.services.ticket_service import _derive_ticket_company_id
    ticket.company_id = _derive_ticket_company_id(
        db,
        service_technician_id=ticket.service_technician_id,
        service_manager_id=ticket.service_manager_id,
        partner_id=ticket.partner_id,
    )

    db.commit()
    db.refresh(ticket)
    
    return {
        "success": True,
        "message": f"Staff reassigned successfully: {'; '.join(changes)}",
        "ticket_id": ticket.id,
        "changes": changes,
        "service_manager_id": ticket.service_manager_id,
        "service_manager_name": ticket.service_manager.full_name if ticket.service_manager else None,
        "service_technician_id": ticket.service_technician_id,
        "service_technician_name": ticket.service_technician.full_name if ticket.service_technician else None
    }


@router.get("/admin/timeline", response_model=TicketTimelineResponse)
async def get_ticket_timeline(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get ticket timeline and analytics (Admin)"""
    stats = TicketService.get_timeline_stats(db, days=days)
    
    # Get recent tickets for timeline
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    tickets = db.query(ServiceTicket).filter(
        ServiceTicket.created_date >= cutoff_date
    ).order_by(ServiceTicket.created_date.desc()).all()
    
    timeline_entries = []
    for ticket in tickets:
        user = db.query(User).filter(User.id == ticket.user_id).first()
        timeline_entries.append({
            "ticket_id": ticket.ticket_id,
            "user_id": ticket.user_id,
            "user_name": user.name if user else "Unknown",
            "issue_category": ticket.issue_category,
            "created_date": ticket.created_date,
            "resolved_date": ticket.resolved_date,
            "resolution_time_hours": ticket.resolution_time_hours,
            "status": ticket.status,
            "sla_status": ticket.sla_status,
            "assigned_to": ticket.assigned_to
        })
    
    return {
        "stats": stats,
        "tickets": timeline_entries,
        "date_range": f"Last {days} days"
    }


@router.get("/admin/open-tickets", response_model=List[TicketResponse])
async def get_open_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all open tickets (Admin)"""
    tickets = db.query(ServiceTicket).filter(
        ServiceTicket.status == 'Open'
    ).order_by(ServiceTicket.sla_deadline.asc()).all()
    
    # Update SLA status
    for ticket in tickets:
        new_sla_status = TicketService.check_sla_status(ticket)
        if new_sla_status != ticket.sla_status:
            ticket.sla_status = new_sla_status
    
    db.commit()
    return tickets


# ===== DC PROTOCOL JAN 2026: EV SERVICE TICKET ENDPOINTS =====

@router.post("/service/create")
async def create_service_ticket(
    request: Request,
    issue_category: str = Body(...),
    issue_description: str = Body(...),
    priority: str = Body(default='Medium'),
    ticket_type: str = Body(default='technical'),
    source_channel: str = Body(default='website'),
    partner_id: Optional[int] = Body(default=None),
    customer_name: Optional[str] = Body(default=None),
    customer_phone: Optional[str] = Body(default=None),
    customer_email: Optional[str] = Body(default=None),
    customer_address: Optional[str] = Body(default=None),
    product_name: Optional[str] = Body(default=None),
    product_serial: Optional[str] = Body(default=None),
    product_model: Optional[str] = Body(default=None),
    warranty_status: Optional[str] = Body(default=None),
    spares_required: bool = Body(default=False),
    spare_items: Optional[List[dict]] = Body(default=None),
    customer_mobile: Optional[str] = Body(default=None),
    vehicle_number: Optional[str] = Body(default=None),
    vehicle_model: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Create new EV service ticket with customer and product details
    
    DC Protocol Jan 2026: Enhanced with spare_items array support
    - spare_items: [{part_name, sku, quantity, stock_item_id}]
    - Creates ServiceTicketSpareRequest records for procurement queue
    
    DC Protocol Jan 2026: Backward compatibility for mobile app
    - customer_mobile: Alias for customer_phone (legacy mobile app field)
    - vehicle_number: Alias for product_serial (legacy mobile app field)
    - vehicle_model: Alias for product_model (legacy mobile app field)
    """
    final_customer_phone = customer_phone or customer_mobile
    final_product_serial = product_serial or vehicle_number
    final_product_model = product_model or vehicle_model
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest
    
    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    
    staff_id = None
    staff = None
    try:
        staff = get_current_staff_user_from_hybrid(current_user, db)
        if staff:
            staff_id = staff.id
    except:
        pass
    
    # DC Protocol: Staff users have integer IDs, MNR users have string IDs
    # service_ticket.user_id is FK to user.id (MNR string IDs)
    # For staff-created tickets, user_id is None (nullable), staff_id tracks creator
    if staff:
        ticket_user_id = None  # Staff-created ticket
    else:
        ticket_user_id = current_user.id  # MNR user's string ID
    
    ticket = TicketService.create_service_ticket(
        db=db,
        user_id=ticket_user_id,
        issue_category=issue_category,
        issue_description=issue_description,
        priority=priority,
        ticket_type=ticket_type,
        source_channel=source_channel,
        partner_id=partner_id,
        customer_name=customer_name,
        customer_phone=final_customer_phone,
        customer_email=customer_email,
        customer_address=customer_address,
        product_name=product_name,
        product_serial=final_product_serial,
        product_model=final_product_model,
        warranty_status=warranty_status,
        spares_required=spares_required,
        ip_address=ip_address,
        user_agent=user_agent,
        staff_id=staff_id
    )
    
    # DC Protocol Jan 2026: Create spare request records for procurement queue
    spare_count = 0
    if spares_required and spare_items:
        for item in spare_items:
            if item.get('part_name'):
                spare_request = ServiceTicketSpareRequest(
                    ticket_id=ticket.id,
                    spare_item_name=item.get('part_name'),
                    spare_item_code=item.get('sku'),
                    quantity_required=item.get('quantity', 1),
                    procurement_status='pending',
                    requested_by_id=staff_id,
                    tat_extension_hours=48
                )
                db.add(spare_request)
                spare_count += 1
        
        if spare_count > 0:
            # Update ticket status to indicate spares workflow
            ticket.sub_status = 'awaiting_spares'
            ticket.spare_requested_at = datetime.utcnow()
            db.commit()

    # DC_WA_TEMPLATES_SEED_001: Notify customer on ticket creation (non-fatal)
    try:
        from app.services.whatsapp_auto_service import send_ticket_created_wa
        send_ticket_created_wa(db, ticket)
    except Exception as _wa_tc:
        logger.warning(f"[WA-AUTO] ticket_created WA error (non-fatal): {_wa_tc}")

    return {"success": True, "ticket_id": ticket.ticket_id, "id": ticket.id, "spares_added": spare_count}



@router.get("/service/dashboard-stats")
async def get_service_dashboard_stats(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    partner_id: Optional[int] = None,
    sub_status: Optional[str] = None,
    ticket_type: Optional[str] = None,
    priority: Optional[str] = None,
    technician_id: Optional[int] = None,
    sla_status: Optional[str] = None,
    source_channel: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get service ticket dashboard statistics with comprehensive filters"""
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta
    import pytz
    
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if date_from:
        try:
            filter_from = datetime.strptime(date_from, '%Y-%m-%d')
            filter_from = ist.localize(filter_from)
        except:
            filter_from = today_start - timedelta(days=30)
    else:
        filter_from = today_start - timedelta(days=30)
    
    if date_to:
        try:
            filter_to = datetime.strptime(date_to, '%Y-%m-%d')
            filter_to = ist.localize(filter_to.replace(hour=23, minute=59, second=59))
        except:
            filter_to = now
    else:
        filter_to = now
    
    def apply_filters(query):
        query = query.filter(
            ServiceTicket.created_date >= filter_from,
            ServiceTicket.created_date <= filter_to
        )
        if partner_id:
            query = query.filter(ServiceTicket.partner_id == partner_id)
        if sub_status:
            query = query.filter(ServiceTicket.sub_status == sub_status)
        if ticket_type:
            query = query.filter(ServiceTicket.ticket_type == ticket_type)
        if priority:
            query = query.filter(ServiceTicket.priority == priority)
        if technician_id:
            query = query.filter(ServiceTicket.service_technician_id == technician_id)
        if source_channel:
            query = query.filter(ServiceTicket.source_channel == source_channel)
        if sla_status == 'breached':
            query = query.filter(
                ServiceTicket.tat_due_at < now,
                ServiceTicket.sub_status.notin_(['closed', 'work_complete'])
            )
        elif sla_status == 'within':
            query = query.filter(
                or_(
                    ServiceTicket.tat_due_at >= now,
                    ServiceTicket.tat_due_at.is_(None),
                    ServiceTicket.sub_status.in_(['closed', 'work_complete'])
                )
            )
        return query
    
    base_query = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.status != 'deleted')
    total_tickets = apply_filters(base_query).scalar() or 0
    
    open_statuses = ['new', 'acknowledged', 'diagnosing', 'awaiting_spares', 'procurement_in_progress', 'ready_for_work']
    open_query = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.sub_status.in_(open_statuses))
    open_tickets = apply_filters(open_query).scalar() or 0
    
    resolved_query = db.query(func.count(ServiceTicket.id)).filter(
        ServiceTicket.sub_status.in_(['work_complete', 'closed']),
        ServiceTicket.work_completed_at >= today_start
    )
    resolved_today = apply_filters(resolved_query).scalar() or 0
    
    sla_breached_query = db.query(func.count(ServiceTicket.id)).filter(
        ServiceTicket.tat_due_at < now,
        ServiceTicket.sub_status.notin_(['closed', 'work_complete'])
    )
    sla_breached = apply_filters(sla_breached_query).scalar() or 0
    
    spares_query = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.sub_status == 'awaiting_spares')
    awaiting_spares = apply_filters(spares_query).scalar() or 0
    
    sla_total_query = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.tat_due_at.isnot(None))
    total_for_sla = apply_filters(sla_total_query).scalar() or 1
    within_sla = total_for_sla - sla_breached
    sla_compliance = round((within_sla / total_for_sla) * 100) if total_for_sla > 0 else 100
    
    new_query = db.query(func.count(ServiceTicket.id)).filter(ServiceTicket.sub_status == 'new')
    status_new = apply_filters(new_query).scalar() or 0
    
    progress_query = db.query(func.count(ServiceTicket.id)).filter(
        ServiceTicket.sub_status.in_(['acknowledged', 'diagnosing', 'ready_for_work'])
    )
    status_progress = apply_filters(progress_query).scalar() or 0
    status_spares = awaiting_spares
    
    complete_query = db.query(func.count(ServiceTicket.id)).filter(
        ServiceTicket.sub_status.in_(['work_complete', 'closed'])
    )
    status_complete = apply_filters(complete_query).scalar() or 0
    
    date_diff = (filter_to - filter_from).days
    if date_diff <= 7:
        trend_days = date_diff + 1
    elif date_diff <= 30:
        trend_days = min(date_diff, 14)
    else:
        trend_days = 30
    
    dates = []
    created_counts = []
    resolved_counts = []
    for i in range(trend_days - 1, -1, -1):
        day = today_start - timedelta(days=i)
        next_day = day + timedelta(days=1)
        if day >= filter_from and day <= filter_to:
            dates.append(day.strftime('%b %d'))
            
            created_day_query = db.query(func.count(ServiceTicket.id)).filter(
                ServiceTicket.created_date >= day,
                ServiceTicket.created_date < next_day
            )
            if partner_id:
                created_day_query = created_day_query.filter(ServiceTicket.partner_id == partner_id)
            if ticket_type:
                created_day_query = created_day_query.filter(ServiceTicket.ticket_type == ticket_type)
            if priority:
                created_day_query = created_day_query.filter(ServiceTicket.priority == priority)
            if technician_id:
                created_day_query = created_day_query.filter(ServiceTicket.service_technician_id == technician_id)
            if source_channel:
                created_day_query = created_day_query.filter(ServiceTicket.source_channel == source_channel)
            created_counts.append(created_day_query.scalar() or 0)
            
            resolved_day_query = db.query(func.count(ServiceTicket.id)).filter(
                ServiceTicket.work_completed_at >= day,
                ServiceTicket.work_completed_at < next_day
            )
            if partner_id:
                resolved_day_query = resolved_day_query.filter(ServiceTicket.partner_id == partner_id)
            if ticket_type:
                resolved_day_query = resolved_day_query.filter(ServiceTicket.ticket_type == ticket_type)
            if priority:
                resolved_day_query = resolved_day_query.filter(ServiceTicket.priority == priority)
            if technician_id:
                resolved_day_query = resolved_day_query.filter(ServiceTicket.service_technician_id == technician_id)
            if source_channel:
                resolved_day_query = resolved_day_query.filter(ServiceTicket.source_channel == source_channel)
            resolved_counts.append(resolved_day_query.scalar() or 0)
    
    recent_query = db.query(ServiceTicket).filter(
        ServiceTicket.created_date >= filter_from,
        ServiceTicket.created_date <= filter_to
    )
    if partner_id:
        recent_query = recent_query.filter(ServiceTicket.partner_id == partner_id)
    if sub_status:
        recent_query = recent_query.filter(ServiceTicket.sub_status == sub_status)
    if ticket_type:
        recent_query = recent_query.filter(ServiceTicket.ticket_type == ticket_type)
    if priority:
        recent_query = recent_query.filter(ServiceTicket.priority == priority)
    if technician_id:
        recent_query = recent_query.filter(ServiceTicket.service_technician_id == technician_id)
    if source_channel:
        recent_query = recent_query.filter(ServiceTicket.source_channel == source_channel)
    
    recent_tickets = recent_query.order_by(ServiceTicket.created_date.desc()).limit(10).all()
    
    return {
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "resolved_today": resolved_today,
        "sla_breached": sla_breached,
        "awaiting_spares": awaiting_spares,
        "sla_compliance": sla_compliance,
        "avg_resolution_hours": 18,
        "avg_response_hours": 2,
        "status_distribution": {
            "new": status_new,
            "in_progress": status_progress,
            "awaiting_spares": status_spares,
            "completed": status_complete
        },
        "trend_data": {
            "dates": dates,
            "created": created_counts,
            "resolved": resolved_counts
        },
        "recent_tickets": [t.to_dict() for t in recent_tickets],
        "filters_applied": {
            "date_from": date_from or filter_from.strftime('%Y-%m-%d'),
            "date_to": date_to or filter_to.strftime('%Y-%m-%d'),
            "partner_id": partner_id,
            "sub_status": sub_status,
            "ticket_type": ticket_type,
            "priority": priority,
            "technician_id": technician_id,
            "sla_status": sla_status,
            "source_channel": source_channel
        }
    }


@router.get("/service/showroom-breakdown")
async def get_showroom_breakdown(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sub_status: Optional[str] = None,
    ticket_type: Optional[str] = None,
    priority: Optional[str] = None,
    technician_id: Optional[int] = None,
    sla_status: Optional[str] = None,
    source_channel: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Showroom/service-center-wise ticket breakdown for dashboard Tab 1.
    DC Protocol Mar 2026: Returns only showrooms with >= 1 ticket in the selected period.
    Respects all global filters. Auth: get_current_user_hybrid.
    """
    from sqlalchemy import func, and_, case
    from app.models.staff_accounts import OfficialPartner
    import pytz
    from datetime import datetime, timedelta

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    # Build date range (same logic as dashboard-stats)
    if date_from:
        try:
            filter_from = ist.localize(datetime.strptime(date_from, '%Y-%m-%d'))
        except Exception:
            filter_from = now - timedelta(days=30)
    else:
        filter_from = None

    if date_to:
        try:
            filter_to = ist.localize(datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        except Exception:
            filter_to = now
    else:
        filter_to = now

    open_statuses = ['new', 'acknowledged', 'diagnosing', 'awaiting_spares', 'procurement_in_progress', 'ready_for_work']

    # Base filter predicate builder
    def base_filters(q):
        if filter_from:
            q = q.filter(ServiceTicket.created_date >= filter_from)
        q = q.filter(ServiceTicket.created_date <= filter_to)
        q = q.filter(ServiceTicket.status != 'deleted')
        q = q.filter(ServiceTicket.partner_id.isnot(None))
        if sub_status:
            q = q.filter(ServiceTicket.sub_status == sub_status)
        if ticket_type:
            q = q.filter(ServiceTicket.ticket_type == ticket_type)
        if priority:
            q = q.filter(ServiceTicket.priority == priority)
        if technician_id:
            q = q.filter(ServiceTicket.service_technician_id == technician_id)
        if source_channel:
            q = q.filter(ServiceTicket.source_channel == source_channel)
        if sla_status == 'breached':
            q = q.filter(ServiceTicket.tat_due_at < now, ServiceTicket.sub_status.notin_(['closed', 'work_complete']))
        elif sla_status == 'within':
            q = q.filter(or_(ServiceTicket.tat_due_at >= now, ServiceTicket.tat_due_at.is_(None), ServiceTicket.sub_status.in_(['closed', 'work_complete'])))
        return q

    rows = base_filters(
        db.query(
            ServiceTicket.partner_id,
            func.count(ServiceTicket.id).label('total'),
            func.sum(case((ServiceTicket.sub_status.in_(open_statuses), 1), else_=0)).label('open'),
            func.sum(case((ServiceTicket.sub_status.in_(['work_complete', 'closed']), 1), else_=0)).label('resolved'),
            func.sum(case(
                (and_(ServiceTicket.tat_due_at < now, ServiceTicket.sub_status.notin_(['closed', 'work_complete'])), 1),
                else_=0
            )).label('sla_breached'),
            func.sum(case((ServiceTicket.tat_due_at.isnot(None), 1), else_=0)).label('sla_tracked'),
            func.avg(
                func.extract('epoch', ServiceTicket.work_completed_at - ServiceTicket.created_date) / 3600
            ).label('avg_resolution_hrs')
        ).group_by(ServiceTicket.partner_id)
    ).all()

    # Fetch partner names
    partner_ids = [r.partner_id for r in rows if r.partner_id]
    partners = {p.id: p.partner_name for p in db.query(OfficialPartner).filter(OfficialPartner.id.in_(partner_ids)).all()}

    result = []
    for r in rows:
        total = r.total or 0
        sla_breached = r.sla_breached or 0
        sla_tracked = r.sla_tracked or 0
        sla_pct = round(((sla_tracked - sla_breached) / sla_tracked * 100)) if sla_tracked > 0 else 100
        result.append({
            "partner_id": r.partner_id,
            "partner_name": partners.get(r.partner_id, f"Center #{r.partner_id}"),
            "total": total,
            "open": r.open or 0,
            "resolved": r.resolved or 0,
            "sla_breached": sla_breached,
            "sla_pct": sla_pct,
            "avg_resolution_hrs": round(r.avg_resolution_hrs, 1) if r.avg_resolution_hrs else None
        })

    result.sort(key=lambda x: x['total'], reverse=True)
    return {"showrooms": result, "total_showrooms": len(result)}


@router.get("/service/technician-breakdown")
async def get_technician_breakdown(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    partner_id: Optional[int] = None,
    sub_status: Optional[str] = None,
    ticket_type: Optional[str] = None,
    priority: Optional[str] = None,
    sla_status: Optional[str] = None,
    source_channel: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Technician-wise ticket breakdown for dashboard Trends tab.
    DC Protocol Mar 2026: Includes all staff in department_id=14 (Service).
    Shows assigned/resolved/pending/SLA stats per technician.
    Auth: get_current_user_hybrid.
    """
    from sqlalchemy import func, and_, case
    from app.models.staff import StaffEmployee
    import pytz
    from datetime import datetime, timedelta

    SERVICE_DEPT_ID = 14

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    if date_from:
        try:
            filter_from = ist.localize(datetime.strptime(date_from, '%Y-%m-%d'))
        except Exception:
            filter_from = now - timedelta(days=30)
    else:
        filter_from = None

    if date_to:
        try:
            filter_to = ist.localize(datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        except Exception:
            filter_to = now
    else:
        filter_to = now

    open_statuses = ['new', 'acknowledged', 'diagnosing', 'awaiting_spares', 'procurement_in_progress', 'ready_for_work']

    # All active service dept staff
    service_staff = db.query(StaffEmployee).filter(
        StaffEmployee.department_id == SERVICE_DEPT_ID,
        StaffEmployee.status == 'active'
    ).all()
    staff_map = {s.id: s.full_name for s in service_staff}
    service_staff_ids = list(staff_map.keys())

    def base_filters(q):
        if filter_from:
            q = q.filter(ServiceTicket.created_date >= filter_from)
        q = q.filter(ServiceTicket.created_date <= filter_to)
        q = q.filter(ServiceTicket.status != 'deleted')
        if partner_id:
            q = q.filter(ServiceTicket.partner_id == partner_id)
        if sub_status:
            q = q.filter(ServiceTicket.sub_status == sub_status)
        if ticket_type:
            q = q.filter(ServiceTicket.ticket_type == ticket_type)
        if priority:
            q = q.filter(ServiceTicket.priority == priority)
        if source_channel:
            q = q.filter(ServiceTicket.source_channel == source_channel)
        if sla_status == 'breached':
            q = q.filter(ServiceTicket.tat_due_at < now, ServiceTicket.sub_status.notin_(['closed', 'work_complete']))
        elif sla_status == 'within':
            q = q.filter(or_(ServiceTicket.tat_due_at >= now, ServiceTicket.tat_due_at.is_(None), ServiceTicket.sub_status.in_(['closed', 'work_complete'])))
        return q

    rows = base_filters(
        db.query(
            ServiceTicket.service_technician_id,
            func.count(ServiceTicket.id).label('assigned'),
            func.sum(case((ServiceTicket.sub_status.in_(['work_complete', 'closed']), 1), else_=0)).label('resolved'),
            func.sum(case((ServiceTicket.sub_status.in_(open_statuses), 1), else_=0)).label('pending'),
            func.sum(case(
                (and_(ServiceTicket.tat_due_at < now, ServiceTicket.sub_status.notin_(['closed', 'work_complete'])), 1),
                else_=0
            )).label('sla_breaches'),
            func.avg(
                func.extract('epoch', ServiceTicket.work_completed_at - ServiceTicket.created_date) / 3600
            ).label('avg_resolution_hrs')
        ).filter(
            ServiceTicket.service_technician_id.in_(service_staff_ids)
        ).group_by(ServiceTicket.service_technician_id)
    ).all()

    ticket_ids_set = {r.service_technician_id for r in rows}

    result = []
    for staff_id, staff_name in staff_map.items():
        row = next((r for r in rows if r.service_technician_id == staff_id), None)
        assigned = row.assigned if row else 0
        resolved = row.resolved if row else 0
        pending = row.pending if row else 0
        sla_breaches = row.sla_breaches if row else 0
        avg_res = round(row.avg_resolution_hrs, 1) if row and row.avg_resolution_hrs else None
        result.append({
            "technician_id": staff_id,
            "technician_name": staff_name,
            "assigned": assigned,
            "resolved": resolved,
            "pending": pending,
            "sla_breaches": sla_breaches,
            "avg_resolution_hrs": avg_res
        })

    result.sort(key=lambda x: x['assigned'], reverse=True)
    return {"technicians": result, "total_technicians": len(result)}


@router.get("/service/showroom-trend")
async def get_showroom_trend(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    partner_id: Optional[int] = None,
    sub_status: Optional[str] = None,
    ticket_type: Optional[str] = None,
    priority: Optional[str] = None,
    sla_status: Optional[str] = None,
    source_channel: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Showroom-wise ticket trend over time for dashboard Trends Tab Section A.
    DC Protocol Mar 2026: Auto-granularity: daily <=30d, weekly >30d.
    Auth: get_current_user_hybrid.
    """
    from sqlalchemy import func
    from app.models.staff_accounts import OfficialPartner
    import pytz
    from datetime import datetime, timedelta

    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)

    if date_from:
        try:
            filter_from = ist.localize(datetime.strptime(date_from, '%Y-%m-%d'))
        except Exception:
            filter_from = now - timedelta(days=30)
    else:
        filter_from = now - timedelta(days=180)

    if date_to:
        try:
            filter_to = ist.localize(datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
        except Exception:
            filter_to = now
    else:
        filter_to = now

    date_diff = (filter_to - filter_from).days
    weekly = date_diff > 30

    # Build date buckets
    buckets = []
    cursor = filter_from.replace(hour=0, minute=0, second=0, microsecond=0)
    step = timedelta(weeks=1) if weekly else timedelta(days=1)
    while cursor <= filter_to:
        buckets.append(cursor)
        cursor += step

    # Get partner IDs that have tickets in range
    pq = db.query(ServiceTicket.partner_id).filter(
        ServiceTicket.created_date >= filter_from,
        ServiceTicket.created_date <= filter_to,
        ServiceTicket.status != 'deleted',
        ServiceTicket.partner_id.isnot(None)
    )
    if partner_id:
        pq = pq.filter(ServiceTicket.partner_id == partner_id)
    active_partner_ids = list({r.partner_id for r in pq.distinct().all()})

    if not active_partner_ids:
        return {"dates": [], "series": [], "granularity": "daily"}

    partners = {p.id: p.partner_name for p in db.query(OfficialPartner).filter(OfficialPartner.id.in_(active_partner_ids)).all()}

    label_fmt = '%b %d' if not weekly else '%b %d'
    date_labels = [b.strftime(label_fmt) for b in buckets]

    series = []
    for pid in active_partner_ids:
        data = []
        for i, bucket_start in enumerate(buckets):
            bucket_end = buckets[i + 1] if i + 1 < len(buckets) else filter_to + timedelta(seconds=1)
            cnt = db.query(func.count(ServiceTicket.id)).filter(
                ServiceTicket.partner_id == pid,
                ServiceTicket.created_date >= bucket_start,
                ServiceTicket.created_date < bucket_end,
                ServiceTicket.status != 'deleted'
            ).scalar() or 0
            data.append(cnt)
        series.append({"partner_id": pid, "partner_name": partners.get(pid, f"Center #{pid}"), "data": data})

    series.sort(key=lambda x: sum(x['data']), reverse=True)
    return {
        "dates": date_labels,
        "series": series,
        "granularity": "weekly" if weekly else "daily"
    }


@router.get("/service/queue")
async def get_service_queue(
    service_center_id: Optional[int] = None,
    sub_status: Optional[str] = None,
    ticket_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get service team ticket queue
    DC Protocol Feb 2026: Enhanced error handling for serialization issues
    DC Protocol Mar 2026 (RBAC): key_leadership, vgk4u, manager, service_head roles see all tickets.
    DC Protocol Apr 2026: accounts role added — full visibility of all service tickets for Accounts dept.
    All other roles see only tickets where they are the service_manager or service_technician.
    """
    import logging
    logger = logging.getLogger(__name__)

    _PRIVILEGED_ROLES = {'vgk4u', 'key_leadership', 'manager', 'service_head', 'service_incharge', 'accounts', 'ea'}
    _user_role_code = ''
    try:
        _role_obj = getattr(current_user, 'role', None)
        if _role_obj is None and hasattr(current_user, '_user'):
            _role_obj = getattr(current_user._user, 'role', None)
        _user_role_code = (getattr(_role_obj, 'role_code', '') or '').lower().strip()
    except Exception:
        pass
    _is_privileged = _user_role_code in _PRIVILEGED_ROLES
    _staff_id_filter = None if _is_privileged else getattr(current_user, 'id', None)

    try:
        tickets = TicketService.get_service_queue(
            db=db,
            service_center_id=service_center_id,
            sub_status_filter=sub_status,
            ticket_type_filter=ticket_type,
            staff_id_filter=_staff_id_filter
        )
        
        result = []
        for ticket in tickets:
            try:
                d = ticket.to_dict()
                # DC-VENDOR-REPAIR-TRACKER-001: count spares currently at vendor
                d['vendor_repair_count'] = sum(
                    1 for s in (ticket.spare_requests or [])
                    if getattr(s, 'vendor_repair_status', None) in ('sent', 'waiting_for_repair')
                )
                result.append(d)
            except Exception as e:
                logger.error(f"[ServiceQueue] Failed to serialize ticket {ticket.id}: {e}")
                result.append({
                    'id': ticket.id,
                    'ticket_id': ticket.ticket_id,
                    'ticket_number': ticket.ticket_id,
                    'status': ticket.status,
                    'sub_status': ticket.sub_status,
                    'priority': ticket.priority,
                    'customer_name': ticket.customer_name,
                    'customer_phone': ticket.customer_phone,
                    'customer_mobile': ticket.customer_phone,
                    'issue_category': ticket.issue_category,
                    'issue_description': ticket.issue_description,
                    'product_serial': ticket.product_serial,
                    'vehicle_number': ticket.product_serial,
                    'product_model': ticket.product_model,
                    'vehicle_model': ticket.product_model,
                    'partner_id': ticket.partner_id,
                    'partner_name': None,
                    'partner': None,
                    'service_manager_id': ticket.service_manager_id,
                    'service_manager_name': None,
                    'service_technician_id': ticket.service_technician_id,
                    'service_technician_name': None,
                    'created_date': ticket.created_date.isoformat() if ticket.created_date else None,
                    'created_at': ticket.created_date.isoformat() if ticket.created_date else None,
                    'product_name': getattr(ticket, 'product_name', None),
                    'ticket_type': getattr(ticket, 'ticket_type', None),
                    'warranty_status': getattr(ticket, 'warranty_status', None),
                    'warranty_invoice_number': getattr(ticket, 'warranty_invoice_number', None),
                    'warranty_sale_date': str(ticket.warranty_sale_date) if getattr(ticket, 'warranty_sale_date', None) else None,
                    'warranty_motor_number': getattr(ticket, 'warranty_motor_number', None),
                    'warranty_chassis_number': getattr(ticket, 'warranty_chassis_number', None),
                    'warranty_model': getattr(ticket, 'warranty_model', None),
                    'warranty_notes': getattr(ticket, 'warranty_notes', None),
                    'assigned_department_id': getattr(ticket, 'assigned_department_id', None),
                    'assigned_department_name': getattr(getattr(ticket, 'assigned_department', None), 'name', None),
                    'tat_due_at': ticket.tat_due_at.isoformat() if getattr(ticket, 'tat_due_at', None) else None,
                    'sla_status': getattr(ticket, 'sla_status', None),
                    'spares_required': getattr(ticket, 'spares_required', False),
                    'vendor_repair_count': 0,
                    '_serialization_error': str(e)
                })
        
        return result
    except Exception as e:
        logger.error(f"[ServiceQueue] Failed to load queue: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load service queue: {str(e)}")


@router.get("/service/procurement-queue")
async def get_procurement_queue(
    status: Optional[str] = Query(None, description="Filter by procurement status"),
    urgency: Optional[str] = Query(None, description="Filter by urgency"),
    search: Optional[str] = Query(None, description="Search by item name or ticket ID"),
    date_from: Optional[str] = Query(None, description="Filter from date"),
    date_to: Optional[str] = Query(None, description="Filter to date"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get procurement team spare requests queue with filters"""
    from app.models.ticket import ServiceTicketSpareRequest, ServiceTicket, TicketAttachment
    from datetime import datetime as dt
    
    query = db.query(ServiceTicketSpareRequest)
    
    if status:
        query = query.filter(ServiceTicketSpareRequest.procurement_status == status)
    else:
        query = query.filter(ServiceTicketSpareRequest.procurement_status.in_(['pending', 'acknowledged', 'ordered']))
    
    if urgency:
        query = query.filter(ServiceTicketSpareRequest.urgency == urgency)
    
    if date_from:
        try:
            from_date = dt.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ServiceTicketSpareRequest.requested_at >= from_date)
        except: pass
    
    if date_to:
        try:
            to_date = dt.strptime(date_to, '%Y-%m-%d')
            query = query.filter(ServiceTicketSpareRequest.requested_at <= to_date)
        except: pass
    
    spare_requests = query.order_by(ServiceTicketSpareRequest.requested_at.desc()).all()
    
    result = []
    for spare in spare_requests:
        item = spare.to_dict()
        if spare.ticket:
            item['ticket_id_str'] = spare.ticket.ticket_id
            item['customer_name'] = spare.ticket.customer_name
            item['product_name'] = spare.ticket.product_name
            item['ticket_sub_status'] = spare.ticket.sub_status
            item['ticket_priority'] = spare.ticket.priority
            attachments = db.query(TicketAttachment).filter(TicketAttachment.ticket_id == spare.ticket.id).all()
            item['attachments'] = [
                {
                    'id': a.id,
                    'filename': a.original_filename,
                    'url': f'/api/v1/tickets/{spare.ticket.id}/attachment/{a.id}'
                } for a in attachments
            ]

        # Enrich with marketplace PO / ZYPR numbers if catalog-sourced
        if spare.marketplace_po_id:
            from app.models.marketplace import MarketplacePurchaseOrder as _MPO
            _po = db.query(_MPO).filter(_MPO.id == spare.marketplace_po_id).first()
            if _po:
                item['marketplace_po_number'] = _po.po_number
                item['marketplace_po_status'] = _po.status
        if spare.marketplace_procurement_id:
            from app.models.marketplace import MarketplaceProcurementRequest as _MPR
            _pr = db.query(_MPR).filter(_MPR.id == spare.marketplace_procurement_id).first()
            if _pr:
                item['marketplace_procurement_number'] = _pr.procurement_number
        
        if search:
            search_lower = search.lower()
            if not (search_lower in (item.get('item_name') or '').lower() or 
                    search_lower in (item.get('ticket_id_str') or '').lower() or
                    search_lower in (item.get('customer_name') or '').lower()):
                continue
        
        result.append(item)
    
    return result


@router.post("/service/{ticket_id}/update-status")
async def update_service_ticket_status(
    ticket_id: int,
    sub_status: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Generic status update for service tickets (staff use).
    DC Protocol Mar 2026: No state guards — staff can freely move a ticket to any
    valid status from the dropdown. Also covers work_complete and closed which
    previously routed to special endpoints with strict guards that blocked
    out-of-order transitions.
    Sets all audit timestamp / status fields the special endpoints would have set.
    """
    from app.models.ticket import TicketLog as _TLog
    from app.core.security import get_current_staff_user_from_hybrid
    ALLOWED = ['acknowledged', 'diagnosing', 'awaiting_spares',
               'procurement_in_progress', 'payment_pending', 'ready_for_work',
               'work_complete', 'closed', 'cancelled']
    if sub_status not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Invalid status: {sub_status}")
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    staff = get_current_staff_user_from_hybrid(current_user, db)
    staff_id = staff.id if staff else None
    old_status = ticket.sub_status
    now = datetime.utcnow()

    ticket.sub_status = sub_status

    # Sync the top-level status + audit timestamps to match the special endpoints
    if sub_status == 'acknowledged':
        ticket.status = 'In Progress'
        if not ticket.in_progress_date:
            ticket.in_progress_date = now
    elif sub_status == 'work_complete':
        ticket.status = 'Resolved'
        ticket.work_completed_at = now
        ticket.resolved_date = now
        if ticket.created_date:
            ticket.resolution_time_hours = (now - ticket.created_date).total_seconds() / 3600
    elif sub_status == 'closed':
        ticket.status = 'Closed'
        ticket.closed_date = now
    elif sub_status == 'cancelled':
        ticket.status = 'Cancelled'
    elif sub_status in ('diagnosing', 'awaiting_spares', 'procurement_in_progress',
                        'payment_pending', 'ready_for_work'):
        ticket.status = 'In Progress'

    db.add(_TLog(
        ticket_id=ticket_id,
        action_type='Status Changed',
        action_description=f'Status updated: {old_status} → {sub_status}',
        old_value=old_status,
        new_value=sub_status,
        staff_performer_id=staff_id
    ))
    db.commit()

    # ── WhatsApp auto-trigger on ticket status change ─────────────────────
    try:
        from app.services.whatsapp_auto_service import send_auto_whatsapp
        _ticket_wa_map = {
            'acknowledged': 'ticket_acknowledged',
            'work_complete': 'ticket_resolved',
            'closed': 'ticket_closed',
        }
        _ticket_event = _ticket_wa_map.get(sub_status)
        _ticket_phone = getattr(ticket, 'customer_phone', None)
        if _ticket_event and _ticket_phone:
            send_auto_whatsapp(
                db=db, event_key=_ticket_event, phone=_ticket_phone,
                context={
                    'name': getattr(ticket, 'customer_name', '') or '',
                    'ticket_id': ticket_id,
                    'status': sub_status,
                },
            )
    except Exception as _wa_ex:
        print(f"[WA-AUTO] Ticket hook error: {_wa_ex}")
    # ─────────────────────────────────────────────────────────────────────

    # DC Protocol Apr 2026: Deduct VGK member points on work_complete
    if sub_status == 'work_complete':
        try:
            from app.models.ticket import ServiceTicketSpareRequest as _STSR
            from sqlalchemy import text as _text
            _spares = db.query(_STSR).filter(
                _STSR.ticket_id == ticket_id,
                _STSR.discount_mode == 'vgk',
                _STSR.discount_id.isnot(None)
            ).all()
            if _spares:
                _disc_map = {}
                for _sp in _spares:
                    _did = (_sp.discount_id or '').upper()
                    _amt = float(_sp.discount_amount or 0) * int(_sp.quantity_required or 1)
                    _disc_map[_did] = _disc_map.get(_did, 0) + _amt

                for _vgk_code, _total_disc in _disc_map.items():
                    if _total_disc <= 0:
                        continue
                    _pb = db.execute(
                        _text("SELECT id, current_balance, total_consumed FROM mnr_points_balance WHERE user_id = :uid LIMIT 1"),
                        {'uid': _vgk_code}
                    ).fetchone()
                    if not _pb:
                        continue
                    _deduct = min(round(_total_disc, 2), float(_pb.current_balance or 0))
                    if _deduct <= 0:
                        continue
                    _new_bal = round(float(_pb.current_balance or 0) - _deduct, 2)
                    _new_consumed = round(float(_pb.total_consumed or 0) + _deduct, 2)
                    db.execute(
                        _text("""UPDATE mnr_points_balance
                                 SET current_balance=:bal, total_consumed=:cons, updated_at=NOW()
                                 WHERE id=:pid"""),
                        {'bal': _new_bal, 'cons': _new_consumed, 'pid': _pb.id}
                    )
                    db.execute(
                        _text("""INSERT INTO mnr_points_transactions
                                 (company_id, user_id, transaction_type, amount, balance_after, description, created_by_type, created_at)
                                 VALUES (1, :uid, 'discount_used', :amt, :bal, :desc, 'system', NOW())"""),
                        {'uid': _vgk_code, 'amt': -_deduct, 'bal': _new_bal,
                         'desc': f'VGK discount used on service ticket #{ticket_id} (₹{_deduct:.2f})'}
                    )
                db.commit()
        except Exception as _pts_ex:
            db.rollback()
            print(f"[VGK-POINTS] Deduction error on ticket {ticket_id}: {_pts_ex}")

    return {"success": True, "sub_status": sub_status}


@router.post("/service/{ticket_id}/acknowledge")
async def acknowledge_service_ticket(
    ticket_id: int,
    data: ServiceTicketAcknowledge = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Service team acknowledges ticket"""
    from app.core.security import get_current_staff_user_from_hybrid
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    result = TicketService.acknowledge_ticket(
        db=db,
        ticket_id=ticket_id,
        staff_id=staff.id,
        user_id=current_user.id,
        notes=data.notes
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/service/{ticket_id}/diagnose")
async def diagnose_service_ticket(
    ticket_id: int,
    data: ServiceTicketDiagnose = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Complete diagnosis and determine if spares are needed"""
    from app.core.security import get_current_staff_user_from_hybrid
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    result = TicketService.diagnose_ticket(
        db=db,
        ticket_id=ticket_id,
        staff_id=staff.id,
        user_id=current_user.id,
        diagnosis_notes=data.diagnosis_notes,
        spares_required=data.spares_required
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/service/{ticket_id}/request-spares")
async def request_spares_for_ticket(
    ticket_id: int,
    spare_items: List[dict] = Body(..., example=[{
        "name": "Battery 60V 30Ah",
        "code": "BATT-6030",
        "quantity": 1,
        "marketplace_spare_id": 123,
        "discount_mode": "dealer"
    }]),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Request spare parts for a ticket.
    Supports optional marketplace integration:
    - marketplace_spare_id: links to MarketplaceSpareItem
    - discount_mode: mnr/dealer/student/partner
    - quantity: required quantity
    """
    from app.core.security import get_current_staff_user_from_hybrid
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    result = TicketService.request_spares(
        db=db,
        ticket_id=ticket_id,
        staff_id=staff.id,
        user_id=current_user.id,
        spare_items=spare_items
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/service/spare-requests/{spare_id}/media")
async def upload_spare_media(
    spare_id: int,
    images: List[UploadFile] = File(default=[]),
    video: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Upload media files (images/video) for spare request.
    DC Protocol Jan 2026: Up to 10 images OR 1 video (max 3 minutes) - not both.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest
    import os
    import uuid
    from datetime import datetime
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    spare = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.id == spare_id
    ).first()
    
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")
    
    has_images = len(images) > 0 and any(img.filename for img in images)
    has_video = video is not None and video.filename
    
    if has_images and has_video:
        raise HTTPException(status_code=400, detail="Upload either images OR video, not both")
    
    if has_images and len([img for img in images if img.filename]) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")
    
    media_dir = f"uploads/spare_media/{spare_id}"
    os.makedirs(media_dir, exist_ok=True)
    
    media_files = spare.media_files or []
    uploaded = []
    
    for img in images:
        if img.filename:
            ext = os.path.splitext(img.filename)[1] or '.jpg'
            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = f"{media_dir}/{filename}"
            
            with open(filepath, 'wb') as f:
                content = await img.read()
                f.write(content)
            
            media_files.append({
                'type': 'image',
                'filename': img.filename,
                'path': filepath,
                'uploaded_at': datetime.utcnow().isoformat()
            })
            uploaded.append({'type': 'image', 'filename': img.filename})
    
    if video and video.filename:
        content = await video.read()
        max_video_size = 100 * 1024 * 1024  # 100MB limit (approx 3 min at typical bitrate)
        if len(content) > max_video_size:
            raise HTTPException(status_code=400, detail="Video file too large. Max 100MB (approx 3 min)")
        
        ext = os.path.splitext(video.filename)[1] or '.mp4'
        filename = f"video_{uuid.uuid4().hex}{ext}"
        filepath = f"{media_dir}/{filename}"
        
        with open(filepath, 'wb') as f:
            f.write(content)
        
        media_files.append({
            'type': 'video',
            'filename': video.filename,
            'path': filepath,
            'uploaded_at': datetime.utcnow().isoformat()
        })
        uploaded.append({'type': 'video', 'filename': video.filename})
    
    spare.media_files = media_files
    db.commit()
    
    return {
        "success": True,
        "message": f"Uploaded {len(uploaded)} files",
        "uploaded": uploaded,
        "total_media": len(media_files)
    }


@router.get("/spare-media/{spare_id}/{media_index}")
async def serve_spare_media(
    spare_id: int,
    media_index: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Serve spare request media file with access control.
    DC Protocol: Only ticket owner, admin, or staff can access spare media.
    """
    from fastapi.responses import FileResponse
    from app.models.ticket import ServiceTicketSpareRequest
    import os
    
    spare = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.id == spare_id
    ).first()
    
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")
    
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == spare.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    is_admin = hasattr(current_user, 'is_admin') and callable(getattr(current_user, 'is_admin', None)) and current_user.is_admin()
    if ticket.user_id != current_user.id and not is_admin and not is_staff:
        raise HTTPException(status_code=403, detail="Access denied")
    
    media_files = spare.media_files or []
    if media_index < 0 or media_index >= len(media_files):
        raise HTTPException(status_code=404, detail="Media not found")
    
    media = media_files[media_index]
    filepath = media.get('path')
    
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    media_type = 'image/jpeg' if media.get('type') == 'image' else 'video/mp4'
    return FileResponse(filepath, media_type=media_type)


@router.post("/service/spares/{spare_id}/acknowledge")
async def acknowledge_spare_request(
    spare_id: int,
    stock_available: bool = Body(...),
    stock_quantity: int = Body(default=0),
    notes: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Procurement team acknowledges spare request"""
    from app.core.security import get_current_staff_user_from_hybrid
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    result = TicketService.acknowledge_spare_request(
        db=db,
        spare_request_id=spare_id,
        staff_id=staff.id,
        user_id=current_user.id,
        stock_available=stock_available,
        stock_quantity=stock_quantity,
        notes=notes
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/service/spares/{spare_id}/release")
async def release_spare_parts(
    spare_id: int,
    actual_cost: Optional[float] = Body(default=None),
    notes: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Release spare parts for service work"""
    from app.core.security import get_current_staff_user_from_hybrid
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    result = TicketService.release_spares(
        db=db,
        spare_request_id=spare_id,
        staff_id=staff.id,
        user_id=current_user.id,
        actual_cost=actual_cost,
        notes=notes
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.put("/service/spares/{spare_id}/pricing")
async def update_spare_pricing(
    spare_id: int,
    unit_price: float = Body(..., embed=True),
    gst_rate: float = Body(default=18.0, embed=True),
    hsn_code: Optional[str] = Body(default=None, embed=True),
    vendor_id: Optional[int] = Body(default=None, embed=True),
    vendor_invoice_number: Optional[str] = Body(default=None, embed=True),
    vendor_invoice_amount: Optional[float] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Update spare request pricing and GST details.
    Allows staff to set/override unit price, GST rate, and vendor details.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    spare = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.id == spare_id
    ).first()
    
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")
    
    spare.unit_price = unit_price
    spare.gst_rate = gst_rate
    spare.hsn_code = hsn_code
    spare.gst_amount = (unit_price * spare.quantity_required * gst_rate) / 100
    spare.total_with_gst = (unit_price * spare.quantity_required) + spare.gst_amount
    spare.price_overridden = True
    
    if vendor_id:
        spare.vendor_id = vendor_id
    if vendor_invoice_number:
        spare.vendor_invoice_number = vendor_invoice_number
    if vendor_invoice_amount:
        spare.vendor_invoice_amount = vendor_invoice_amount
    
    db.commit()
    db.refresh(spare)
    
    return {"success": True, "spare_request": spare.to_dict()}


@router.post("/service/spares/{spare_id}/auto-populate-pricing")
async def auto_populate_spare_pricing(
    spare_id: int,
    stock_item_id: int = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Auto-populate spare request pricing from stock item master.
    Copies selling price, GST rate, and HSN code from stock item.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest
    from app.models.staff_accounts import StockItemMaster
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    spare = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.id == spare_id
    ).first()
    
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")
    
    stock_item = db.query(StockItemMaster).filter(
        StockItemMaster.id == stock_item_id,
        StockItemMaster.is_active == True
    ).first()
    
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    spare.stock_item_id = stock_item_id
    spare.spare_item_code = stock_item.item_code
    spare.unit_price = float(stock_item.selling_rate or 0)
    spare.gst_rate = float(stock_item.default_gst_rate or 18)
    spare.hsn_code = stock_item.hsn_code
    spare.gst_amount = (spare.unit_price * spare.quantity_required * spare.gst_rate) / 100
    spare.total_with_gst = (spare.unit_price * spare.quantity_required) + spare.gst_amount
    spare.price_overridden = False
    
    if stock_item.default_vendor_id:
        spare.vendor_id = stock_item.default_vendor_id
    
    db.commit()
    db.refresh(spare)
    
    return {
        "success": True,
        "spare_request": spare.to_dict(),
        "stock_item": stock_item.to_dict()
    }


@router.get("/service/stock-items/search")
async def search_stock_items(
    q: str = Query(default="", description="Search term"),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Search stock items for spare request auto-populate"""
    from app.models.staff_accounts import StockItemMaster
    
    query = db.query(StockItemMaster).filter(StockItemMaster.is_active == True)
    
    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            (StockItemMaster.item_name.ilike(search_pattern)) |
            (StockItemMaster.item_code.ilike(search_pattern))
        )
    
    if category:
        query = query.filter(StockItemMaster.item_category == category)
    
    items = query.limit(limit).all()
    
    return {
        "success": True,
        "items": [item.to_dict() for item in items]
    }


# ===== CUSTOM SPARES ENDPOINTS (DC Protocol Jan 2026) =====

@router.post("/service/{ticket_id}/request-custom-spare")
async def request_custom_spare(
    ticket_id: int,
    spare_item_name: str = Body(...),
    spare_description: Optional[str] = Body(default=None),
    quantity_required: int = Body(default=1),
    estimated_cost: Optional[float] = Body(default=None),
    request_notes: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Request custom/free-text spare item for a ticket.
    DC Protocol: Allows technicians to add spare items by name when exact stock item is unknown.
    Procurement team can later verify and map to actual stock items.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    company_id = getattr(ticket, 'company_id', None) or 1
    source_type = 'technical_ticket' if ticket.ticket_type == 'technical' else 'service_ticket'

    from app.models.marketplace import MarketplacePurchaseOrder, MarketplacePOItem
    from sqlalchemy import text as _text
    ym = datetime.utcnow().strftime('%Y%m')
    prefix = f'ZYPO-{ym}-'
    row = db.execute(_text(
        "SELECT COUNT(*)+1 FROM marketplace_purchase_orders WHERE po_number LIKE :pfx AND company_id=:cid"
    ), {'pfx': prefix + '%', 'cid': company_id}).fetchone()
    cnt = int(row[0]) if row else 1
    po_num = f'{prefix}{cnt:04d}'
    while db.query(MarketplacePurchaseOrder).filter_by(po_number=po_num).first():
        cnt += 1; po_num = f'{prefix}{cnt:04d}'

    _est = float(estimated_cost or 0)
    _gst_val = round(_est * 18 / 100, 2)
    _total = round((_est + _gst_val) * quantity_required, 2)
    po = MarketplacePurchaseOrder(
        po_number=po_num, po_count=cnt,
        customer_name=f'Service Ticket {ticket.ticket_id}',
        customer_phone='N/A', customer_type='service_ticket',
        total_items=1, total_ordered_qty=quantity_required, total_value=_total,
        status='draft', notes=f'Draft PO for custom spare on ticket {ticket.ticket_id}',
        source_type=source_type, source_ticket_id=ticket.id, company_id=company_id,
    )
    db.add(po); db.flush()
    # ── Store task hook ──────────────────────────────────────────────────────
    try:
        from app.services.store_task_service import add_po_phase as _svc_add_po
        _svc_add_po(db, po, company_id)
    except Exception as _e:
        import logging; logging.getLogger(__name__).error(f'[StoreTask] tickets PO hook: {_e}')
    # ─────────────────────────────────────────────────────────────────────────
    po_item = MarketplacePOItem(
        po_id=po.id, sku='CUSTOM', product_name=spare_item_name,
        ordered_qty=quantity_required, dealer_price=_est, net_price=_est,
        gst_percent=18, gst_amount=_gst_val * quantity_required,
        unit_final_price=round(_est + _gst_val, 2), line_total=_total,
        stock_available=0, procurement_required=True, company_id=company_id,
    )
    db.add(po_item); db.flush()

    spare_request = ServiceTicketSpareRequest(
        ticket_id=ticket_id,
        spare_item_name=spare_item_name,
        spare_description=spare_description,
        quantity_required=quantity_required,
        estimated_cost=estimated_cost,
        request_notes=request_notes,
        requested_by_id=staff.id,
        is_custom=True,
        original_item_name=spare_item_name,
        procurement_status='pending',
        marketplace_po_id=po.id,
    )
    db.add(spare_request)
    
    ticket.spares_required = True
    ticket.spare_requested_at = datetime.utcnow()
    if ticket.sub_status in ['new', 'acknowledged', 'diagnosing']:
        ticket.sub_status = 'awaiting_spares'
    
    log = TicketLog(
        ticket_id=ticket_id,
        action_type='custom_spare_requested',
        action_description=f'Custom spare requested: {spare_item_name} x{quantity_required} | ZYPO {po_num} (draft)',
        staff_performer_id=staff.id
    )
    db.add(log)
    
    db.commit()
    db.refresh(spare_request)
    
    return {
        "success": True,
        "message": "Custom spare request created",
        "spare_request": spare_request.to_dict(),
        "zypo_number": po_num,
    }


@router.put("/service/spares/{spare_id}/update")
async def update_spare_request(
    spare_id: int,
    spare_item_name: Optional[str] = Body(default=None),
    spare_description: Optional[str] = Body(default=None),
    quantity_required: Optional[int] = Body(default=None),
    estimated_cost: Optional[float] = Body(default=None),
    request_notes: Optional[str] = Body(default=None),
    marketplace_spare_id: Optional[int] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Update spare request details.
    DC Protocol: Allows updating spare item name, quantity, or notes before verification.
    When marketplace_spare_id is supplied, links the spare to a catalog product and
    re-runs pricing enrichment. Sets is_custom=False.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog
    from app.models.marketplace import (
        MarketspareItem, MarketplacePurchaseOrder, MarketplacePOItem,
        MarketplaceCategoryConfig,
    )
    from app.services.marketplace_pricing import enrich_product_with_pricing
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    spare = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.id == spare_id
    ).first()
    
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")
    
    if spare.procurement_status in ('released', 'dispatched', 'cancelled'):
        raise HTTPException(status_code=400, detail=f"Cannot update spare in status '{spare.procurement_status}'")
    
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == spare.ticket_id).first()
    company_id = getattr(ticket, 'company_id', None) or 1 if ticket else 1

    updates = []
    if spare_item_name and spare_item_name != spare.spare_item_name:
        if spare.is_custom and not spare.original_item_name:
            spare.original_item_name = spare.spare_item_name
        spare.spare_item_name = spare_item_name
        updates.append(f"name: {spare_item_name}")
    
    if spare_description is not None:
        spare.spare_description = spare_description
    
    if quantity_required is not None and quantity_required != spare.quantity_required:
        spare.quantity_required = quantity_required
        updates.append(f"qty: {quantity_required}")
        if spare.unit_price:
            spare.gst_amount = (spare.unit_price * quantity_required * (spare.gst_rate or 18)) / 100
            spare.total_with_gst = (spare.unit_price * quantity_required) + spare.gst_amount
    
    if estimated_cost is not None:
        spare.estimated_cost = estimated_cost
    
    if request_notes is not None:
        spare.request_notes = request_notes

    if marketplace_spare_id is not None:
        mkt_spare = db.query(MarketspareItem).filter(
            MarketspareItem.id == marketplace_spare_id,
            MarketspareItem.company_id == company_id,
            MarketspareItem.is_active == True,
        ).first()
        if not mkt_spare:
            raise HTTPException(status_code=404, detail="Catalog product not found or does not belong to this company")
        
        cfg = db.query(MarketplaceCategoryConfig).filter(
            MarketplaceCategoryConfig.company_id == company_id,
            MarketplaceCategoryConfig.category_name == mkt_spare.category_name,
        ).first()
        cfg_dict = cfg.to_dict() if cfg else {}
        enriched = enrich_product_with_pricing(mkt_spare.to_dict(), cfg_dict, spare.discount_mode)

        spare.marketplace_spare_id = marketplace_spare_id
        spare.spare_item_name = mkt_spare.name
        spare.spare_item_code = mkt_spare.sku
        spare.is_custom = False
        qty = quantity_required or spare.quantity_required or 1
        spare.unit_price = float(enriched.get('net_before_tax', enriched.get('dealer_price', 0)))
        spare.gst_rate = float(enriched.get('gst_percent', 18))
        spare.gst_amount = float(enriched.get('gst_amount', 0))
        spare.total_with_gst = float(enriched.get('final_price', 0))
        spare.hsn_code = enriched.get('hsn_code') or spare.hsn_code
        spare.catalog_price = float(enriched.get('dealer_price', 0))
        spare.discount_pct = float(enriched.get('discount_pct', 0))
        spare.discount_amount = float(enriched.get('discount_amount', 0))
        spare.net_before_tax = float(enriched.get('net_before_tax', 0))
        updates.append(f"linked catalog: {mkt_spare.sku} ({mkt_spare.name})")

        if spare.marketplace_po_id:
            draft_po = db.query(MarketplacePurchaseOrder).filter(
                MarketplacePurchaseOrder.id == spare.marketplace_po_id,
                MarketplacePurchaseOrder.status == 'draft',
            ).first()
            if draft_po:
                _unit_final = round(spare.unit_price + spare.gst_amount, 2)
                _line_total = round(_unit_final * qty, 2)
                draft_po.total_value = _line_total
                draft_po.total_ordered_qty = qty
                po_item = db.query(MarketplacePOItem).filter(
                    MarketplacePOItem.po_id == draft_po.id
                ).first()
                if po_item:
                    po_item.sku = mkt_spare.sku
                    po_item.product_name = mkt_spare.name
                    po_item.category_name = mkt_spare.category_name
                    po_item.brand = mkt_spare.brand
                    po_item.ordered_qty = qty
                    po_item.dealer_price = spare.unit_price
                    po_item.net_price = spare.unit_price
                    po_item.gst_percent = spare.gst_rate
                    po_item.gst_amount = spare.gst_amount * qty
                    po_item.unit_final_price = _unit_final
                    po_item.line_total = _line_total
    
    if updates and spare.marketplace_po_id and marketplace_spare_id is None:
        draft_po = db.query(MarketplacePurchaseOrder).filter(
            MarketplacePurchaseOrder.id == spare.marketplace_po_id,
            MarketplacePurchaseOrder.status == 'draft',
        ).first()
        if draft_po:
            _qty = spare.quantity_required or 1
            _up = float(spare.unit_price or spare.estimated_cost or 0)
            _gp = float(spare.gst_rate or 18)
            _ga = round(_up * _gp / 100, 2)
            _uf = round(_up + _ga, 2)
            _lt = round(_uf * _qty, 2)
            draft_po.total_ordered_qty = _qty
            draft_po.total_value = _lt
            po_item = db.query(MarketplacePOItem).filter(
                MarketplacePOItem.po_id == draft_po.id
            ).first()
            if po_item:
                po_item.product_name = spare.spare_item_name or po_item.product_name
                po_item.sku = spare.spare_item_code or po_item.sku
                po_item.ordered_qty = _qty
                po_item.dealer_price = _up
                po_item.net_price = _up
                po_item.gst_percent = _gp
                po_item.gst_amount = _ga * _qty
                po_item.unit_final_price = _uf
                po_item.line_total = _lt

    if updates:
        log = TicketLog(
            ticket_id=spare.ticket_id,
            action_type='spare_updated',
            action_description=f'Spare updated: {", ".join(updates)}',
            staff_performer_id=staff.id
        )
        db.add(log)
    
    db.commit()
    db.refresh(spare)

    result = {"success": True, "spare_request": spare.to_dict()}
    if spare.marketplace_po_id:
        from app.models.marketplace import MarketplacePurchaseOrder as _MPO
        _po = db.query(_MPO).filter(_MPO.id == spare.marketplace_po_id).first()
        if _po:
            result['marketplace_po_number'] = _po.po_number
    if spare.marketplace_procurement_id:
        from app.models.marketplace import MarketplaceProcurementRequest as _MPR
        _pr = db.query(_MPR).filter(_MPR.id == spare.marketplace_procurement_id).first()
        if _pr:
            result['marketplace_procurement_number'] = _pr.procurement_number
    
    return result


@router.post("/service/spares/{spare_id}/verify")
async def verify_custom_spare(
    spare_id: int,
    stock_item_id: int = Body(...),
    spare_item_name: Optional[str] = Body(default=None),
    spare_item_code: Optional[str] = Body(default=None),
    unit_price: Optional[float] = Body(default=None),
    gst_rate: Optional[float] = Body(default=None),
    hsn_code: Optional[str] = Body(default=None),
    verification_notes: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Verify and map custom spare to actual stock item.
    DC Protocol: Procurement team maps free-text spares to actual stock items.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog
    from app.models.staff_accounts import StockItemMaster
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    spare = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.id == spare_id
    ).first()
    
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")
    
    stock_item = db.query(StockItemMaster).filter(
        StockItemMaster.id == stock_item_id,
        StockItemMaster.is_active == True
    ).first()
    
    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    
    if spare.is_custom and not spare.original_item_name:
        spare.original_item_name = spare.spare_item_name
    
    spare.stock_item_id = stock_item_id
    spare.spare_item_name = spare_item_name or stock_item.item_name
    spare.spare_item_code = spare_item_code or stock_item.item_code
    spare.unit_price = unit_price if unit_price is not None else float(stock_item.selling_rate or 0)
    spare.gst_rate = gst_rate if gst_rate is not None else float(stock_item.default_gst_rate or 18)
    spare.hsn_code = hsn_code or stock_item.hsn_code
    spare.gst_amount = (spare.unit_price * spare.quantity_required * spare.gst_rate) / 100
    spare.total_with_gst = (spare.unit_price * spare.quantity_required) + spare.gst_amount
    spare.verified_by_id = staff.id
    spare.verified_at = datetime.utcnow()
    spare.verification_notes = verification_notes
    
    if stock_item.default_vendor_id:
        spare.vendor_id = stock_item.default_vendor_id
    
    log = TicketLog(
        ticket_id=spare.ticket_id,
        action_type='spare_verified',
        action_description=f'Custom spare verified: "{spare.original_item_name}" → "{spare.spare_item_name}" (Stock #{stock_item_id})',
        staff_performer_id=staff.id
    )
    db.add(log)
    
    db.commit()
    db.refresh(spare)
    
    return {
        "success": True,
        "message": "Custom spare verified and mapped to stock item",
        "spare_request": spare.to_dict()
    }


# ── DC Protocol Mar 2026: Spare lifecycle action endpoints ─────────────────────

@router.get("/service/spares/{spare_id}/availability")
async def get_spare_availability(
    spare_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Live stock availability check for a spare request."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest
    from app.models.marketplace import MarketspareItem

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")

    if not spare.marketplace_spare_id:
        return {"spare_id": spare_id, "marketplace_spare_id": None, "available_qty": None,
                "message": "No catalog link — manual/custom spare"}

    mkt = db.query(MarketspareItem).filter(MarketspareItem.id == spare.marketplace_spare_id).first()
    if not mkt:
        return {"spare_id": spare_id, "marketplace_spare_id": spare.marketplace_spare_id,
                "available_qty": 0, "message": "Catalog item not found"}

    aq = int(mkt.available_qty or 0)
    return {
        "spare_id": spare_id,
        "marketplace_spare_id": spare.marketplace_spare_id,
        "sku": mkt.sku,
        "name": mkt.name,
        "available_qty": aq,
        "quantity_required": spare.quantity_required,
        "in_stock": aq >= spare.quantity_required,
        "stock_status": "in_stock" if aq >= spare.quantity_required else "low_stock" if aq > 0 else "out_of_stock"
    }


@router.post("/service/spares/{spare_id}/accept")
async def accept_spare_request(
    spare_id: int,
    notes: Optional[str] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol Mar 2026: Store staff accepts/acknowledges a spare request.
    - Sets procurement_status = 'acknowledged'
    - Checks live stock; if in-stock → auto-create ZYPO; if out-of-stock → auto-create ZYPR
    - Linked PO/PR numbers returned in response for display.
    WVV: All DB writes in single transaction.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog
    from app.models.marketplace import MarketspareItem, MarketplacePurchaseOrder, MarketplacePOItem, MarketplaceProcurementRequest, MarketplaceCategoryConfig
    from app.services.ticket_service import TicketService

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")

    if spare.procurement_status not in ('pending', 'acknowledged'):
        raise HTTPException(status_code=400,
            detail=f"Cannot accept spare in status '{spare.procurement_status}' — only pending spares can be accepted")

    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == spare.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    po_number = None
    pr_number = None
    from sqlalchemy import text as _text

    if spare.marketplace_po_id:
        existing_po = db.query(MarketplacePurchaseOrder).filter(MarketplacePurchaseOrder.id == spare.marketplace_po_id).first()
        if existing_po and existing_po.status == 'draft':
            existing_po.status = 'confirmed'
            existing_po.confirmed_by_staff_id = staff.id
            existing_po.confirmed_at = datetime.utcnow()
            po_number = existing_po.po_number
            logger.info(f'[SPARE-ACCEPT] Draft ZYPO {po_number} confirmed on accept')

    if not spare.marketplace_po_id:
        # Attempt to load catalog item (not filtered by is_active — use spare data as fallback)
        mkt = None
        if spare.marketplace_spare_id:
            mkt = db.query(MarketspareItem).filter(
                MarketspareItem.id == spare.marketplace_spare_id
            ).first()

        aq = int(getattr(mkt, 'available_qty', 0) or 0)
        qty = spare.quantity_required or 1
        company_id = getattr(ticket, 'company_id', None) or 1
        source_type = 'technical_ticket' if ticket.ticket_type == 'technical' else 'service_ticket'
        ym = datetime.utcnow().strftime('%y%m')

        # Always create ZYPO — for both catalog and custom spares
        prefix_po = f'ZYPO-{ym}-'
        row_po = db.execute(_text("SELECT COUNT(*) FROM marketplace_purchase_orders WHERE po_number LIKE :pfx AND company_id = :cid"),
                         {'pfx': prefix_po + '%', 'cid': company_id}).fetchone()
        cnt_po = int(row_po[0]) if row_po else 1
        po_number = f'{prefix_po}{cnt_po:04d}'
        while db.query(MarketplacePurchaseOrder).filter_by(po_number=po_number).first():
            cnt_po += 1; po_number = f'{prefix_po}{cnt_po:04d}'

        # Pricing: prefer spare's own stored values, fall back to catalog item
        _unit_price = float(spare.unit_price or (mkt.dealer_price if mkt else None) or 0)
        _gst_pct = float(spare.gst_rate or (mkt.gst_percent if mkt else None) or 18)
        _gst_amt = round(_unit_price * _gst_pct / 100, 2)
        _unit_final = round(_unit_price + _gst_amt, 2)
        _line_total = round(_unit_final * qty, 2)
        po = MarketplacePurchaseOrder(
            po_number=po_number,
            company_id=company_id,
            customer_name=getattr(ticket, 'customer_name', None) or 'Service Ticket',
            customer_phone=getattr(ticket, 'customer_phone', None) or '0000000000',
            customer_type='service_ticket',
            total_items=1,
            total_ordered_qty=qty,
            total_value=_line_total,
            status='confirmed',
            source_type=source_type,
            source_ticket_id=ticket.id,
            notes=f'Auto-raised on spare accept for ticket {ticket.ticket_id}',
            confirmed_by_staff_id=staff.id,
        )
        db.add(po); db.flush()
        # ── Store task hook ──────────────────────────────────────────────────
        try:
            from app.services.store_task_service import add_po_phase as _svc_add_po2
            _svc_add_po2(db, po, company_id)
        except Exception as _e:
            import logging; logging.getLogger(__name__).error(f'[StoreTask] tickets PO2 hook: {_e}')
        # ────────────────────────────────────────────────────────────────────
        _sku = (mkt.sku if mkt else None) or spare.spare_item_code or ''
        poi = MarketplacePOItem(
            po_id=po.id,
            company_id=company_id,
            sku=_sku,
            product_name=spare.spare_item_name or '',
            ordered_qty=qty,
            dealer_price=_unit_price,
            net_price=_unit_price,
            gst_percent=_gst_pct,
            gst_amount=_gst_amt,
            unit_final_price=_unit_final,
            line_total=_line_total,
            stock_available=int(aq >= qty),
            procurement_required=(aq < qty),
        )
        db.add(poi); db.flush()
        spare.marketplace_po_id = po.id

        # ZYPR only for catalog spares with a stock shortfall
        if mkt and aq < qty:
            shortfall = qty - aq
            if not spare.marketplace_procurement_id:
                existing_proc = db.query(MarketplaceProcurementRequest).filter(
                    MarketplaceProcurementRequest.sku == (spare.spare_item_code or ''),
                    MarketplaceProcurementRequest.company_id == company_id,
                    MarketplaceProcurementRequest.status.in_(['pending', 'ordered']),
                ).first()
                if existing_proc:
                    # Update existing ZYPR with PO linkage and ticket context
                    existing_proc.po_id = po.id
                    existing_proc.po_item_id = poi.id
                    existing_proc.ordered_qty = max(int(existing_proc.ordered_qty or 0), qty)
                    existing_proc.shortfall_qty = shortfall
                    existing_proc.source_ticket_id = ticket.id
                    existing_proc.source_type = source_type
                    existing_proc.triggered_by = source_type
                    spare.marketplace_procurement_id = existing_proc.id
                    pr_number = existing_proc.procurement_number
                else:
                    prefix_pr = f'ZYPR-{ym}-'
                    row_pr = db.execute(_text("SELECT COUNT(*) FROM marketplace_procurement_requests WHERE procurement_number LIKE :pfx AND company_id = :cid"),
                                      {'pfx': prefix_pr + '%', 'cid': company_id}).fetchone()
                    cnt_pr = int(row_pr[0]) if row_pr else 1
                    pr_number = f'{prefix_pr}{cnt_pr:04d}'
                    while db.query(MarketplaceProcurementRequest).filter_by(procurement_number=pr_number).first():
                        cnt_pr += 1; pr_number = f'{prefix_pr}{cnt_pr:04d}'
                    proc = MarketplaceProcurementRequest(
                        procurement_number=pr_number, company_id=company_id,
                        sku=spare.spare_item_code or '', product_name=spare.spare_item_name or '',
                        ordered_qty=qty, available_qty=aq, shortfall_qty=shortfall,
                        po_id=po.id, po_item_id=poi.id,
                        triggered_by=source_type, status='pending',
                        source_type=source_type, source_ticket_id=ticket.id,
                    )
                    db.add(proc); db.flush()
                    # ── Store task hook ────────────────────────────────────
                    try:
                        from app.services.store_task_service import add_pr_phase as _svc_add_pr
                        _svc_add_pr(db, proc, company_id)
                    except Exception as _e:
                        import logging; logging.getLogger(__name__).error(f'[StoreTask] tickets PR hook: {_e}')
                    # ────────────────────────────────────────────────────────
                    spare.marketplace_procurement_id = proc.id

    # WVV: WRITE
    spare.procurement_status = 'acknowledged'
    spare.acknowledged_by_id = staff.id
    spare.acknowledged_at = datetime.utcnow()
    if notes:
        spare.acknowledgment_notes = notes

    db.add(TicketLog(
        ticket_id=spare.ticket_id,
        action_type='spare_accepted',
        action_description=f'Spare accepted by Store: {spare.spare_item_name}' +
            (f' | ZYPO: {po_number}' if po_number else '') +
            (f' | ZYPR: {pr_number}' if pr_number else ''),
        staff_performer_id=staff.id
    ))
    db.commit()
    db.refresh(spare)

    return {
        "success": True,
        "message": "Spare accepted" + (f" — ZYPO {po_number} created" if po_number else f" — ZYPR {pr_number} raised" if pr_number else ""),
        "spare_request": spare.to_dict(),
        "marketplace_po_number": po_number,
        "marketplace_procurement_number": pr_number
    }


@router.post("/service/spares/{spare_id}/cancel")
async def cancel_spare_request(
    spare_id: int,
    reason: Optional[str] = Body(default="Cancelled by staff", embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol Mar 2026: Cancel a spare request (before dispatch)."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog
    from app.models.marketplace import MarketplacePurchaseOrder, MarketplaceProcurementRequest

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")

    if spare.procurement_status == 'dispatched':
        raise HTTPException(status_code=400, detail="Cannot cancel an already dispatched spare")

    # Cancel linked ZYPO if still pending/confirmed
    if spare.marketplace_po_id:
        po = db.query(MarketplacePurchaseOrder).filter(MarketplacePurchaseOrder.id == spare.marketplace_po_id).first()
        if po and po.status in ('draft', 'pending', 'confirmed'):
            po.status = 'cancelled'
            po.notes = (po.notes or '') + f' | Cancelled: spare request cancelled ({reason})'

    spare.procurement_status = 'cancelled'
    spare.acknowledgment_notes = (spare.acknowledgment_notes or '') + f' | CANCELLED: {reason}'

    db.add(TicketLog(
        ticket_id=spare.ticket_id,
        action_type='spare_cancelled',
        action_description=f'Spare cancelled: {spare.spare_item_name}. Reason: {reason}',
        staff_performer_id=staff.id
    ))
    db.commit()
    db.refresh(spare)

    return {"success": True, "message": "Spare request cancelled", "spare_request": spare.to_dict()}


@router.get("/service/spares/{spare_id}/transactions")
async def get_spare_transactions(
    spare_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol Mar 2026: List all payment transactions for a spare request."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, ServiceTicketSpareTransaction
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")
    txns = db.query(ServiceTicketSpareTransaction).filter(
        ServiceTicketSpareTransaction.spare_request_id == spare_id
    ).order_by(ServiceTicketSpareTransaction.created_at).all()
    total_paid = sum(t.amount for t in txns)
    all_confirmed = all(t.income_entry_status == 'CONFIRMED' for t in txns) if txns else False
    # Legacy payment: recorded via old endpoint (direct on spare), no transaction record
    legacy_payment = None
    if not txns and spare.payment_amount and float(spare.payment_amount) > 0:
        legacy_payment = {
            "amount": float(spare.payment_amount),
            "payment_mode": spare.payment_mode,
            "payment_reference": spare.payment_reference,
            "payment_date": spare.payment_date.isoformat() if spare.payment_date else None,
            "payment_notes": spare.payment_notes,
            "income_entry_id": spare.income_entry_id,
        }
    return {
        "spare_request_id": spare_id,
        "spare_name": spare.spare_item_name,
        "is_warranty": getattr(spare, 'is_warranty', False) or False,
        "transactions": [t.to_dict() for t in txns],
        "total_paid": round(total_paid, 2),
        "count": len(txns),
        "all_confirmed": all_confirmed,
        "dispatch_allowed": getattr(spare, 'is_warranty', False) or (len(txns) > 0 and all_confirmed),
        "legacy_payment": legacy_payment,
    }


@router.delete("/service/spares/{spare_id}/transactions/{txn_id}")
async def delete_spare_transaction(
    spare_id: int,
    txn_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol Mar 2026: Delete a payment transaction only if income entry is still PENDING.
    Cannot delete once Accounts has CONFIRMED the income entry.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, ServiceTicketSpareTransaction, TicketLog
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    txn = db.query(ServiceTicketSpareTransaction).filter(
        ServiceTicketSpareTransaction.id == txn_id,
        ServiceTicketSpareTransaction.spare_request_id == spare_id
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.income_entry_status == 'CONFIRMED':
        raise HTTPException(status_code=400,
            detail=f"Cannot delete transaction {txn.transaction_number} — income entry already confirmed by Accounts")
    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    txn_number = txn.transaction_number
    txn_amount = txn.amount
    db.delete(txn)
    # Recalculate total paid on spare (legacy field sync)
    remaining = db.query(ServiceTicketSpareTransaction).filter(
        ServiceTicketSpareTransaction.spare_request_id == spare_id
    ).all()
    if remaining:
        spare.payment_amount = round(sum(t.amount for t in remaining), 2)
    else:
        spare.payment_amount = 0.0
        spare.procurement_status = 'acknowledged'
    db.add(TicketLog(
        ticket_id=spare.ticket_id,
        action_type='spare_transaction_deleted',
        action_description=f'Transaction {txn_number} (₹{txn_amount:.2f}) deleted by {staff.full_name}',
        staff_performer_id=staff.id
    ))
    db.commit()
    return {"success": True, "message": f"Transaction {txn_number} deleted", "deleted_id": txn_id}


@router.get("/service/{ticket_id}/spare-transactions")
async def get_ticket_spare_transactions(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol Mar 2026: All spare payment transactions for a ticket (ticket-level view)."""
    from app.models.ticket import ServiceTicketSpareRequest, ServiceTicketSpareTransaction as SpTxn, ServiceTicket as SvcTicket, ServiceTicketBilling
    if not current_user:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    ticket = db.query(SvcTicket).filter(SvcTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    spares = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.ticket_id == ticket_id
    ).order_by(ServiceTicketSpareRequest.id).all()

    spare_status_labels = {
        'pending': 'Pending',
        'acknowledged': 'Payment Pending',
        'payment_received': 'Payment Received',
        'waiting_for_spares': 'Waiting for Spares',
        'dispatched': 'Dispatched',
        'cancelled': 'Cancelled',
        'ordered': 'Ordered',
        'received': 'Received',
        'released': 'Released',
    }

    all_transactions = []
    spares_summary = []
    total_spare_value = 0.0
    total_paid = 0.0
    total_confirmed_paid = 0.0
    total_pending_paid = 0.0
    total_accepted_value = 0.0
    total_accepted_net_value = 0.0

    for spare in spares:
        if spare.procurement_status == 'cancelled':
            continue

        # DC-CUSTOMER-SPARE-001: customer-supplied parts have no company cost — zero out and summarise separately
        is_customer_spare = getattr(spare, 'spare_source', 'company') == 'customer'
        if is_customer_spare:
            spares_summary.append({
                "spare_id": spare.id,
                "spare_name": spare.spare_item_name,
                "procurement_status": spare.procurement_status,
                "procurement_status_label": spare_status_labels.get(spare.procurement_status or 'pending', spare.procurement_status or 'Pending'),
                "is_warranty": False,
                "is_accepted": True,
                "spare_value": 0.0,
                "net_value": 0.0,
                "total_paid": 0.0,
                "confirmed_paid": 0.0,
                "pending_paid": 0.0,
                "outstanding": 0.0,
                "dispatch_allowed": True,
                "txn_count": 0,
                "spare_source": "customer",
                "repair_route": getattr(spare, 'repair_route', None),
                "sub_ticket_number": getattr(spare, 'sub_ticket_number', None),
            })
            continue

        # DC Protocol Mar 2026: is_warranty is authoritative — read it FIRST so it governs
        # spare_value and net_value. Python `or` is falsy on 0.0 so explicit None-check used.
        is_warranty = bool(getattr(spare, 'is_warranty', False))

        # Compute raw spare value with explicit None guard (avoids 0.0 falsy bypass)
        _twg = spare.total_with_gst
        _up  = spare.unit_price
        spare_value_raw = float(_twg if _twg is not None else (_up if _up is not None else 0))

        # Warranty spares are ₹0 — is_warranty flag is authoritative regardless of stored values
        if is_warranty:
            spare_value = 0.0
            net_value   = 0.0
        else:
            spare_value = spare_value_raw
            # net_value = ex-GST (pre-tax) amount — used for "Estimated" view
            _net_raw = getattr(spare, 'net_before_tax', None)
            _gst_raw = getattr(spare, 'gst_amount',    None)
            if _net_raw is not None and float(_net_raw) > 0:
                # net_before_tax is per-unit; multiply by qty for total
                qty_f = float(spare.quantity_required or 1)
                net_value = round(float(_net_raw) * qty_f, 2)
            elif _gst_raw is not None and float(_gst_raw) > 0 and spare_value > 0:
                net_value = round(spare_value - float(_gst_raw), 2)
            elif spare_value > 0:
                _gst_r = float(getattr(spare, 'gst_rate', None) or 18)
                net_value = round(spare_value / (1 + _gst_r / 100), 2)
            else:
                net_value = 0.0

        total_spare_value += spare_value

        txns = db.query(SpTxn).filter(
            SpTxn.spare_request_id == spare.id
        ).order_by(SpTxn.created_at).all()

        confirmed_txn_amt = sum(t.amount for t in txns if t.income_entry_status == 'CONFIRMED')
        pending_txn_amt   = sum(t.amount for t in txns if t.income_entry_status != 'CONFIRMED')
        spare_paid = sum(t.amount for t in txns)
        # Legacy payment fallback (recorded on spare directly before transaction system)
        if not txns and spare.payment_amount and float(spare.payment_amount) > 0:
            spare_paid = float(spare.payment_amount)
            confirmed_txn_amt = spare_paid
            pending_txn_amt = 0.0

        total_paid += spare_paid

        for t in txns:
            all_transactions.append({
                **t.to_dict(),
                "spare_name": spare.spare_item_name,
                "spare_id": spare.id,
            })
        is_accepted = spare.procurement_status not in ('pending', 'cancelled')
        all_confirmed = all(t.income_entry_status == 'CONFIRMED' for t in txns) if txns else False
        dispatch_allowed = is_warranty or (len(txns) > 0 and all_confirmed)

        if is_accepted and not is_warranty:
            total_confirmed_paid += confirmed_txn_amt
            total_pending_paid += pending_txn_amt
            total_accepted_value += spare_value
            total_accepted_net_value += net_value

        spares_summary.append({
            "spare_id": spare.id,
            "spare_name": spare.spare_item_name,
            "procurement_status": spare.procurement_status,
            "procurement_status_label": spare_status_labels.get(spare.procurement_status or 'pending', spare.procurement_status or 'Pending'),
            "is_warranty": is_warranty,
            "is_accepted": is_accepted,
            "spare_value": round(spare_value, 2),      # total with GST — Invoice amount
            "net_value": round(net_value, 2),           # ex-GST — Estimated amount
            "total_paid": round(spare_paid, 2),
            "confirmed_paid": round(confirmed_txn_amt, 2),
            "pending_paid": round(pending_txn_amt, 2),
            "outstanding": round(max(0, spare_value - spare_paid), 2),
            "dispatch_allowed": dispatch_allowed,
            "txn_count": len(txns),
            "spare_source": getattr(spare, 'spare_source', 'company') or 'company',
            "repair_route": getattr(spare, 'repair_route', None),
            "sub_ticket_number": getattr(spare, 'sub_ticket_number', None),
        })

    # Sort all transactions by created_at
    all_transactions.sort(key=lambda x: x.get('created_at') or '')

    total_outstanding = round(max(0, total_spare_value - total_paid), 2)
    # Net payable is only for accepted (acknowledged+) non-warranty spares
    accepted_outstanding = round(max(0, total_accepted_value - total_confirmed_paid), 2)
    fully_paid = accepted_outstanding <= 0.01 if total_accepted_value > 0 else False
    all_dispatched = all(s['procurement_status'] == 'dispatched' for s in spares_summary) if spares_summary else False

    # net outstanding = ex-tax payable minus confirmed paid
    accepted_net_outstanding = round(max(0, total_accepted_net_value - total_confirmed_paid), 2)

    # DC Protocol Mar 2026: include billing summary for service/labour items
    billing_summary = None
    billing_rec = db.query(ServiceTicketBilling).filter(ServiceTicketBilling.ticket_id == ticket_id).first()
    if billing_rec:
        billing_outstanding = round(max(0, (billing_rec.net_payable or 0) - (billing_rec.amount_paid or 0)), 2)
        billing_summary = {
            "billing_id": billing_rec.id,
            "document_type": billing_rec.document_type,
            "status": billing_rec.status,
            "payment_status": billing_rec.payment_status,
            "total_amount": round(billing_rec.total_amount or 0, 2),
            "net_payable": round(billing_rec.net_payable or 0, 2),
            "amount_paid": round(billing_rec.amount_paid or 0, 2),
            "outstanding": billing_outstanding,
            "company_name": billing_rec.company.company_name if billing_rec.company else None,
        }

    return {
        "ticket_id": ticket_id,
        "spares_summary": spares_summary,
        "transactions": all_transactions,
        "total_spare_value": round(total_spare_value, 2),
        "total_accepted_value": round(total_accepted_value, 2),         # with GST — Invoice basis
        "total_accepted_net_value": round(total_accepted_net_value, 2), # ex-GST  — Estimated basis
        "total_paid": round(total_paid, 2),
        "total_confirmed_paid": round(total_confirmed_paid, 2),
        "total_pending_paid": round(total_pending_paid, 2),
        "total_outstanding": total_outstanding,
        "accepted_outstanding": accepted_outstanding,                    # Invoice outstanding
        "accepted_net_outstanding": accepted_net_outstanding,           # Estimated outstanding
        "fully_paid": fully_paid,
        "all_dispatched": all_dispatched,
        "payable_spares": [s for s in spares_summary if not s['is_warranty'] and s['procurement_status'] not in ('cancelled', 'dispatched')],
        "billing_summary": billing_summary,
    }


@router.post("/service/spares/{spare_id}/payment")
async def record_spare_payment(
    spare_id: int,
    amount: float = Body(..., gt=0),
    payment_mode: str = Body(...),
    payment_reference: Optional[str] = Body(default=None),
    payment_date_str: Optional[str] = Body(default=None, alias="payment_date"),
    payment_notes: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol Mar 2026: Add a payment transaction for a spare (multi-transaction, CRM-style).
    WVV: Creates IncomeEntry (PENDING) + SpareTransaction atomically.
    Accounts must CONFIRM the income entry before dispatch is allowed.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, ServiceTicketSpareTransaction, TicketLog
    from app.models.staff_accounts import IncomeEntry, IncomeSourceType
    from sqlalchemy import text as _text
    import decimal

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    valid_modes = ['CASH', 'BANK', 'UPI', 'CHEQUE', 'DD', 'NEFT', 'RTGS', 'CARD']
    payment_mode = (payment_mode or '').upper()
    if payment_mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid payment mode. Use: {', '.join(valid_modes)}")

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")
    if spare.procurement_status == 'dispatched':
        raise HTTPException(status_code=400, detail="Spare already dispatched — cannot add payment")
    if spare.procurement_status == 'cancelled':
        raise HTTPException(status_code=400, detail="Spare is cancelled")

    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == spare.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # DC-IE-DEDUP-SPARE-001: Idempotency guard — prevent double-submit race creating orphan IEs.
    # If an identical payment (same spare_id, amount, mode) was recorded within the last 60 seconds,
    # return the existing transaction instead of creating a duplicate.
    from sqlalchemy import text as _dedup_text
    from datetime import timedelta
    _cutoff = datetime.utcnow() - timedelta(seconds=60)
    _recent = db.execute(_dedup_text(
        "SELECT st.income_entry_number, st.transaction_number FROM service_ticket_spare_transactions st "
        "WHERE st.spare_request_id = :sid AND st.amount = :amt "
        "AND upper(st.payment_mode) = :mode AND st.created_at >= :cutoff "
        "ORDER BY st.created_at DESC LIMIT 1"
    ), {'sid': spare_id, 'amt': float(round(amount, 2)), 'mode': payment_mode, 'cutoff': _cutoff}).fetchone()
    if _recent:
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate submission detected — payment already recorded as {_recent[1]} "
                   f"(IE: {_recent[0] or 'pending'}). Please refresh and try again if this is a new payment."
        )

    pay_date = datetime.utcnow()
    if payment_date_str:
        try:
            pay_date = datetime.fromisoformat(payment_date_str.replace('Z', ''))
        except Exception:
            pass

    # WVV: READ — get SVC_SPARE income source
    income_source = db.query(IncomeSourceType).filter(
        IncomeSourceType.source_code == 'SVC_SPARE', IncomeSourceType.is_active == True
    ).first() or db.query(IncomeSourceType).filter(
        IncomeSourceType.source_code == 'SERVICE', IncomeSourceType.is_active == True
    ).first()

    ie_number = None
    income_entry_id = None
    if income_source:
        # Generate IE number using MAX(id) to avoid COUNT(*) race on deletions
        year_prefix = f"IE-{datetime.utcnow().year}-"
        last_row = db.execute(_text(
            "SELECT entry_number FROM income_entries WHERE entry_number LIKE :pfx ORDER BY id DESC LIMIT 1"
        ), {'pfx': year_prefix + '%'}).fetchone()
        last_num = int(last_row[0].split('-')[-1]) if last_row else 0
        ie_number = f"{year_prefix}{last_num + 1:05d}"
        company_id = 2  # Zynova Mobility Pvt Ltd — spare payments always booked to Zynova
        # Derive payment_type (CASH|BANK) from payment_mode per check constraint
        _payment_type = 'CASH' if payment_mode == 'CASH' else 'BANK'
        income_entry = IncomeEntry(
            entry_number=ie_number,
            company_id=company_id,
            income_source_id=income_source.id,
            income_date=pay_date.date(),
            amount=decimal.Decimal(str(round(amount, 2))),
            reference_type='SERVICE_TICKET_SPARE',
            reference_id=ticket.ticket_id,
            payment_mode=payment_mode,
            payment_type=_payment_type,
            payment_reference=payment_reference,
            payment_date=pay_date.date(),
            payer_name=getattr(ticket, 'customer_name', None),
            payer_contact=getattr(ticket, 'customer_phone', None),
            narration=f'Spare payment: ticket {ticket.ticket_id} | {spare.spare_item_name}'
                      + (f' | Ref: {payment_reference}' if payment_reference else ''),
            collected_by_id=staff.id,
            destination_type='COMPANY_ACCOUNT',
            destination_company_id=company_id,
            created_by_id=staff.id,
            status='PENDING',   # Accounts must confirm
        )
        db.add(income_entry)
        db.flush()
        income_entry_id = income_entry.id
        spare.income_entry_id = income_entry_id  # keep legacy ref to most recent

    # Generate transaction number SPRTXN-YYMM-NNNN
    ym = datetime.utcnow().strftime('%y%m')
    pfx = f'SPRTXN-{ym}-'
    cnt_row = db.execute(_text("SELECT COUNT(*) FROM service_ticket_spare_transactions WHERE transaction_number LIKE :p"),
                         {'p': pfx + '%'}).fetchone()
    txn_number = f"{pfx}{(int(cnt_row[0]) if cnt_row else 0) + 1:04d}"

    txn = ServiceTicketSpareTransaction(
        spare_request_id=spare_id,
        ticket_id=spare.ticket_id,
        transaction_number=txn_number,
        amount=amount,
        payment_mode=payment_mode,
        payment_reference=payment_reference,
        payment_date=pay_date,
        payment_notes=payment_notes,
        income_entry_id=income_entry_id,
        income_entry_number=ie_number,
        income_entry_status='PENDING',
        created_by_id=staff.id,
    )
    db.add(txn)

    # Update spare legacy payment fields (running total)
    existing_total = float(spare.payment_amount or 0)
    spare.payment_amount = round(existing_total + amount, 2)
    spare.payment_mode = payment_mode
    spare.payment_reference = payment_reference
    spare.payment_date = pay_date
    spare.payment_notes = payment_notes
    if spare.procurement_status in ('pending', 'acknowledged'):
        spare.procurement_status = 'payment_received'

    db.add(TicketLog(
        ticket_id=spare.ticket_id,
        action_type='spare_payment_added',
        action_description=f'Payment ₹{amount:.2f} via {payment_mode} added for "{spare.spare_item_name}"'
            + (f' | IE: {ie_number} (PENDING Accounts review)' if ie_number else ''),
        staff_performer_id=staff.id
    ))
    db.commit()
    db.refresh(spare)
    db.refresh(txn)

    # Return all transactions for this spare
    all_txns = db.query(ServiceTicketSpareTransaction).filter(
        ServiceTicketSpareTransaction.spare_request_id == spare_id
    ).order_by(ServiceTicketSpareTransaction.created_at).all()

    return {
        "success": True,
        "message": f"Payment of ₹{amount:.2f} recorded via {payment_mode}. Awaiting Accounts confirmation.",
        "transaction": txn.to_dict(),
        "transactions": [t.to_dict() for t in all_txns],
        "income_entry_number": ie_number,
        "spare_request": spare.to_dict(),
        "total_paid": round(sum(t.amount for t in all_txns), 2),
    }


@router.post("/service/spares/{spare_id}/dispatch")
async def dispatch_spare_request(
    spare_id: int,
    notes: Optional[str] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol Mar 2026: Mark spare as physically dispatched to technician.
    Decrements stock quantity from marketplace_spares (physical dispatch event).
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog
    from app.models.marketplace import MarketspareItem

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    from app.models.ticket import ServiceTicketSpareTransaction

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")

    if spare.procurement_status == 'dispatched':
        raise HTTPException(status_code=400, detail="Spare already dispatched")
    if spare.procurement_status not in ('payment_received', 'acknowledged', 'waiting_for_spares'):
        raise HTTPException(status_code=400,
            detail=f"Cannot dispatch spare in status '{spare.procurement_status}'")

    # DC Protocol Mar 2026: Dispatch gate — warranty bypass OR all transactions confirmed
    if not getattr(spare, 'is_warranty', False):
        txns = db.query(ServiceTicketSpareTransaction).filter(
            ServiceTicketSpareTransaction.spare_request_id == spare_id
        ).all()
        if not txns:
            raise HTTPException(status_code=400,
                detail="Dispatch blocked — no payment recorded. Record payment first or mark item as warranty.")
        pending_txns = [t for t in txns if t.income_entry_status != 'CONFIRMED']
        if pending_txns:
            nums = ', '.join(t.transaction_number for t in pending_txns)
            raise HTTPException(status_code=400,
                detail=f"Dispatch blocked — {len(pending_txns)} transaction(s) pending Accounts confirmation: {nums}. "
                       f"Please confirm income entries in the Accounts › Income Entries page first.")

    # Decrement marketplace stock (physical dispatch event — DC rule: only on actual dispatch)
    if spare.marketplace_spare_id:
        mkt = db.query(MarketspareItem).filter(MarketspareItem.id == spare.marketplace_spare_id).first()
        if mkt:
            qty = spare.quantity_required or 1
            mkt.available_qty = max(0, int(mkt.available_qty or 0) - qty)

    spare.procurement_status = 'dispatched'
    spare.dispatched_at = datetime.utcnow()
    spare.dispatched_by_id = staff.id
    if notes:
        spare.release_notes = notes

    db.add(TicketLog(
        ticket_id=spare.ticket_id,
        action_type='spare_dispatched',
        action_description=f'Spare dispatched to technician: {spare.spare_item_name} (qty: {spare.quantity_required})'
            + (f' | {notes}' if notes else ''),
        staff_performer_id=staff.id
    ))
    db.commit()
    db.refresh(spare)

    return {"success": True, "message": f"Spare dispatched to technician", "spare_request": spare.to_dict()}


@router.post("/service/spares/{spare_id}/warranty-toggle")
async def toggle_spare_warranty(
    spare_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC Protocol Mar 2026 — Toggle is_warranty on a spare request.
    When marked warranty: cost fields set to ₹0 (bypasses payment gate, dispatch allowed).
    When unmarked: cost fields restored from catalog_price / discount_pct stored on spare.
    Blocked if spare is already dispatched or cancelled.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")

    if spare.procurement_status in ('dispatched', 'cancelled'):
        raise HTTPException(status_code=400,
            detail=f"Cannot change warranty status — spare is already {spare.procurement_status}")

    new_val = not bool(getattr(spare, 'is_warranty', False))
    spare.is_warranty = new_val

    if new_val:
        # Zero all cost columns — net_before_tax is per-unit (correct column name)
        spare.net_before_tax = 0.0
        spare.gst_amount     = 0.0
        spare.total_with_gst = 0.0
        action_desc = f'Spare marked as warranty (₹0): {spare.spare_item_name}'
    else:
        # Restore costs from catalog_price and discount_pct stored on spare
        catalog      = float(getattr(spare, 'catalog_price', None) or 0.0)
        disc_pct     = float(getattr(spare, 'discount_pct',  None) or 0.0)
        qty          = int(spare.quantity_required or 1)
        gst_pct      = float(getattr(spare, 'gst_rate', None) or 18.0)
        net_per_unit = round(catalog * (1 - disc_pct / 100), 4)   # per-unit, before GST
        net_total    = round(net_per_unit * qty, 2)
        gst          = round(net_total * gst_pct / 100, 2)
        spare.net_before_tax = round(net_per_unit, 2)              # per-unit column
        spare.gst_amount     = gst
        spare.total_with_gst = round(net_total + gst, 2)
        action_desc = f'Spare warranty removed — cost restored (₹{spare.total_with_gst:.2f}): {spare.spare_item_name}'

    db.add(TicketLog(
        ticket_id=spare.ticket_id,
        action_type='spare_warranty_toggled',
        action_description=action_desc,
        staff_performer_id=staff.id
    ))
    db.commit()
    db.refresh(spare)
    return {"success": True, "is_warranty": new_val, "spare_request": spare.to_dict()}


@router.post("/service/{ticket_id}/complete")
async def complete_service_work(
    ticket_id: int,
    data: ServiceTicketComplete = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Mark service work as complete"""
    from app.core.security import get_current_staff_user_from_hybrid
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    result = TicketService.complete_work(
        db=db,
        ticket_id=ticket_id,
        staff_id=staff.id,
        user_id=current_user.id,
        resolution_summary=data.resolution_summary
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/service/{ticket_id}/close")
async def close_service_ticket(
    ticket_id: int,
    data: Optional[ServiceTicketClose] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Close service ticket after billing
    
    DC Protocol Jan 2026: Accepts optional ServiceTicketClose body
    - Handles empty body {} gracefully
    - customer_satisfaction: Optional 1-5 rating
    """
    from app.core.security import get_current_staff_user_from_hybrid
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    customer_satisfaction = data.customer_satisfaction if data else None
    force_close = data.force_close if data else False
    
    if force_close:
        _role_code = ''
        if hasattr(staff, 'role') and staff.role:
            _role_code = (getattr(staff.role, 'role_code', '') or '').lower().strip()
        _admin_codes = {'admin', 'superadmin', 'key_leadership', 'vgk4u', 'manager', 'service_head', 'service_incharge', 'ea'}
        if _role_code not in _admin_codes:
            raise HTTPException(status_code=403, detail="Only admin/manager roles can force-close tickets with pending spares")
    
    result = TicketService.close_service_ticket(
        db=db,
        ticket_id=ticket_id,
        staff_id=staff.id,
        user_id=current_user.id,
        customer_satisfaction=customer_satisfaction,
        force_close=force_close
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # DC_WA_TEMPLATES_SEED_001: Notify customer on ticket close (non-fatal)
    try:
        from app.services.whatsapp_auto_service import send_ticket_closed_wa
        _closed = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
        if _closed:
            send_ticket_closed_wa(db, _closed)
    except Exception as _wa_cl:
        logger.warning(f"[WA-AUTO] ticket_closed WA error (non-fatal): {_wa_cl}")

    return result


@router.get("/service/dashboard/stats")
async def get_service_dashboard_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get service ticket dashboard statistics"""
    from datetime import timedelta
    from sqlalchemy import func
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    tickets = db.query(ServiceTicket).filter(
        ServiceTicket.created_date >= cutoff_date,
        ServiceTicket.ticket_type.in_(['technical', 'spares'])
    ).all()
    
    total = len(tickets)
    by_status = {}
    by_sub_status = {}
    by_type = {}
    
    for ticket in tickets:
        by_status[ticket.status] = by_status.get(ticket.status, 0) + 1
        by_sub_status[ticket.sub_status or 'unknown'] = by_sub_status.get(ticket.sub_status or 'unknown', 0) + 1
        by_type[ticket.ticket_type or 'general'] = by_type.get(ticket.ticket_type or 'general', 0) + 1
    
    sla_breached = sum(1 for t in tickets if t.sla_status == 'SLA Breached')
    avg_resolution = None
    resolution_times = [t.resolution_time_hours for t in tickets if t.resolution_time_hours]
    if resolution_times:
        avg_resolution = sum(resolution_times) / len(resolution_times)
    
    return {
        "total_tickets": total,
        "by_status": by_status,
        "by_sub_status": by_sub_status,
        "by_type": by_type,
        "sla_breached": sla_breached,
        "average_resolution_hours": avg_resolution,
        "date_range": f"Last {days} days"
    }


# ===== DC PROTOCOL JAN 2026: BILLING ENDPOINTS =====

@router.post("/service/{ticket_id}/billing/create")
async def create_service_billing(
    ticket_id: int,
    document_type: str = Body(default='bill'),
    is_gst_invoice: bool = Body(default=False),
    company_id: Optional[int] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Create billing record for a service ticket"""
    from app.core.security import get_current_staff_user_from_hybrid
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    result = TicketService.create_billing(
        db=db,
        ticket_id=ticket_id,
        document_type=document_type,
        is_gst_invoice=is_gst_invoice,
        company_id=company_id,
        created_by_id=staff.id
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.get("/service/{ticket_id}/billing")
async def get_service_billing(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get billing record for a service ticket"""
    from app.models.ticket import ServiceTicketBilling, ServiceTicketBillingItem
    
    billing = db.query(ServiceTicketBilling).filter(
        ServiceTicketBilling.ticket_id == ticket_id
    ).first()
    
    if not billing:
        return {"billing": None, "items": []}
    
    items = db.query(ServiceTicketBillingItem).filter(
        ServiceTicketBillingItem.billing_id == billing.id
    ).all()
    
    # DC Protocol Mar 2026: Enrich billing spare items from marketplace (single source of truth)
    from app.models.ticket import ServiceTicketSpareRequest as _STSpare
    from app.models.marketplace import MarketspareItem as _MktSpare2, MarketplaceCategoryConfig as _MktCatCfg2
    from app.services.marketplace_pricing import enrich_product_with_pricing as _enrich2

    spare_ids = [i.spare_request_id for i in items if i.spare_request_id]
    spare_map = {}
    mkt_enrich_map = {}
    if spare_ids:
        spares_q = db.query(_STSpare).filter(_STSpare.id.in_(spare_ids)).all()
        for sp in spares_q:
            spare_map[sp.id] = sp
        mkt_spare_ids2 = [sp.marketplace_spare_id for sp in spares_q if sp.marketplace_spare_id]
        if mkt_spare_ids2:
            mi_list2 = db.query(_MktSpare2).filter(_MktSpare2.id.in_(mkt_spare_ids2)).all()
            mi_map2 = {mi.id: mi for mi in mi_list2}
            cat_names2 = list({mi.category_name for mi in mi_list2 if mi.category_name})
            cfg_map2 = {}
            if cat_names2:
                _cfgs2 = db.query(_MktCatCfg2).filter(
                    _MktCatCfg2.category_name.in_(cat_names2),
                    _MktCatCfg2.company_id == 1
                ).all()
                for c in _cfgs2:
                    cfg_map2[c.category_name] = c.to_dict()
            # DC Protocol: ticket-level discount — if any spare has a discount_mode,
            # apply it to all spares in this ticket (one customer = one discount tier)
            ticket_disc_mode = next((sp.discount_mode for sp in spares_q if sp.discount_mode), None)
            for sp in spares_q:
                if sp.marketplace_spare_id and sp.marketplace_spare_id in mi_map2:
                    mi2 = mi_map2[sp.marketplace_spare_id]
                    eff_disc = sp.discount_mode or ticket_disc_mode
                    enriched2 = _enrich2(mi2.to_dict(), cfg_map2.get(mi2.category_name), eff_disc)
                    mkt_enrich_map[sp.id] = {
                        "display_mrp":          enriched2.get("display_mrp"),
                        "mrp_discount_amount":  enriched2.get("mrp_discount_amount"),
                        "mrp_discount_pct":     enriched2.get("mrp_discount_pct"),
                        "net_before_tax_unit":  enriched2.get("net_before_tax"),
                        "gst_percent_mkt":      enriched2.get("gst_percent"),
                        "gst_amount_unit":      enriched2.get("gst_amount"),
                        "final_price_unit":     enriched2.get("final_price"),
                        "markup_percent":       enriched2.get("markup_percent"),
                        "discount_amount_unit": enriched2.get("discount_amount"),
                        "dealer_price":         enriched2.get("dealer_price"),
                        "discount_mode":        eff_disc,
                        "mkt_specs":            mi2.specifications or '',
                        "mkt_color":            mi2.color or '',
                    }

    billing_items = []
    for i in items:
        sp_enrich = mkt_enrich_map.get(i.spare_request_id, {}) if i.spare_request_id else {}
        sp_raw = spare_map.get(i.spare_request_id) if i.spare_request_id else None
        billing_items.append({
            "id": i.id,
            "item_type": i.item_type,
            "description": i.description,
            "quantity": i.quantity,
            "rate": i.rate,
            "hsn_code": i.hsn_code,
            "taxable_amount": i.taxable_amount,
            "tax_rate": i.tax_rate,
            "cgst_amount": i.cgst_amount,
            "sgst_amount": i.sgst_amount,
            "line_total": i.line_total,
            "spare_request_id": i.spare_request_id,
            # Product detail fields (snapshot from marketplace or manually set)
            "specification":  i.specification or (sp_enrich.get("mkt_specs") or ''),
            "warranty_info":  i.warranty_info or '',
            "serial_numbers": i.serial_numbers or [],
            # Marketplace enriched pricing (single source of truth for spare items)
            **sp_enrich,
            # Fallback legacy fields from stored spare_request (for custom/non-catalog spares)
            "catalog_price":    float(sp_raw.catalog_price) if sp_raw and sp_raw.catalog_price and not sp_enrich else sp_enrich.get("display_mrp"),
            "discount_pct":     float(sp_raw.discount_pct) if sp_raw and sp_raw.discount_pct and not sp_enrich else None,
            "discount_amount":  float(sp_raw.discount_amount) if sp_raw and sp_raw.discount_amount and not sp_enrich else sp_enrich.get("discount_amount_unit"),
            "discount_mode":    sp_enrich.get("discount_mode") or (sp_raw.discount_mode if sp_raw else None),
        })

    return {"billing": billing.to_dict(), "items": billing_items}


@router.post("/service/billing/{billing_id}/add-item")
async def add_billing_item(
    billing_id: int,
    item_type: str = Body(...),
    description: str = Body(...),
    quantity: float = Body(default=1.0),
    rate: float = Body(...),
    hsn_code: Optional[str] = Body(default=None),
    tax_rate: float = Body(default=0.0),
    is_intrastate: bool = Body(default=True),
    product_category: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Add line item to billing"""
    from app.core.security import get_current_staff_user_from_hybrid
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    result = TicketService.add_billing_item(
        db=db,
        billing_id=billing_id,
        item_type=item_type,
        description=description,
        quantity=quantity,
        rate=rate,
        hsn_code=hsn_code,
        tax_rate=tax_rate,
        is_intrastate=is_intrastate,
        product_category=product_category or None,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.delete("/service/billing/{billing_id}/items/{item_id}")
async def delete_billing_item(
    billing_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol Mar 2026: Delete a billing line item (only while billing is draft)."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketBilling, ServiceTicketBillingItem
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    billing = db.query(ServiceTicketBilling).filter(ServiceTicketBilling.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Billing not found")
    if billing.status != 'draft':
        raise HTTPException(status_code=400, detail="Can only delete items from a draft billing")
    item = db.query(ServiceTicketBillingItem).filter(
        ServiceTicketBillingItem.id == item_id,
        ServiceTicketBillingItem.billing_id == billing_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Billing item not found")
    if item.item_type == 'spare':
        raise HTTPException(status_code=400, detail="Spare items cannot be deleted individually. Use Sync Spares to manage spare quantities.")
    db.delete(item)
    db.commit()
    # Re-fetch items to return updated list
    items = db.query(ServiceTicketBillingItem).filter(
        ServiceTicketBillingItem.billing_id == billing_id
    ).order_by(ServiceTicketBillingItem.id).all()
    return {"success": True, "message": "Item deleted", "items": [i.to_dict() for i in items]}


@router.patch("/service/billing/{billing_id}/items/{item_id}/serial-numbers")
async def update_billing_item_serial_numbers(
    billing_id: int,
    item_id: int,
    serial_numbers: Optional[list] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol Mar 2026: Update serial numbers on a billing line item (all item types, all billing states)."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketBilling, ServiceTicketBillingItem
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    billing = db.query(ServiceTicketBilling).filter(ServiceTicketBilling.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Billing not found")
    item = db.query(ServiceTicketBillingItem).filter(
        ServiceTicketBillingItem.id == item_id,
        ServiceTicketBillingItem.billing_id == billing_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Billing item not found")
    # Store serial numbers as a list of non-empty strings
    cleaned = [str(s).strip() for s in (serial_numbers or []) if str(s).strip()]
    item.serial_numbers = cleaned if cleaned else None
    db.commit()
    db.refresh(item)
    return {"success": True, "item_id": item_id, "serial_numbers": item.serial_numbers}


@router.patch("/service/tickets/{ticket_id}/vehicle-serial")
async def update_vehicle_serial(
    ticket_id: int,
    product_serial: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol Mar 2026: Staff endpoint to update vehicle serial/chassis number on a service ticket."""
    from app.core.security import get_current_staff_user_from_hybrid
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.product_serial = product_serial.strip() if product_serial else None
    db.commit()
    return {"success": True, "ticket_id": ticket_id, "product_serial": ticket.product_serial}


@router.post("/service/billing/{billing_id}/record-payment")
async def record_billing_payment(
    billing_id: int,
    amount: float = Body(..., gt=0),
    payment_mode: str = Body(...),
    payment_reference: Optional[str] = Body(default=None),
    payment_date: Optional[str] = Body(default=None),
    payment_notes: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol Mar 2026: Record a payment transaction against a billing record (service/labour items).
    Creates a PENDING income entry — Accounts must confirm. Supports partial and full payment."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketBilling, ServiceTicket as SvcTkt
    from app.models.staff_accounts import IncomeEntry, IncomeSourceType
    from sqlalchemy import text as _t
    import decimal

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    billing = db.query(ServiceTicketBilling).filter(ServiceTicketBilling.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Billing not found")
    if billing.payment_status == 'paid':
        raise HTTPException(status_code=400, detail="Billing already marked as fully paid")

    valid_modes = ['CASH', 'BANK', 'UPI', 'CHEQUE', 'DD', 'NEFT', 'RTGS', 'CARD']
    payment_mode = (payment_mode or '').upper()
    if payment_mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid payment mode. Use: {', '.join(valid_modes)}")

    ticket = db.query(SvcTkt).filter(SvcTkt.id == billing.ticket_id).first()

    pay_date_obj = datetime.utcnow()
    if payment_date:
        try:
            pay_date_obj = datetime.fromisoformat(payment_date.replace('Z', ''))
        except Exception:
            pass

    # Find income source (SVC_BILLING → SERVICE → first active)
    income_source = db.query(IncomeSourceType).filter(
        IncomeSourceType.source_code == 'SVC_BILLING', IncomeSourceType.is_active == True
    ).first() or db.query(IncomeSourceType).filter(
        IncomeSourceType.source_code == 'SERVICE', IncomeSourceType.is_active == True
    ).first() or db.query(IncomeSourceType).filter(
        IncomeSourceType.is_active == True
    ).first()

    ie_number = None
    if income_source:
        # Generate IE number using MAX(id) to avoid COUNT(*) race on deletions
        year_prefix = f"IE-{datetime.utcnow().year}-"
        last_row = db.execute(_t(
            "SELECT entry_number FROM income_entries WHERE entry_number LIKE :pfx ORDER BY id DESC LIMIT 1"
        ), {'pfx': year_prefix + '%'}).fetchone()
        last_num = int(last_row[0].split('-')[-1]) if last_row else 0
        ie_number = f"{year_prefix}{last_num + 1:05d}"
        company_id = billing.company_id or (staff.company_id if hasattr(staff, 'company_id') else 2)
        # Derive payment_type (CASH|BANK) from payment_mode per check constraint
        _billing_payment_type = 'CASH' if payment_mode == 'CASH' else 'BANK'
        ie = IncomeEntry(
            entry_number=ie_number,
            company_id=company_id,
            income_source_id=income_source.id,
            income_date=pay_date_obj.date(),
            amount=decimal.Decimal(str(round(amount, 2))),
            reference_type='SERVICE_TICKET_BILLING',
            reference_id=ticket.ticket_id if ticket else str(billing.ticket_id),
            payment_mode=payment_mode,
            payment_type=_billing_payment_type,
            payment_reference=payment_reference,
            payment_date=pay_date_obj.date(),
            payer_name=getattr(ticket, 'customer_name', None) if ticket else None,
            payer_contact=getattr(ticket, 'customer_phone', None) if ticket else None,
            narration=f'Service billing payment: ticket {billing.ticket_id} | billing #{billing_id}'
                      + (f' | {payment_notes}' if payment_notes else '')
                      + (f' | Ref: {payment_reference}' if payment_reference else ''),
            collected_by_id=staff.id,
            destination_type='COMPANY_ACCOUNT',
            destination_company_id=company_id,
            created_by_id=staff.id,
            status='PENDING',
        )
        db.add(ie)
        db.flush()

        # ── Link billing payment to ZYPO if one exists for this ticket ────────
        # So the payment appears in the PO page transactions modal
        try:
            from app.models.marketplace import MarketplacePurchaseOrder as _MPO
            from app.models.crm import CRMLeadTransaction as _CRMT
            _linked_po = db.query(_MPO).filter(
                _MPO.source_ticket_id == billing.ticket_id,
                _MPO.status.notin_(['cancelled'])
            ).order_by(_MPO.created_at.desc()).first()
            if _linked_po:
                _IE_MODE_REVERSE = {
                    'CASH': 'cash', 'UPI': 'upi', 'NEFT': 'neft', 'RTGS': 'rtgs',
                    'CHEQUE': 'cheque', 'CARD': 'card', 'DD': 'dd', 'BANK': 'other',
                }
                _pm_lower = _IE_MODE_REVERSE.get(payment_mode.upper(), 'other')
                _crmt = _CRMT(
                    company_id=company_id,
                    lead_id=None,
                    po_id=_linked_po.id,
                    transaction_date=pay_date_obj,
                    amount=amount,
                    transaction_type='partial',
                    payment_mode=_pm_lower,
                    collected_by_id=staff.id,
                    reference_number=payment_reference,
                    notes=f'Billing payment — ticket {billing.ticket_id} | billing #{billing_id}'
                          + (f' | {payment_notes}' if payment_notes else ''),
                    validation_status='pending',
                    income_entry_id=ie.id,
                    created_by_id=staff.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(_crmt)
        except Exception as _po_link_err:
            print(f'[BILLING-PAY] PO link failed (non-fatal): {_po_link_err}')
        # ──────────────────────────────────────────────────────────────────────

    # Update billing payment totals
    prev_paid = float(billing.amount_paid or 0)
    new_paid = round(prev_paid + amount, 2)
    billing.amount_paid = new_paid
    net = float(billing.net_payable or 0)
    billing.amount_due = round(max(0, net - new_paid), 2)
    if billing.amount_due <= 0.01:
        billing.payment_status = 'paid'
        billing.payment_mode = payment_mode
        billing.payment_reference = payment_reference
    else:
        billing.payment_status = 'partial'

    db.commit()
    return {
        "success": True,
        "message": f"Payment of ₹{amount:.2f} recorded via {payment_mode}",
        "income_entry_number": ie_number,
        "payment_status": billing.payment_status,
        "amount_paid": new_paid,
        "amount_due": billing.amount_due,
    }


@router.post("/service/billing/{billing_id}/apply-coupon")
async def apply_billing_coupon(
    billing_id: int,
    coupon_code: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC-BILLING-COUPON Mar 2026: Validate any marketplace discount code and apply to billing.
    Accepts all 5 marketplace discount types:
      1. Promo code   (marketplace_promo_codes, custom %)
      2. Partner code (official_partners DEALER/DISTRIBUTOR, default 12%)
      3. VGK code     (official_partners VGK_TEAM, activated=3%, non-activated=2%)
      4. MNR ID       (user table, activated=3%, non-activated=1.5%)
      5. Student ID   (etc_students, default 10%)
    Only allowed while billing is draft."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketBilling
    from app.models.marketplace import MarketplacePromoCode
    from app.models.base import get_indian_time
    from sqlalchemy import text as _text

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    billing = db.query(ServiceTicketBilling).filter(ServiceTicketBilling.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Billing not found")
    if billing.status != 'draft':
        raise HTTPException(status_code=400, detail="Coupons can only be applied to draft billings")

    code_val = coupon_code.strip().upper()
    now = get_indian_time()
    discount_pct = 0.0
    coupon_label = ''
    matched_type = None

    # ── 1. Marketplace promo code ───────────────────────────────────────
    pc = db.query(MarketplacePromoCode).filter(
        MarketplacePromoCode.code == code_val,
        MarketplacePromoCode.status == 'active',
    ).first()
    if pc:
        if (pc.valid_from and now < pc.valid_from) or \
           (pc.valid_to and now > pc.valid_to) or \
           (pc.usage_limit and pc.times_used >= pc.usage_limit):
            pc = None
    if pc:
        discount_pct = float(pc.default_discount_pct or 0)
        coupon_label = pc.label or f'Promo {code_val}'
        matched_type = 'promo'

    # ── 2. Official partner / dealer code (DEALER, DISTRIBUTOR) ────────
    if not matched_type:
        partner = db.execute(_text("""
            SELECT partner_name, partner_code, category
            FROM official_partners
            WHERE UPPER(partner_code) = :code
              AND is_active = true
              AND category NOT IN ('VGK_TEAM')
            LIMIT 1
        """), {'code': code_val}).fetchone()
        if partner:
            discount_pct = 12.0
            coupon_label = f'{partner.partner_name} (Partner)'
            matched_type = 'partner'

    # ── 3. VGK team member code ─────────────────────────────────────────
    if not matched_type:
        vgk = db.execute(_text("""
            SELECT partner_name, partner_code, vgk_points_balance, vgk_activated_at
            FROM official_partners
            WHERE UPPER(partner_code) = :code
              AND category = 'VGK_TEAM'
              AND is_active = true
            LIMIT 1
        """), {'code': code_val}).fetchone()
        if vgk:
            from app.models.ticket import ServiceTicketBillingItem as _BItem
            _items = db.query(_BItem).filter(_BItem.billing_id == billing_id).all()
            _is_act = bool(vgk.vgk_activated_at)
            _spares_rate = 3.0 if _is_act else 2.0

            # Separate EV Vehicle items from everything else
            _ev_items    = [i for i in _items if (i.product_category or '').strip() == 'EV Vehicle']
            _other_items = [i for i in _items if (i.product_category or '').strip() != 'EV Vehicle']
            _ev_qty      = sum(i.quantity or 0 for i in _ev_items)
            _ev_taxable  = sum(i.taxable_amount or 0 for i in _ev_items)
            _other_taxable = sum(i.taxable_amount or 0 for i in _other_items)
            _total_taxable = _ev_taxable + _other_taxable

            if _total_taxable <= 0 or _ev_qty == 0:
                # No EV vehicle items — flat EV Spares rate
                discount_pct = _spares_rate
            elif _ev_qty == 1:
                # EV B2C: L1 = 5% activated / 2% registered
                _vehicle_rate = 5.0 if _is_act else 2.0
                if _other_taxable > 0:
                    discount_pct = round(
                        (_ev_taxable * _vehicle_rate + _other_taxable * _spares_rate) / _total_taxable, 4
                    )
                else:
                    discount_pct = _vehicle_rate
            else:
                # EV B2B (2+ vehicles): L1 = 1% activated / 2% registered
                _vehicle_rate = 1.0 if _is_act else 2.0
                if _other_taxable > 0:
                    discount_pct = round(
                        (_ev_taxable * _vehicle_rate + _other_taxable * _spares_rate) / _total_taxable, 4
                    )
                else:
                    discount_pct = _vehicle_rate

            coupon_label = f'{vgk.partner_name} (VGK Member)'
            matched_type = 'vgk'

    # ── 4. MNR member ID ────────────────────────────────────────────────
    if not matched_type:
        mnr = db.execute(_text("""
            SELECT name, id, activation_date FROM "user"
            WHERE id = :mid AND account_status = 'Active'
            LIMIT 1
        """), {'mid': code_val}).fetchone()
        if mnr:
            is_activated = mnr.activation_date is not None
            discount_pct = 3.0 if is_activated else 1.5
            coupon_label = f'{mnr.name} (MNR Member)'
            matched_type = 'mnr'

    # ── 5. ETC student ID ───────────────────────────────────────────────
    if not matched_type:
        student = db.execute(_text("""
            SELECT name, student_id FROM etc_students
            WHERE UPPER(student_id) = :sid AND is_active = TRUE
            LIMIT 1
        """), {'sid': code_val}).fetchone()
        if student:
            discount_pct = 10.0
            coupon_label = f'{student.name} (Student)'
            matched_type = 'student'

    if not matched_type:
        raise HTTPException(status_code=400, detail="Coupon / discount code not found, expired, or inactive")

    # DC Protocol: Just set the coupon fields — _recalculate_billing_totals handles
    # applying the discount BEFORE GST, reducing both taxable base and GST proportionally.
    billing.coupon_code = code_val
    billing.coupon_discount_pct = discount_pct
    TicketService._recalculate_billing_totals(db, billing)
    db.commit()

    discount_amount = float(billing.discount_amount or 0)
    return {
        "success": True,
        "message": f"'{code_val}' applied — {discount_pct}% {matched_type} discount (₹{discount_amount:.2f} off taxable)",
        "coupon_code": code_val,
        "coupon_label": coupon_label,
        "coupon_type": matched_type,
        "discount_pct": discount_pct,
        "discount_amount": discount_amount,
        "net_payable": billing.net_payable,
        "billing": billing.to_dict(),
    }


@router.delete("/service/billing/{billing_id}/coupon")
async def remove_billing_coupon(
    billing_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC-BILLING-COUPON Mar 2026: Remove applied coupon from billing and reset discount."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketBilling

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    billing = db.query(ServiceTicketBilling).filter(ServiceTicketBilling.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Billing not found")
    if billing.status != 'draft':
        raise HTTPException(status_code=400, detail="Can only remove coupons from draft billings")

    billing.coupon_code = None
    billing.coupon_discount_pct = 0.0
    billing.discount_amount = 0.0
    TicketService._recalculate_billing_totals(db, billing)
    db.commit()

    return {
        "success": True,
        "message": "Coupon removed",
        "net_payable": billing.net_payable,
        "billing": billing.to_dict(),
    }


@router.patch("/service/billing/{billing_id}/manual-discount")
async def set_billing_manual_discount(
    billing_id: int,
    amount: float = Body(..., embed=True),
    note: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC-BILLING-MANUAL-DISC Mar 2026: Set (or clear) a manual post-GST flat discount on a draft billing.
    Pass amount=0 to remove. Manual discount is deducted from Grand Total (after coupon+GST),
    so GST distribution is not affected."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketBilling

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    billing = db.query(ServiceTicketBilling).filter(ServiceTicketBilling.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Billing not found")
    if billing.status != 'draft':
        raise HTTPException(status_code=400, detail="Manual discount can only be set on draft billings")

    disc_amt = round(max(0.0, float(amount or 0)), 2)
    if disc_amt > float(billing.total_amount or 0):
        raise HTTPException(status_code=400, detail="Manual discount cannot exceed the billing total")

    billing.manual_discount_amount = disc_amt
    billing.manual_discount_note = (note or '').strip() or None
    TicketService._recalculate_billing_totals(db, billing)
    db.commit()

    action = "removed" if disc_amt == 0 else f"set to ₹{disc_amt:.2f}"
    return {
        "success": True,
        "message": f"Manual discount {action}",
        "manual_discount_amount": disc_amt,
        "net_payable": billing.net_payable,
        "billing": billing.to_dict(),
    }


@router.get("/service/billing/companies")
async def list_billing_companies(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol Mar 2026: Return associated companies for billing company selector."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.staff_accounts import AssociatedCompany
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    companies = db.query(AssociatedCompany).order_by(AssociatedCompany.id).all()
    return {"companies": [{"id": c.id, "name": c.company_name} for c in companies]}


@router.patch("/service/billing/{billing_id}/company")
async def update_billing_company(
    billing_id: int,
    company_id: Optional[int] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC Protocol Mar 2026: Set or clear the company on a service billing (for invoice/estimate header)."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketBilling
    from app.models.staff_accounts import AssociatedCompany
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    billing = db.query(ServiceTicketBilling).filter(ServiceTicketBilling.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=404, detail="Billing not found")
    if company_id is not None:
        company = db.query(AssociatedCompany).filter(AssociatedCompany.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        billing.company_id = company_id
    else:
        billing.company_id = None
    db.commit()
    db.refresh(billing)
    return {"success": True, "company_id": billing.company_id, "company_name": billing.company.company_name if billing.company else None, "billing": billing.to_dict()}


@router.post("/service/{ticket_id}/billing/auto-populate")
async def auto_populate_billing_items(
    ticket_id: int,
    service_charge: float = Body(default=0.0),
    labour_charge: float = Body(default=0.0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Auto-populate billing items from spare requests + add service/labour charges"""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketBilling, ServiceTicketSpareRequest
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    billing = db.query(ServiceTicketBilling).filter(
        ServiceTicketBilling.ticket_id == ticket_id
    ).first()
    
    if not billing:
        create_result = TicketService.create_billing(
            db=db, ticket_id=ticket_id, document_type='bill',
            is_gst_invoice=False, created_by_id=staff.id
        )
        if not create_result["success"]:
            raise HTTPException(status_code=400, detail=create_result["message"])
        billing = db.query(ServiceTicketBilling).filter(
            ServiceTicketBilling.ticket_id == ticket_id
        ).first()
    
    items_added = []
    
    spare_requests = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.ticket_id == ticket_id
    ).all()
    
    from app.models.ticket import ServiceTicketBillingItem
    db.query(ServiceTicketBillingItem).filter(
        ServiceTicketBillingItem.billing_id == billing.id,
        ServiceTicketBillingItem.item_type == 'spare'
    ).delete()
    db.commit()

    # Pre-fetch marketplace spare data for specification snapshot + pricing enrichment fallback
    from app.models.marketplace import MarketplaceCategoryConfig as _MktCatCfgAP
    from app.models.marketplace import MarketspareItem as _MktSpareItemAP
    from app.services.marketplace_pricing import enrich_product_with_pricing as _enrich_ap
    _spare_mkt_map = {}
    _spare_cat_cfg_map = {}
    _spare_mkt_ids = [s.marketplace_spare_id for s in spare_requests if s.marketplace_spare_id]
    if _spare_mkt_ids:
        _mkt_spares = db.query(_MktSpareItemAP).filter(_MktSpareItemAP.id.in_(_spare_mkt_ids)).all()
        _spare_mkt_map = {m.id: m for m in _mkt_spares}
        _cat_names_ap = list({m.category_name for m in _mkt_spares if m.category_name})
        if _cat_names_ap:
            _billing_company_id = billing.company_id or 1
            _cfgs_ap = db.query(_MktCatCfgAP).filter(
                _MktCatCfgAP.category_name.in_(_cat_names_ap),
                _MktCatCfgAP.company_id == _billing_company_id
            ).all()
            _spare_cat_cfg_map = {c.category_name: c.to_dict() for c in _cfgs_ap}

    for spare in spare_requests:
        if spare.procurement_status in ('cancelled',):
            continue
        qty = spare.quantity_required or 1
        gst_rate = spare.gst_rate or 18.0

        # ── Compute net_rate = taxable amount per unit (ex-GST) ──────────
        # Priority: DB-stored net_before_tax → actual_cost → payment_amount
        # → unit_price (already ex-tax — NO re-division) → total_with_gst
        # → live marketplace enrichment fallback → estimated_cost
        net_before_tax = getattr(spare, 'net_before_tax', None)
        if net_before_tax and net_before_tax > 0:
            # FIX-1: net_before_tax is already ex-tax per unit
            net_rate = float(net_before_tax)
            gst_rate = spare.gst_rate or gst_rate
        elif spare.actual_cost and spare.actual_cost > 0:
            net_rate = float(spare.actual_cost) / qty / (1 + gst_rate / 100)
        elif getattr(spare, 'payment_amount', None) and spare.payment_amount > 0:
            net_rate = float(spare.payment_amount) / qty / (1 + gst_rate / 100)
        elif spare.unit_price and spare.unit_price > 0:
            # FIX-2: unit_price stores net_before_tax (ex-tax) — do NOT divide by GST again
            net_rate = float(spare.unit_price)
            gst_rate = spare.gst_rate or gst_rate
        elif spare.total_with_gst and spare.total_with_gst > 0:
            net_rate = float(spare.total_with_gst) / qty / (1 + gst_rate / 100)
        else:
            # FIX-3: Live marketplace enrichment fallback for old/zero-priced spares
            net_rate = 0.0
            if spare.marketplace_spare_id and spare.marketplace_spare_id in _spare_mkt_map:
                _ms_ap = _spare_mkt_map[spare.marketplace_spare_id]
                _cfg_ap = _spare_cat_cfg_map.get(_ms_ap.category_name)
                _disc_mode = getattr(spare, 'discount_mode', None)
                _enriched_ap = _enrich_ap(_ms_ap.to_dict(), _cfg_ap, _disc_mode)
                net_rate = float(_enriched_ap.get('net_before_tax', 0))
                gst_rate = float(_enriched_ap.get('gst_percent', gst_rate))
                # Back-fill DB fields so future syncs are faster (write-through)
                if net_rate > 0:
                    spare.net_before_tax = net_rate
                    spare.unit_price     = net_rate
                    spare.gst_rate       = gst_rate
                    spare.gst_amount     = round(net_rate * qty * gst_rate / 100, 2)
                    spare.total_with_gst = round((net_rate + net_rate * gst_rate / 100) * qty, 2)
                    db.flush()
            if net_rate <= 0:
                net_rate = float(spare.estimated_cost or 0.0) / qty

        if net_rate <= 0:
            continue
        hsn = spare.hsn_code or None

        # Snapshot marketplace product details into billing item
        _spec_parts = []
        _warranty_info = None
        if spare.marketplace_spare_id and spare.marketplace_spare_id in _spare_mkt_map:
            _ms = _spare_mkt_map[spare.marketplace_spare_id]
            if _ms.brand:
                _spec_parts.append(f"Brand: {_ms.brand}")
            if _ms.specifications:
                _spec_parts.append(f"Spec: {_ms.specifications}")
            if _ms.model_compat:
                _spec_parts.append(f"Compatible: {_ms.model_compat}")
            if _ms.warranty_details:
                _warranty_info = str(_ms.warranty_details)
        elif spare.spare_description:
            _spec_parts.append(f"Spec: {spare.spare_description}")
        _specification = " | ".join(_spec_parts) if _spec_parts else None

        result = TicketService.add_billing_item(
            db=db,
            billing_id=billing.id,
            item_type='spare',
            description=spare.spare_item_name or 'Spare Part',
            quantity=qty,
            rate=net_rate,
            hsn_code=hsn,
            tax_rate=gst_rate,
            is_intrastate=True,
            spare_request_id=spare.id,
            specification=_specification,
            warranty_info=_warranty_info,
        )
        if result["success"]:
            items_added.append({"type": "spare", "name": spare.spare_item_name, "amount": net_rate * qty})
    
    if service_charge > 0:
        result = TicketService.add_billing_item(
            db=db, billing_id=billing.id, item_type='service',
            description='Service Charges', quantity=1, rate=service_charge,
            tax_rate=18.0, is_intrastate=True
        )
        if result["success"]:
            items_added.append({"type": "service", "name": "Service Charges", "amount": service_charge})
    
    if labour_charge > 0:
        result = TicketService.add_billing_item(
            db=db, billing_id=billing.id, item_type='labour',
            description='Labour Charges', quantity=1, rate=labour_charge,
            tax_rate=18.0, is_intrastate=True
        )
        if result["success"]:
            items_added.append({"type": "labour", "name": "Labour Charges", "amount": labour_charge})
    
    db.refresh(billing)
    
    return {
        "success": True,
        "billing_id": billing.id,
        "items_added": items_added,
        "total_items": len(items_added),
        "billing_total": billing.net_payable
    }


@router.post("/service/billing/{billing_id}/confirm")
async def confirm_billing_and_sync_sfms(
    billing_id: int,
    payment_mode: str = Body(default='cash'),
    payment_reference: Optional[str] = Body(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Confirm billing and sync to SFMS for accounting"""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketBilling
    from app.services.service_ticket_sfms_integration import create_billing_sfms_entries
    
    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")
    
    billing = db.query(ServiceTicketBilling).filter(
        ServiceTicketBilling.id == billing_id
    ).first()
    
    if not billing:
        raise HTTPException(status_code=404, detail="Billing not found")
    
    if billing.sfms_status == 'posted':
        raise HTTPException(status_code=400, detail="Billing already confirmed and synced to SFMS")
    
    billing.payment_mode = payment_mode
    billing.payment_reference = payment_reference
    billing.payment_status = 'paid'
    billing.amount_paid = billing.net_payable
    billing.amount_due = 0
    billing.posted_by_id = staff.id
    billing.sfms_status = 'pending_sfms'
    
    db.commit()
    db.refresh(billing)
    
    sfms_result = create_billing_sfms_entries(
        db=db,
        billing=billing,
        confirmed_by_id=staff.id
    )
    
    if not sfms_result["success"]:
        billing.sfms_status = 'draft'
        billing.sfms_error = sfms_result.get("error", "Unknown error")
        billing.payment_status = 'pending'
        billing.amount_paid = 0
        billing.amount_due = billing.net_payable
        billing.posted_by_id = None
        db.commit()
        raise HTTPException(status_code=500, detail=f"SFMS sync failed: {sfms_result.get('error')}")
    
    return {
        "success": True,
        "message": "Billing confirmed and synced to SFMS",
        "billing_id": billing_id,
        "payment_mode": payment_mode,
        "sfms_entries": sfms_result.get("entries", []),
        "total_revenue": sfms_result.get("grand_total", 0)
    }


@router.get("/service/billing/{billing_id}/pdf")
async def generate_billing_pdf(
    billing_id: int,
    mode: Optional[str] = Query(None, regex='^(estimate|tax_invoice)$'),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Generate PDF for service billing — Tax Invoice or Estimate copy.
    mode=tax_invoice → full GST invoice with CGST/SGST breakdown (requires confirmed status)
    mode=estimate    → estimate copy without GST details (allowed on draft too)
    If mode omitted, defaults to billing's own is_gst_invoice flag.
    """
    from fastapi.responses import StreamingResponse
    from app.models.ticket import ServiceTicketBilling, ServiceTicketBillingItem, ServiceTicket, ServiceTicketSpareRequest
    from app.services.invoice_pdf_generator import generate_invoice_pdf
    import io

    billing = db.query(ServiceTicketBilling).filter(
        ServiceTicketBilling.id == billing_id
    ).first()

    if not billing:
        raise HTTPException(status_code=404, detail="Billing not found")

    # Resolve mode: use explicit param, fall back to billing's own type
    if not mode:
        mode = 'tax_invoice' if billing.is_gst_invoice else 'estimate'

    # DC Protocol Mar 2026: Allow Tax Invoice PDFs for any billing status.
    # Staff need to preview/print before confirming; removing the confirmed-only restriction.

    items = db.query(ServiceTicketBillingItem).filter(
        ServiceTicketBillingItem.billing_id == billing_id
    ).all()

    ticket = db.query(ServiceTicket).filter(
        ServiceTicket.id == billing.ticket_id
    ).first()

    # DC Protocol Mar 2026: Enrich billing items with live marketplace spec/warranty data.
    # Billing items may have been created before the spec-snapshot feature existed, so
    # we always fall back to live marketplace data when stored fields are empty.
    try:
        from app.models.marketplace import MarketspareItem as _MktSpareItem
        _mkt_lookup: dict = {}   # spare_request_id → MarketspareItem
        _spare_req_map: dict = {}  # spare_request_id → ServiceTicketSpareRequest
        # Fetch ALL spare requests for this billing (need item_code/spec/warranty for all)
        _all_spare_ids = [i.spare_request_id for i in items if i.spare_request_id]
        if _all_spare_ids:
            _spare_reqs = db.query(ServiceTicketSpareRequest).filter(
                ServiceTicketSpareRequest.id.in_(_all_spare_ids)
            ).all()
            _spare_req_map = {sr.id: sr for sr in _spare_reqs}
            _mkt_ids = [s.marketplace_spare_id for s in _spare_reqs if s.marketplace_spare_id]
            if _mkt_ids:
                _mkt_items = db.query(_MktSpareItem).filter(_MktSpareItem.id.in_(_mkt_ids)).all()
                _mkt_by_id = {m.id: m for m in _mkt_items}
                for _sr in _spare_reqs:
                    if _sr.marketplace_spare_id and _sr.marketplace_spare_id in _mkt_by_id:
                        _mkt_lookup[_sr.id] = _mkt_by_id[_sr.marketplace_spare_id]

        class _EnrichedItem:
            """Thin wrapper that overlays live marketplace spec/warranty/SKU on a billing item."""
            __slots__ = ('_item', 'specification', 'warranty_info', 'serial_numbers', 'item_code',
                         'description', 'quantity', 'rate', 'taxable_amount', 'tax_rate',
                         'cgst_amount', 'sgst_amount', 'line_total', 'hsn_code')
            def __init__(self, item, spare_req, mkt):
                self._item = item
                # Item code/SKU: from spare request, or marketplace sku
                self.item_code = (
                    (spare_req.spare_item_code if spare_req else None)
                    or (mkt.sku if mkt else None)
                    or ''
                )
                # Specification: stored value wins; fall back to live marketplace fields
                if item.specification:
                    self.specification = item.specification
                elif mkt:
                    _parts = []
                    if mkt.brand:          _parts.append(f"Brand: {mkt.brand}")
                    if mkt.specifications: _parts.append(f"Spec: {mkt.specifications}")
                    if mkt.model_compat:   _parts.append(f"Compatible: {mkt.model_compat}")
                    self.specification = " | ".join(_parts) if _parts else None
                elif spare_req and getattr(spare_req, 'spare_description', None):
                    self.specification = f"Spec: {spare_req.spare_description}"
                else:
                    self.specification = None
                # Warranty: stored value wins; fall back to live marketplace field
                self.warranty_info    = item.warranty_info or (str(mkt.warranty_details) if mkt and mkt.warranty_details else None)
                self.serial_numbers   = item.serial_numbers or []
                # Pass-through all other fields
                self.description      = item.description
                self.quantity         = item.quantity
                self.rate             = item.rate
                self.taxable_amount   = item.taxable_amount
                self.tax_rate         = item.tax_rate
                self.cgst_amount      = item.cgst_amount
                self.sgst_amount      = item.sgst_amount
                self.line_total       = item.line_total
                self.hsn_code         = item.hsn_code

        enriched_items = [
            _EnrichedItem(
                i,
                _spare_req_map.get(i.spare_request_id) if i.spare_request_id else None,
                _mkt_lookup.get(i.spare_request_id) if i.spare_request_id else None
            )
            for i in items
        ]
    except Exception as _enrich_err:
        logger.warning(f"[DC-PDF-ENRICH] marketplace enrichment skipped: {_enrich_err}")
        enriched_items = items

    try:
        pdf_bytes = generate_invoice_pdf(billing, enriched_items, ticket, mode=mode)
        ref = billing.invoice_number or billing.bill_reference or str(billing_id)
        filename = f"{'Invoice' if mode == 'tax_invoice' else 'Estimate'}_{ref}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error generating PDF for billing {billing_id} mode={mode}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


@router.get("/service/reports/revenue-by-partner")
async def get_revenue_by_service_center(
    partner_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """Get service center wise revenue report (Staff view - all partners)"""
    from app.services.service_ticket_sfms_integration import get_service_center_revenue
    from datetime import datetime as dt
    
    from_date = None
    to_date = None
    
    if date_from:
        try:
            from_date = dt.strptime(date_from, '%Y-%m-%d').date()
        except: pass
    
    if date_to:
        try:
            to_date = dt.strptime(date_to, '%Y-%m-%d').date()
        except: pass
    
    results = get_service_center_revenue(
        db=db,
        partner_id=partner_id,
        date_from=from_date,
        date_to=to_date
    )
    
    total_spares = sum(r['spares_revenue'] for r in results)
    total_service = sum(r['service_revenue'] for r in results)
    total_labour = sum(r['labour_revenue'] for r in results)
    grand_total = sum(r['total_revenue'] for r in results)
    
    total_estimate_count = sum(r.get('estimated_bills', {}).get('count', 0) for r in results)
    total_estimate_revenue = sum(r.get('estimated_bills', {}).get('revenue', 0) for r in results)
    total_invoice_count = sum(r.get('tax_invoices', {}).get('count', 0) for r in results)
    total_invoice_revenue = sum(r.get('tax_invoices', {}).get('revenue', 0) for r in results)
    total_cgst = sum(r.get('tax_invoices', {}).get('cgst_collected', 0) for r in results)
    total_sgst = sum(r.get('tax_invoices', {}).get('sgst_collected', 0) for r in results)
    
    return {
        "partners": results,
        "summary": {
            "total_partners": len(results),
            "total_spares_revenue": total_spares,
            "total_service_revenue": total_service,
            "total_labour_revenue": total_labour,
            "grand_total_revenue": grand_total,
            "estimated_bills": {
                "count": total_estimate_count,
                "revenue": total_estimate_revenue
            },
            "tax_invoices": {
                "count": total_invoice_count,
                "revenue": total_invoice_revenue,
                "cgst_collected": total_cgst,
                "sgst_collected": total_sgst,
                "gst_collected": total_cgst + total_sgst
            }
        },
        "filters": {
            "partner_id": partner_id,
            "date_from": date_from,
            "date_to": date_to
        }
    }


@router.get("/service/reports/my-revenue")
async def get_partner_own_revenue(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_partner_dependency)
):
    """
    Get partner's own revenue (Partner view - restricted to their center only).
    Uses partner authentication via Depends() to automatically scope to their service center.
    JWT validation is enforced by get_current_partner dependency.
    """
    from app.services.service_ticket_sfms_integration import get_service_center_revenue
    from app.models.ticket import ServiceTicketBilling, ServiceTicket
    from datetime import datetime as dt
    from sqlalchemy import func
    
    from_date = None
    to_date = None
    
    if date_from:
        try:
            from_date = dt.strptime(date_from, '%Y-%m-%d').date()
        except: pass
    
    if date_to:
        try:
            to_date = dt.strptime(date_to, '%Y-%m-%d').date()
        except: pass
    
    results = get_service_center_revenue(
        db=db,
        partner_id=partner.id,
        date_from=from_date,
        date_to=to_date
    )
    
    my_revenue = results[0] if results else {
        "partner_id": partner.id,
        "partner_code": partner.partner_code,
        "partner_name": partner.partner_name,
        "category": partner.category,
        "total_billings": 0,
        "spares_revenue": 0,
        "service_revenue": 0,
        "labour_revenue": 0,
        "total_revenue": 0
    }
    
    ticket_query = db.query(
        func.count(ServiceTicket.id).label('ticket_count'),
        func.count(ServiceTicket.id).filter(ServiceTicket.status == 'Closed').label('closed_count')
    ).filter(ServiceTicket.partner_id == partner.id)
    
    if from_date:
        ticket_query = ticket_query.filter(ServiceTicket.created_date >= from_date)
    if to_date:
        ticket_query = ticket_query.filter(ServiceTicket.created_date <= to_date)
    
    ticket_stats = ticket_query.first()
    
    monthly_trend = []
    if not from_date:
        from_date = dt.now().replace(day=1, month=1).date()
    if not to_date:
        to_date = dt.now().date()
    
    monthly_query = db.query(
        func.date_trunc('month', ServiceTicketBilling.created_at).label('month'),
        func.coalesce(func.sum(ServiceTicketBilling.net_payable), 0).label('revenue')
    ).filter(
        ServiceTicketBilling.service_center_id == partner.id,
        ServiceTicketBilling.status == 'confirmed'
    ).group_by(
        func.date_trunc('month', ServiceTicketBilling.created_at)
    ).order_by('month')
    
    if from_date:
        monthly_query = monthly_query.filter(ServiceTicketBilling.created_at >= from_date)
    if to_date:
        monthly_query = monthly_query.filter(ServiceTicketBilling.created_at <= to_date)
    
    for row in monthly_query.all():
        monthly_trend.append({
            "month": row.month.strftime('%Y-%m') if row.month else None,
            "revenue": float(row.revenue or 0)
        })
    
    return {
        "partner": {
            "id": partner.id,
            "code": partner.partner_code,
            "name": partner.partner_name,
            "category": partner.category
        },
        "revenue": my_revenue,
        "ticket_stats": {
            "total_tickets": ticket_stats.ticket_count if ticket_stats else 0,
            "closed_tickets": ticket_stats.closed_count if ticket_stats else 0
        },
        "monthly_trend": monthly_trend,
        "filters": {
            "date_from": date_from,
            "date_to": date_to
        }
    }


# ===== DC PROTOCOL JAN 2026: PUBLIC SERVICE TICKET ENDPOINT =====
# No authentication required - allows anyone to raise a service ticket

from collections import defaultdict
import time

_public_ticket_rate_limit: dict = defaultdict(list)

def _check_rate_limit(ip: str, max_requests: int = 5, window_seconds: int = 3600) -> bool:
    """Check if IP has exceeded rate limit (5 tickets per hour per IP)"""
    now = time.time()
    _public_ticket_rate_limit[ip] = [t for t in _public_ticket_rate_limit[ip] if now - t < window_seconds]
    if len(_public_ticket_rate_limit[ip]) >= max_requests:
        return False
    _public_ticket_rate_limit[ip].append(now)
    return True


@router.post("/service/public/create")
async def create_public_service_ticket(
    request: Request,
    customer_name: str = Body(...),
    customer_phone: str = Body(...),
    customer_email: Optional[str] = Body(default=None),
    customer_address: Optional[str] = Body(default=None),
    issue_category: Optional[str] = Body(default=''),
    issue_description: str = Body(...),
    ticket_type: Optional[str] = Body(default='technical'),
    product_name: Optional[str] = Body(default=None),
    product_serial: Optional[str] = Body(default=None),
    product_model: Optional[str] = Body(default=None),
    warranty_status: Optional[str] = Body(default=None),
    warranty_invoice_number: Optional[str] = Body(default=None),
    warranty_sale_date: Optional[str] = Body(default=None),
    warranty_motor_number: Optional[str] = Body(default=None),
    warranty_chassis_number: Optional[str] = Body(default=None),
    warranty_model: Optional[str] = Body(default=None),
    warranty_notes: Optional[str] = Body(default=None),
    requested_parts: Optional[List[dict]] = Body(default=None),
    db: Session = Depends(get_db)
):
    """
    PUBLIC endpoint for service ticket creation - NO AUTHENTICATION REQUIRED

    DC Protocol Jan 2026:
    - Allows anyone to raise a service ticket from the website
    - Rate limited: 5 tickets per IP per hour
    - Auto-sets source_channel='website', user_id='PUBLIC_GUEST'
    - Captures IP and user agent for audit trail
    - ticket_type: 'technical' (default) or 'spares'
    - requested_parts: optional list of spare items for spares tickets
    - issue_category: optional (not required)
    """
    from app.models.ticket import ServiceTicketSpareRequest
    ip_address = request.client.host if request and request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")[:200] if request else None

    if not _check_rate_limit(ip_address):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later (max 5 tickets per hour)."
        )

    if len(customer_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Customer name must be at least 2 characters")
    if len(customer_phone.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please enter a valid phone number")
    if len(issue_description.strip()) < 10:
        raise HTTPException(status_code=400, detail="Issue description must be at least 10 characters")

    safe_issue_category = (issue_category or '').strip() or 'General'
    safe_ticket_type = ticket_type.strip() if ticket_type in ('technical', 'spares', 'general') else 'technical'
    spares_required = safe_ticket_type == 'spares' and bool(requested_parts)

    try:
        ticket = TicketService.create_service_ticket(
            db=db,
            user_id="PUBLIC_GUEST",
            issue_category=safe_issue_category,
            issue_description=issue_description.strip(),
            priority='Medium',
            ticket_type=safe_ticket_type,
            source_channel='website',
            partner_id=None,
            customer_name=customer_name.strip(),
            customer_phone=customer_phone.strip(),
            customer_email=customer_email.strip() if customer_email else None,
            customer_address=customer_address.strip() if customer_address else None,
            product_name=product_name.strip() if product_name else None,
            product_serial=product_serial.strip() if product_serial else None,
            product_model=product_model.strip() if product_model else None,
            warranty_status='under_warranty' if warranty_status == 'under_warranty' else None,
            warranty_invoice_number=warranty_invoice_number.strip() if warranty_invoice_number else None,
            warranty_sale_date=warranty_sale_date if warranty_sale_date else None,
            warranty_motor_number=warranty_motor_number.strip() if warranty_motor_number else None,
            warranty_chassis_number=warranty_chassis_number.strip() if warranty_chassis_number else None,
            warranty_model=warranty_model.strip() if warranty_model else None,
            warranty_notes=warranty_notes.strip() if warranty_notes else None,
            spares_required=spares_required,
            ip_address=ip_address,
            user_agent=user_agent,
            staff_id=None
        )

        spare_count = 0
        if requested_parts:
            for part in requested_parts:
                name = (part.get('name') or '').strip()
                if not name:
                    continue
                qty = max(1, int(part.get('quantity') or 1))
                spare_req = ServiceTicketSpareRequest(
                    ticket_id=ticket.id,
                    spare_item_name=name,
                    spare_item_code=part.get('code') or None,
                    quantity_required=qty,
                    unit_price=float(part.get('unit_price') or 0) or None,
                    gst_rate=float(part.get('gst_rate') or 18),
                    gst_amount=float(part.get('gst_amount') or 0) or None,
                    total_with_gst=float(part.get('total_with_gst') or 0) or None,
                    hsn_code=part.get('hsn_code') or None,
                    marketplace_spare_id=int(part['marketplace_spare_id']) if part.get('marketplace_spare_id') else None,
                    discount_mode=part.get('discount_mode') or None,
                    discount_id=part.get('discount_id') or None,
                    catalog_price=float(part.get('catalog_price') or 0) or None,
                    discount_pct=float(part.get('discount_pct') or 0) or None,
                    discount_amount=float(part.get('discount_amount') or 0) or None,
                    net_before_tax=float(part.get('net_before_tax') or 0) or None,
                    procurement_status='pending',
                    is_custom=not bool(part.get('marketplace_spare_id')),
                )
                db.add(spare_req)
                spare_count += 1
            if spare_count:
                db.commit()

        return {
            "success": True,
            "ticket_id": ticket.ticket_id,
            "spare_requests_created": spare_count,
            "message": f"Your service request has been registered successfully. Ticket ID: {ticket.ticket_id}"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to create service ticket. Please try again later."
        )


# ── GET /service/public/status/{ticket_id} — Public ticket status (phone soft-auth) ──
@router.get("/service/public/status/{ticket_id_str}")
def get_public_ticket_status(
    ticket_id_str: str,
    phone: str = Query(..., description="Last 4+ digits of the phone number used to submit the ticket"),
    db: Session = Depends(get_db)
):
    """
    Public ticket status — no JWT required.
    Soft auth: caller must supply the last 4+ digits of the phone number on the ticket.
    Returns ticket details + spare parts list for customer tracking.
    DC Protocol: Read-only. No PII beyond what customer already knows.
    """
    from app.models.ticket import ServiceTicket, ServiceTicketSpareRequest
    ticket = db.query(ServiceTicket).filter(ServiceTicket.ticket_id == ticket_id_str.strip()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found. Please check your Ticket ID.")

    stored_phone = (ticket.customer_phone or '').strip().replace(' ', '').replace('-', '')
    provided = phone.strip().replace(' ', '').replace('-', '')
    if len(provided) < 4:
        raise HTTPException(status_code=400, detail="Please provide at least the last 4 digits of your phone number.")
    if not stored_phone.endswith(provided[-max(4, len(provided)):]):
        raise HTTPException(status_code=403, detail="Phone number does not match our records for this ticket.")

    spares = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.ticket_id == ticket.id
    ).order_by(ServiceTicketSpareRequest.id).all()

    # DC Protocol Mar 2026: Comprehensive status + sub_status labels
    status_labels = {
        'open': 'Open — Awaiting Assignment',
        'Open': 'Open — Awaiting Assignment',
        'in_progress': 'In Progress',
        'In Progress': 'In Progress',
        'pending_parts': 'Awaiting Parts',
        'resolved': 'Resolved',
        'Resolved': 'Resolved',
        'closed': 'Closed',
        'Closed': 'Closed',
        'cancelled': 'Cancelled',
        'Cancelled': 'Cancelled',
    }
    sub_status_labels = {
        'new': 'Received — Awaiting Acknowledgment',
        'acknowledged': 'Acknowledged — Assigned to Service Team',
        'diagnosing': 'Under Diagnosis',
        'awaiting_spares': 'Awaiting Spare Parts',
        'procurement_in_progress': 'Spare Parts Being Procured',
        'ready_for_work': 'Ready for Service Work',
        'work_complete': 'Work Completed',
        'closed': 'Closed',
    }

    # Determine last activity timestamp (ServiceTicket uses created_date not created_at)
    last_activity = (
        ticket.last_response_date or ticket.in_progress_date or
        ticket.resolved_date or ticket.closed_date or ticket.created_date
    )

    # Safe technician name load
    technician_name = None
    try:
        if ticket.service_technician_id and ticket.service_technician:
            technician_name = ticket.service_technician.full_name
    except Exception:
        pass

    spare_status_labels = {
        'pending': 'Requested',
        'acknowledged': 'Acknowledged by Store',
        'ordered': 'Ordered / Procurement Raised',
        'received': 'Received — Ready to Use',
        'released': 'Released to Technician',
        'cancelled': 'Cancelled',
    }

    return {
        "ticket_id": ticket.ticket_id,
        "status": ticket.status,
        "status_label": status_labels.get(ticket.status or 'Open', ticket.status or 'Open'),
        "sub_status": ticket.sub_status,
        "sub_status_label": sub_status_labels.get(ticket.sub_status or 'new', ticket.sub_status or 'Received'),
        "ticket_type": ticket.ticket_type,
        "issue_category": ticket.issue_category,
        "issue_description": ticket.issue_description,
        "customer_name": ticket.customer_name,
        "product_name": ticket.product_name,
        "product_model": ticket.product_model,
        "assigned_to_name": technician_name,
        "created_at": ticket.created_date.isoformat() if ticket.created_date else None,
        "updated_at": last_activity.isoformat() if last_activity else None,
        "spare_parts": [
            {
                "name": s.spare_item_name,
                "code": s.spare_item_code,
                "quantity": s.quantity_required,
                "unit_price": float(s.unit_price) if s.unit_price else None,
                "gst_rate": float(s.gst_rate) if s.gst_rate else 18,
                "procurement_status": s.procurement_status or 'pending',
                "procurement_status_label": spare_status_labels.get(s.procurement_status or 'pending', s.procurement_status or 'Pending'),
                "is_custom": s.is_custom,
            } for s in spares
        ]
    }


# ===== DC PROTOCOL JAN 2026: PARTNER SERVICE TICKET ENDPOINTS =====
# Limited access for partners: create tickets, view own tickets, view charges

@router.get("/service/{ticket_id}/spare-requests")
async def get_ticket_spare_requests(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get all spare requests for a specific ticket (staff view).
    DC Protocol Mar 2026: Provides staff visibility into customer-requested spares
    and any ZYPO/ZYPR records linked to those requests.
    """
    from app.models.ticket import ServiceTicketSpareRequest
    from app.models.marketplace import MarketplacePurchaseOrder, MarketplaceProcurementRequest

    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    spares = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.ticket_id == ticket_id
    ).order_by(ServiceTicketSpareRequest.id).all()

    spare_status_map = {
        'pending':            'Pending — Not yet processed',
        'acknowledged':       'Acknowledged by Store',
        'payment_received':   'Payment Received',
        'waiting_for_spares': 'Waiting for Spares',
        'dispatched':         'Dispatched to Technician',
        'ordered':            'Ordered / PO Raised',
        'received':           'Received in Store',
        'released':           'Released to Technician',
        'cancelled':          'Cancelled',
    }

    # DC Protocol Mar 2026: Preload marketplace items for pricing enrichment (single source of truth)
    from app.models.marketplace import MarketspareItem as _MktSpare, MarketplaceCategoryConfig as _MktCatCfg
    from app.services.marketplace_pricing import enrich_product_with_pricing as _enrich_pricing
    mkt_ids = [s.marketplace_spare_id for s in spares if getattr(s, 'marketplace_spare_id', None)]
    mkt_items_map = {}
    mkt_cat_cfg_map = {}
    if mkt_ids:
        _mkt_items = db.query(_MktSpare).filter(_MktSpare.id.in_(mkt_ids)).all()
        for mi in _mkt_items:
            mkt_items_map[mi.id] = mi
        cat_names = list({mi.category_name for mi in _mkt_items if mi.category_name})
        if cat_names:
            _cfgs = db.query(_MktCatCfg).filter(
                _MktCatCfg.category_name.in_(cat_names),
                _MktCatCfg.company_id == 1
            ).all()
            for cfg in _cfgs:
                mkt_cat_cfg_map[cfg.category_name] = cfg.to_dict()

    # DC Protocol: ticket-level discount — propagate to any spare missing one
    ticket_disc_mode2 = next((getattr(s, 'discount_mode', None) for s in spares if getattr(s, 'discount_mode', None)), None)

    result = []
    for s in spares:
        qty = int(getattr(s, 'quantity_required', 1) or 1)

        # Marketplace pricing enrichment — single source of truth
        mkt_pricing = {}
        mkt_spare_id = getattr(s, 'marketplace_spare_id', None)
        if mkt_spare_id and mkt_spare_id in mkt_items_map:
            mi = mkt_items_map[mkt_spare_id]
            cat_cfg = mkt_cat_cfg_map.get(mi.category_name)
            eff_disc2 = getattr(s, 'discount_mode', None) or ticket_disc_mode2
            enriched = _enrich_pricing(mi.to_dict(), cat_cfg, eff_disc2)
            mkt_pricing = {
                "display_mrp":          enriched.get("display_mrp"),
                "mrp_discount_amount":  enriched.get("mrp_discount_amount"),
                "mrp_discount_pct":     enriched.get("mrp_discount_pct"),
                "net_before_tax_unit":  enriched.get("net_before_tax"),
                "gst_percent_mkt":      enriched.get("gst_percent"),
                "gst_amount_unit":      enriched.get("gst_amount"),
                "final_price_unit":     enriched.get("final_price"),
                "markup_percent":       enriched.get("markup_percent"),
                "discount_amount_unit": enriched.get("discount_amount"),
                "dealer_price":         enriched.get("dealer_price"),
                "mkt_specs":            mi.specifications or '',
                "mkt_color":            mi.color or '',
                "mkt_sku":              mi.sku or '',
            }

        item = {
            "id": s.id,
            "name": s.spare_item_name,
            "code": s.spare_item_code or '',
            "quantity": qty,
            "unit_price": float(s.unit_price) if s.unit_price else None,
            "gst_rate": float(s.gst_rate) if s.gst_rate else 18,
            "gst_amount": float(s.gst_amount) if s.gst_amount else None,
            "total_with_gst": float(s.total_with_gst) if s.total_with_gst else None,
            "hsn_code": s.hsn_code,
            "procurement_status": s.procurement_status or 'pending',
            "procurement_status_label": spare_status_map.get(s.procurement_status or 'pending', s.procurement_status or 'Pending'),
            "is_custom": s.is_custom or False,
            "discount_mode": getattr(s, 'discount_mode', None) or ticket_disc_mode2,
            "catalog_price": float(s.catalog_price) if getattr(s, 'catalog_price', None) else None,
            "discount_pct": float(s.discount_pct) if getattr(s, 'discount_pct', None) else None,
            "discount_amount": float(s.discount_amount) if getattr(s, 'discount_amount', None) else None,
            "net_before_tax": float(s.net_before_tax) if getattr(s, 'net_before_tax', None) else None,
            "marketplace_spare_id": mkt_spare_id,
            "marketplace_po_id": getattr(s, 'marketplace_po_id', None),
            "marketplace_procurement_id": getattr(s, 'marketplace_procurement_id', None),
            "marketplace_po_number": None,
            "marketplace_procurement_number": None,
            "marketplace_po_status": None,
            # DC Protocol Mar 2026: Payment fields
            "payment_amount": getattr(s, 'payment_amount', None),
            "payment_mode": getattr(s, 'payment_mode', None),
            "payment_reference": getattr(s, 'payment_reference', None),
            "payment_date": s.payment_date.isoformat() if getattr(s, 'payment_date', None) else None,
            "payment_notes": getattr(s, 'payment_notes', None),
            "income_entry_id": getattr(s, 'income_entry_id', None),
            "dispatched_at": s.dispatched_at.isoformat() if getattr(s, 'dispatched_at', None) else None,
            "dispatched_by_id": getattr(s, 'dispatched_by_id', None),
            # DC Protocol Mar 2026: Warranty fields
            "is_warranty": getattr(s, 'is_warranty', False) or False,
            "warranty_invoice_number": getattr(s, 'warranty_invoice_number', None),
            "warranty_sale_date": str(s.warranty_sale_date) if getattr(s, 'warranty_sale_date', None) else None,
            "warranty_motor_number": getattr(s, 'warranty_motor_number', None),
            "warranty_chassis_number": getattr(s, 'warranty_chassis_number', None),
            "warranty_model": getattr(s, 'warranty_model', None),
            "warranty_notes": getattr(s, 'warranty_notes', None),
            # For cancelled reason display
            "acknowledgment_notes": getattr(s, 'acknowledgment_notes', None),
            # DC-CUSTOMER-SPARE-001: source + repair routing (essential for frontend split)
            "spare_source": getattr(s, 'spare_source', None) or 'company',
            "repair_route": getattr(s, 'repair_route', None),
            "sub_ticket_number": getattr(s, 'sub_ticket_number', None),
            "spare_item_name": s.spare_item_name,
            "spare_description": getattr(s, 'spare_description', None),
            "quantity_required": qty,
            # Marketplace enriched pricing (single source of truth)
            **mkt_pricing,
        }
        if item["marketplace_po_id"]:
            po = db.query(MarketplacePurchaseOrder).filter(MarketplacePurchaseOrder.id == item["marketplace_po_id"]).first()
            if po:
                item["marketplace_po_number"] = getattr(po, 'po_number', None) or getattr(po, 'order_number', None)
                item["marketplace_po_status"] = getattr(po, 'status', None)
        if item["marketplace_procurement_id"]:
            pr = db.query(MarketplaceProcurementRequest).filter(MarketplaceProcurementRequest.id == item["marketplace_procurement_id"]).first()
            if pr:
                item["marketplace_procurement_number"] = getattr(pr, 'procurement_number', None) or getattr(pr, 'request_number', None)
        result.append(item)

    return {"ticket_id": ticket_id, "spare_requests": result, "count": len(result)}


@router.post("/service/partner/create")
async def create_partner_service_ticket(
    customer_name: str = Body(...),
    customer_phone: str = Body(...),
    customer_email: Optional[str] = Body(default=None),
    customer_address: Optional[str] = Body(default=None),
    issue_category: str = Body(...),
    issue_description: str = Body(...),
    ticket_type: str = Body(default='technical'),
    priority: str = Body(default='Medium'),
    product_name: Optional[str] = Body(default=None),
    product_serial: Optional[str] = Body(default=None),
    product_model: Optional[str] = Body(default=None),
    warranty_status: Optional[str] = Body(default=None),
    request: Request = None,
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_partner_dependency)
):
    """
    Create service ticket from Partner Portal.
    DC Protocol Jan 2026: Partner-scoped ticket creation for walk-in customers.
    
    - ticket_type: 'technical' or 'spares'
    - priority: 'Low', 'Medium', 'High', 'Critical'
    - warranty_status: 'under_warranty', 'out_of_warranty', 'amc'
    """
    ip_address = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent", "")[:200] if request else None
    
    if ticket_type not in ['technical', 'spares', 'general']:
        raise HTTPException(status_code=400, detail="ticket_type must be 'technical', 'spares', or 'general'")
    
    if priority not in ['Low', 'Medium', 'High', 'Critical']:
        raise HTTPException(status_code=400, detail="priority must be 'Low', 'Medium', 'High', or 'Critical'")
    
    if len(customer_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Customer name must be at least 2 characters")
    if len(customer_phone.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please enter a valid phone number")
    
    try:
        ticket = TicketService.create_service_ticket(
            db=db,
            user_id=f"PARTNER_{partner.id}",
            issue_category=issue_category.strip(),
            issue_description=issue_description.strip(),
            priority=priority,
            ticket_type=ticket_type,
            source_channel='partner_portal',
            partner_id=partner.id,
            customer_name=customer_name.strip(),
            customer_phone=customer_phone.strip(),
            customer_email=customer_email.strip() if customer_email else None,
            customer_address=customer_address.strip() if customer_address else None,
            product_name=product_name.strip() if product_name else None,
            product_serial=product_serial.strip() if product_serial else None,
            product_model=product_model.strip() if product_model else None,
            warranty_status=warranty_status,
            spares_required=(ticket_type == 'spares'),
            ip_address=ip_address,
            user_agent=user_agent,
            staff_id=None
        )
        
        return {
            "success": True,
            "ticket_id": ticket.ticket_id,
            "ticket_db_id": ticket.id,
            "message": f"Service ticket created successfully. Ticket ID: {ticket.ticket_id}",
            "ticket_type": ticket_type,
            "priority": priority
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create service ticket: {str(e)}")


@router.get("/service/partner/my-tickets")
async def get_partner_tickets(
    status: Optional[str] = Query(None),
    ticket_type: Optional[str] = Query(None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_partner_dependency)
):
    """
    Get partner's own service tickets with pagination.
    DC Protocol: Partner-scoped - only shows tickets belonging to this partner.
    """
    from sqlalchemy import func
    
    query = db.query(ServiceTicket).filter(ServiceTicket.partner_id == partner.id)
    
    if status:
        query = query.filter(ServiceTicket.status == status)
    
    if ticket_type:
        query = query.filter(ServiceTicket.ticket_type == ticket_type)
    
    total = query.count()
    
    tickets = query.order_by(ServiceTicket.created_date.desc()).offset((page - 1) * limit).limit(limit).all()
    
    status_counts = db.query(
        ServiceTicket.status,
        func.count(ServiceTicket.id)
    ).filter(
        ServiceTicket.partner_id == partner.id
    ).group_by(ServiceTicket.status).all()
    
    return {
        "success": True,
        "tickets": [ticket.to_dict() for ticket in tickets],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "status_counts": {s: c for s, c in status_counts}
    }


@router.get("/service/partner/ticket/{ticket_id}")
async def get_partner_ticket_detail(
    ticket_id: int,
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_partner_dependency)
):
    """
    Get single ticket detail for partner.
    DC Protocol: Partner can only view their own tickets.
    """
    from app.models.ticket import TicketAttachment, ServiceTicketSpareRequest, TicketLog
    
    ticket = db.query(ServiceTicket).filter(
        ServiceTicket.id == ticket_id,
        ServiceTicket.partner_id == partner.id
    ).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    attachments = db.query(TicketAttachment).filter(
        TicketAttachment.ticket_id == ticket_id
    ).all()
    
    spares = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.ticket_id == ticket_id
    ).all()
    
    timeline = db.query(TicketLog).filter(
        TicketLog.ticket_id == ticket_id
    ).order_by(TicketLog.performed_at.desc()).limit(20).all()
    
    return {
        "success": True,
        "ticket": ticket.to_dict(),
        "media": [att.to_dict() for att in attachments if att.media_type in ['image', 'video']],
        "spares": [spare.to_dict() for spare in spares],
        "timeline": [{
            'id': log.id,
            'action': log.action_type,
            'description': log.action_description,
            'date': log.performed_at.isoformat() if log.performed_at else None
        } for log in timeline]
    }


@router.get("/service/partner/charges")
async def get_partner_service_charges(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_partner_dependency)
):
    """
    Get service charges/billing for partner's tickets.
    DC Protocol: Partner-scoped billing view.
    """
    from app.models.ticket import ServiceTicketBilling
    from datetime import datetime as dt
    from sqlalchemy import func
    
    query = db.query(ServiceTicketBilling).filter(
        ServiceTicketBilling.service_center_id == partner.id
    )
    
    if date_from:
        try:
            from_date = dt.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ServiceTicketBilling.created_at >= from_date)
        except: pass
    
    if date_to:
        try:
            to_date = dt.strptime(date_to, '%Y-%m-%d')
            query = query.filter(ServiceTicketBilling.created_at <= to_date)
        except: pass
    
    if status:
        query = query.filter(ServiceTicketBilling.status == status)
    
    billings = query.order_by(ServiceTicketBilling.created_at.desc()).limit(100).all()
    
    totals = db.query(
        func.count(ServiceTicketBilling.id).label('count'),
        func.coalesce(func.sum(ServiceTicketBilling.spares_amount), 0).label('spares'),
        func.coalesce(func.sum(ServiceTicketBilling.labour_amount), 0).label('labour'),
        func.coalesce(func.sum(ServiceTicketBilling.net_payable), 0).label('total')
    ).filter(
        ServiceTicketBilling.service_center_id == partner.id,
        ServiceTicketBilling.status == 'confirmed'
    ).first()
    
    return {
        "success": True,
        "billings": [b.to_dict() if hasattr(b, 'to_dict') else {
            'id': b.id,
            'ticket_id': b.ticket_id,
            'status': b.status,
            'spares_amount': float(b.spares_amount or 0),
            'labour_amount': float(b.labour_amount or 0),
            'service_charges': float(b.service_charges or 0),
            'net_payable': float(b.net_payable or 0),
            'created_at': b.created_at.isoformat() if b.created_at else None
        } for b in billings],
        "summary": {
            "total_billings": totals.count if totals else 0,
            "total_spares": float(totals.spares) if totals else 0,
            "total_labour": float(totals.labour) if totals else 0,
            "total_amount": float(totals.total) if totals else 0
        }
    }


@router.post("/service/partner/ticket/{ticket_id}/upload-media")
async def partner_upload_ticket_media(
    ticket_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    partner: OfficialPartner = Depends(get_current_partner_dependency)
):
    """
    Upload media to partner's own ticket.
    DC Protocol: Partners can upload media to tickets they created.
    Same limits as staff: 10 images OR 1 video (3 min).
    """
    from app.models.ticket import TicketAttachment, TicketLog
    from app.services.universal_upload_service import UniversalUploadService
    
    ticket = db.query(ServiceTicket).filter(
        ServiceTicket.id == ticket_id,
        ServiceTicket.partner_id == partner.id
    ).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found or access denied")
    
    existing_count = db.query(TicketAttachment).filter(
        TicketAttachment.ticket_id == ticket_id
    ).count()
    
    MAX_IMAGES = 10
    MAX_IMAGE_SIZE = 10 * 1024 * 1024
    MAX_VIDEO_SIZE = 50 * 1024 * 1024
    
    uploaded_media = []
    
    for file in files:
        mime_type = file.content_type or 'application/octet-stream'
        is_video = mime_type.startswith('video/')
        is_image = mime_type.startswith('image/')
        
        if not is_video and not is_image:
            raise HTTPException(status_code=400, detail=f"File {file.filename} must be image or video")
        
        file_content = await file.read()
        file_size = len(file_content)
        await file.seek(0)
        
        if is_video and file_size > MAX_VIDEO_SIZE:
            raise HTTPException(status_code=400, detail=f"Video exceeds 50MB limit")
        if is_image and file_size > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail=f"Image exceeds 10MB limit")
        
        try:
            attachment = TicketAttachment(
                ticket_id=ticket_id,
                file_path="pending",
                original_filename=file.filename,
                file_size=file_size,
                mime_type=mime_type,
                media_type='video' if is_video else 'image',
                uploaded_by_partner_id=partner.id,
                processing_status='pending'
            )
            db.add(attachment)
            db.flush()
            
            upload_result = await UniversalUploadService.handle_upload(
                file=file,
                table_name='ticket_attachment',
                record_id=attachment.id,
                uploaded_by_id=partner.id,
                uploaded_by_type='partner',
                storage_dir=f'service_ticket_media/{ticket_id}',
                db=db,
                defer_scheduler=True
            )
            
            attachment.file_path = upload_result['file_path']
            attachment.processing_status = 'pending' if upload_result.get('needs_compression') else 'completed'
            
            uploaded_media.append(attachment.to_dict())
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")
    
    log = TicketLog(
        ticket_id=ticket_id,
        action_type='partner_media_upload',
        action_description=f'Partner uploaded {len(uploaded_media)} media file(s)'
    )
    db.add(log)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"{len(uploaded_media)} file(s) uploaded",
        "media": uploaded_media
    }


# DC-VENDOR-REPAIR-TRACKER-001: These GET routes must be defined BEFORE
# the {ticket_id} wildcard below, otherwise FastAPI matches them as ticket_id.
@router.get("/service/vendor-repair-tracker")
async def list_vendor_repair_tracker(
    vendor_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 300,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC-VENDOR-REPAIR-TRACKER-001: List all spare parts sent to vendors for repair."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest
    from datetime import datetime

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    q = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.vendor_repair_status != None
    )
    if vendor_id:
        q = q.filter(ServiceTicketSpareRequest.vendor_id == vendor_id)
    if status:
        q = q.filter(ServiceTicketSpareRequest.vendor_repair_status == status)
    if date_from:
        try:
            q = q.filter(ServiceTicketSpareRequest.sent_to_vendor_date >= datetime.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            q = q.filter(ServiceTicketSpareRequest.sent_to_vendor_date <= datetime.fromisoformat(date_to + "T23:59:59"))
        except Exception:
            pass

    spares = q.order_by(ServiceTicketSpareRequest.sent_to_vendor_date.desc().nullslast()).limit(limit).all()

    results = []
    for s in spares:
        d = s.to_dict()
        if s.ticket:
            d['customer_name'] = getattr(s.ticket, 'customer_name', None)
            d['customer_phone'] = getattr(s.ticket, 'customer_phone', None)
            d['ticket_number'] = getattr(s.ticket, 'ticket_number', None) or f"TKT-{s.ticket_id}"
        if s.vendor:
            d['vendor_phone'] = getattr(s.vendor, 'mobile_number', None) or getattr(s.vendor, 'phone_number', None)
        results.append(d)

    all_st = [s.vendor_repair_status for s in spares if s.vendor_repair_status]
    summary = {
        "total": len(results),
        "pending": all_st.count('pending'),
        "sent": all_st.count('sent'),
        "waiting_for_repair": all_st.count('waiting_for_repair'),
        "repaired_received": all_st.count('repaired_received'),
        "cancelled": all_st.count('cancelled'),
    }
    return {"success": True, "items": results, "summary": summary}


@router.get("/service/vendor-repair-tracker/vendor-summary")
async def vendor_repair_tracker_summary(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC-VENDOR-REPAIR-TRACKER-001: Vendor-wise aggregation for the Vendor Summary tab."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest
    from app.models.staff_accounts import VendorMaster

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spares = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.vendor_repair_status != None,
        ServiceTicketSpareRequest.vendor_id != None
    ).all()

    vendor_cache = {}
    vendor_map = {}
    for s in spares:
        vid = s.vendor_id
        if vid not in vendor_map:
            if vid not in vendor_cache:
                v = db.query(VendorMaster).filter(VendorMaster.id == vid).first()
                vendor_cache[vid] = v
            v = vendor_cache[vid]
            vendor_map[vid] = {
                "vendor_id": vid,
                "vendor_name": s.vendor_name or (v.vendor_name if v else f"Vendor #{vid}"),
                "vendor_phone": (getattr(v, 'mobile_number', None) or getattr(v, 'phone_number', None)) if v else None,
                "total_sent": 0, "returned": 0, "pending": 0,
                "warranty_count": 0, "chargeable_count": 0,
                "total_repair_cost": 0.0, "repair_times_days": [],
                "last_activity": None
            }
        rec = vendor_map[vid]
        rec["total_sent"] += 1
        st = s.vendor_repair_status
        if st == 'repaired_received':
            rec["returned"] += 1
            if s.vendor_repair_cost:
                rec["chargeable_count"] += 1
                rec["total_repair_cost"] += float(s.vendor_repair_cost)
            else:
                rec["warranty_count"] += 1
            if s.sent_to_vendor_date and s.return_received_date:
                rec["repair_times_days"].append((s.return_received_date - s.sent_to_vendor_date).days)
        elif st in ('sent', 'waiting_for_repair'):
            rec["pending"] += 1
        if s.last_action_date:
            if not rec["last_activity"] or s.last_action_date > rec["last_activity"]:
                rec["last_activity"] = s.last_action_date

    result = []
    for rec in vendor_map.values():
        times = rec.pop("repair_times_days", [])
        rec["avg_repair_days"] = round(sum(times) / len(times), 1) if times else None
        rec["last_activity"] = rec["last_activity"].isoformat() if rec["last_activity"] else None
        result.append(rec)

    result.sort(key=lambda x: x["total_sent"], reverse=True)
    return {"success": True, "vendors": result}


# ===== DC PROTOCOL FEB 2026: PARAMETERIZED GET ROUTE MUST BE LAST =====
# This route must appear AFTER all specific /service/* GET routes to prevent
# paths like /service/queue, /service/stock-items/search, /service/reports/*
# from being matched as {ticket_id}

@router.get("/service/{ticket_id}")
async def get_service_ticket_details(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    Get service ticket details with spare requests.
    DC Protocol Jan 2026: Mobile-compatible format with success wrapper.
    """
    from app.models.ticket import ServiceTicketSpareRequest
    
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    is_staff = hasattr(current_user, 'emp_code') and current_user.emp_code
    is_admin = hasattr(current_user, 'is_admin') and callable(getattr(current_user, 'is_admin', None)) and current_user.is_admin()
    if ticket.user_id != current_user.id and not is_admin and not is_staff:
        raise HTTPException(status_code=403, detail="Access denied")
    
    spare_requests = db.query(ServiceTicketSpareRequest).filter(
        ServiceTicketSpareRequest.ticket_id == ticket_id
    ).order_by(ServiceTicketSpareRequest.requested_at.desc()).all()
    
    spare_dicts = []
    for sr in spare_requests:
        sr_dict = sr.to_dict()
        if sr_dict.get('media_files'):
            sr_dict['media_files'] = [
                {**m, 'url': f"/api/v1/tickets/spare-media/{sr.id}/{i}"} 
                for i, m in enumerate(sr_dict['media_files'])
            ]
        spare_dicts.append(sr_dict)
    
    return {
        "success": True,
        "ticket": ticket.to_dict(),
        "spare_requests": spare_dicts
    }


# ─────────────────────────────────────────────────────────────────────────────
# DC-VENDOR-REPAIR-TRACKER-001: Vendor Repair Tracking Endpoints (June 2026)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/service/spares/{spare_id}/send-to-vendor")
async def send_spare_to_vendor(
    spare_id: int,
    vendor_id: int = Body(..., embed=True),
    courier_name: Optional[str] = Body(default=None, embed=True),
    awb_number: Optional[str] = Body(default=None, embed=True),
    expected_return_date: Optional[str] = Body(default=None, embed=True),
    notes: Optional[str] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC-VENDOR-REPAIR-TRACKER-001: Send a spare part to vendor for repair.
    Sets vendor_repair_status='sent', logs ticket note.
    Access: any authenticated staff (assigned or manager).
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog
    from app.models.staff_accounts import VendorMaster
    from datetime import datetime, date as _date

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")

    if spare.vendor_repair_status in ('sent', 'waiting_for_repair', 'repaired_received'):
        raise HTTPException(status_code=400, detail=f"Spare already in repair pipeline (status: {spare.vendor_repair_status})")

    vendor = db.query(VendorMaster).filter(VendorMaster.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    now = datetime.now()
    spare.vendor_repair_status = 'sent'
    spare.sent_to_vendor_date = now
    spare.sent_courier_name = courier_name
    spare.sent_awb_number = awb_number
    spare.sent_by_staff_id = staff.id
    spare.last_action_date = now
    spare.vendor_repair_notes = notes
    spare.vendor_id = vendor_id
    spare.vendor_name = vendor.vendor_name
    # DC-CUSTOMER-SPARE-001: auto-generate sub_ticket_number + mark repair route on first vendor send
    if not spare.sub_ticket_number:
        existing_count = db.query(ServiceTicketSpareRequest).filter(
            ServiceTicketSpareRequest.ticket_id == spare.ticket_id,
            ServiceTicketSpareRequest.sub_ticket_number.isnot(None)
        ).count()
        spare.sub_ticket_number = f"TKT{spare.ticket_id}-R{existing_count + 1}"
    spare.repair_route = 'vendor_external'
    if expected_return_date:
        try:
            spare.expected_return_date = _date.fromisoformat(expected_return_date)
        except Exception:
            pass

    note_text = (
        f"[Repair] {spare.spare_item_name} sent to vendor {vendor.vendor_name} for repair"
        + (f" via {courier_name}" if courier_name else "")
        + (f" | AWB: {awb_number}" if awb_number else "")
        + (f" | Expected return: {expected_return_date}" if expected_return_date else "")
        + (f" | Notes: {notes}" if notes else "")
    )
    db.add(TicketLog(
        ticket_id=spare.ticket_id,
        action_type='spare_sent_to_vendor',
        action_description=note_text,
        staff_performer_id=staff.id
    ))
    db.commit()
    db.refresh(spare)
    return {"success": True, "message": "Spare sent to vendor for repair", "spare_request": spare.to_dict()}


@router.post("/service/spares/{spare_id}/mark-repaired-received")
async def mark_spare_repaired_received(
    spare_id: int,
    return_awb_number: Optional[str] = Body(default=None, embed=True),
    return_courier_name: Optional[str] = Body(default=None, embed=True),
    vendor_repair_cost: Optional[float] = Body(default=None, embed=True),
    notes: Optional[str] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC-VENDOR-REPAIR-TRACKER-001: Mark repaired spare as received back from vendor.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog
    from datetime import datetime

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")

    if spare.vendor_repair_status not in ('sent', 'waiting_for_repair'):
        raise HTTPException(status_code=400, detail=f"Cannot mark received — current repair status: {spare.vendor_repair_status or 'not sent to vendor'}")

    now = datetime.now()
    spare.vendor_repair_status = 'repaired_received'
    spare.return_received_date = now
    spare.return_awb_number = return_awb_number
    spare.return_courier_name = return_courier_name
    spare.vendor_repair_cost = vendor_repair_cost
    spare.last_action_date = now
    if notes:
        spare.vendor_repair_notes = (spare.vendor_repair_notes or '') + f"\n[Return] {notes}"

    note_text = (
        f"[Repair] {spare.spare_item_name} received back from vendor"
        + (f" via {return_courier_name}" if return_courier_name else "")
        + (f" | AWB: {return_awb_number}" if return_awb_number else "")
        + (f" | Repair cost: ₹{vendor_repair_cost}" if vendor_repair_cost else " | Under warranty (₹0)")
        + (f" | {notes}" if notes else "")
    )
    db.add(TicketLog(
        ticket_id=spare.ticket_id,
        action_type='spare_repair_received',
        action_description=note_text,
        staff_performer_id=staff.id
    ))
    db.commit()
    db.refresh(spare)
    return {"success": True, "message": "Repaired spare marked as received", "spare_request": spare.to_dict()}


@router.patch("/service/spares/{spare_id}/vendor-repair-update")
async def update_spare_vendor_repair_inline(
    spare_id: int,
    vendor_id: Optional[int] = Body(default=None, embed=True),
    vendor_repair_status: Optional[str] = Body(default=None, embed=True),
    sent_courier_name: Optional[str] = Body(default=None, embed=True),
    sent_awb_number: Optional[str] = Body(default=None, embed=True),
    expected_return_date: Optional[str] = Body(default=None, embed=True),
    vendor_repair_cost: Optional[float] = Body(default=None, embed=True),
    notes: Optional[str] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """DC-CUSTOMER-SPARE-001: Inline update of vendor repair tracking fields (status, vendor, courier, cost)."""
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog
    from app.models.staff_accounts import VendorMaster
    from datetime import datetime, date as _date

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")

    valid_statuses = ('pending', 'sent', 'waiting_for_repair', 'repaired_received', 'cancelled')
    if vendor_repair_status and vendor_repair_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    changes = []
    now = datetime.now()

    if vendor_id is not None:
        vendor = db.query(VendorMaster).filter(VendorMaster.id == vendor_id).first()
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        spare.vendor_id = vendor_id
        spare.vendor_name = vendor.vendor_name
        changes.append(f"vendor: {vendor.vendor_name}")

    if vendor_repair_status is not None:
        spare.vendor_repair_status = vendor_repair_status
        if vendor_repair_status == 'sent' and not spare.sent_to_vendor_date:
            spare.sent_to_vendor_date = now
        elif vendor_repair_status == 'repaired_received' and not spare.return_received_date:
            spare.return_received_date = now
        changes.append(f"status → {vendor_repair_status}")

    if sent_courier_name is not None:
        spare.sent_courier_name = sent_courier_name
        changes.append(f"courier: {sent_courier_name}")

    if sent_awb_number is not None:
        spare.sent_awb_number = sent_awb_number
        changes.append(f"AWB: {sent_awb_number}")

    if expected_return_date:
        try:
            spare.expected_return_date = _date.fromisoformat(expected_return_date)
            changes.append(f"exp return: {expected_return_date}")
        except Exception:
            pass

    if vendor_repair_cost is not None:
        spare.vendor_repair_cost = vendor_repair_cost
        changes.append(f"cost: ₹{vendor_repair_cost}")

    if notes:
        spare.vendor_repair_notes = (spare.vendor_repair_notes or '') + f"\n[Update] {notes}"
        changes.append("notes updated")

    spare.last_action_date = now

    if changes:
        db.add(TicketLog(
            ticket_id=spare.ticket_id,
            action_type='spare_vendor_repair_updated',
            action_description=f"[Repair Update] {spare.spare_item_name}: {' | '.join(changes)}",
            staff_performer_id=staff.id
        ))

    db.commit()
    db.refresh(spare)
    return {"success": True, "spare_request": spare.to_dict()}


@router.post("/service/spares/{spare_id}/log-whatsapp")
async def log_spare_whatsapp_send(
    spare_id: int,
    phone: str = Body(..., embed=True),
    message: str = Body(..., embed=True),
    context: Optional[str] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC-VENDOR-REPAIR-TRACKER-001: Log a WhatsApp communication for a spare repair item.
    Appends entry to whatsapp_log JSONB. Called when staff clicks 'Open WhatsApp' in UI.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest
    from sqlalchemy import text as _sql_t
    from datetime import datetime
    import json

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")

    existing = spare.whatsapp_log or []
    existing.append({
        "sent_at": datetime.now().isoformat(),
        "sent_by": f"{staff.first_name} {staff.last_name}".strip(),
        "sent_by_id": staff.id,
        "phone": phone,
        "message": message,
        "context": context or "Vendor Repair Communication"
    })
    db.execute(_sql_t(
        "UPDATE service_ticket_spare_request SET whatsapp_log = :log WHERE id = :id"
    ), {"log": json.dumps(existing), "id": spare_id})
    db.commit()
    return {"success": True, "total_sends": len(existing), "whatsapp_log": existing}


# VRT GET routes moved above {ticket_id} wildcard — see DC-VENDOR-REPAIR-TRACKER-001 block above.


# ─────────────────────────────────────────────────────────────────────────────
# DC-STANDALONE-SPARE-001: Standalone service repair entry (no ticket linked)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/service/spares/standalone")
async def create_standalone_spare_repair(
    item_name: str = Body(..., embed=True),
    quantity: int = Body(default=1, embed=True),
    vendor_id: Optional[int] = Body(default=None, embed=True),
    notes: Optional[str] = Body(default=None, embed=True),
    is_under_warranty: bool = Body(default=False, embed=True),
    warranty_invoice_number: Optional[str] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC-STANDALONE-SPARE-001: Create a standalone service repair entry not linked to any ticket.
    Requires ticket_id column to be nullable (migration spare_ticket_nullable_20260614).
    Sets repair_route='vendor_external', vendor_repair_status='pending'.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest
    from datetime import datetime

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spare = ServiceTicketSpareRequest(
        ticket_id=None,
        spare_item_name=item_name,
        quantity=quantity,
        vendor_id=vendor_id,
        notes=notes,
        is_under_warranty=is_under_warranty,
        warranty_invoice_number=warranty_invoice_number,
        spare_source='company',
        repair_route='vendor_external',
        vendor_repair_status='pending',
        procurement_status='pending',
        requested_by=staff.id,
        requested_at=datetime.now(),
    )
    db.add(spare)
    db.commit()
    db.refresh(spare)
    return {"success": True, "spare_id": spare.id, "message": "Standalone repair entry created"}


# ─────────────────────────────────────────────────────────────────────────────
# DC-CUSTOMER-SPARE-001: Customer-Supplied Parts & Repair Queue Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/service/{ticket_id}/customer-spares")
async def accept_customer_spare(
    ticket_id: int,
    item_name: str = Body(..., embed=True),
    description: Optional[str] = Body(default=None, embed=True),
    quantity: int = Body(default=1, embed=True),
    notes: Optional[str] = Body(default=None, embed=True),
    is_under_warranty: bool = Body(default=False, embed=True),
    warranty_invoice_number: Optional[str] = Body(default=None, embed=True),
    warranty_invoice_date: Optional[str] = Body(default=None, embed=True),
    sold_by: Optional[str] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC-CUSTOMER-SPARE-001: Register a customer-supplied spare part for a service ticket.
    spare_source='customer' — customer brings their own part; no company procurement/payment.
    If is_under_warranty=True, warranty_invoice_number / warranty_invoice_date / sold_by are required.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, ServiceTicket, TicketLog
    from datetime import datetime, date as _date

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Service ticket not found")

    # Validate warranty mandatory fields
    if is_under_warranty:
        missing = []
        if not warranty_invoice_number: missing.append("invoice_number")
        if not warranty_invoice_date:   missing.append("invoice_date")
        if not sold_by:                 missing.append("sold_by")
        if missing:
            raise HTTPException(status_code=422, detail=f"Warranty parts require: {', '.join(missing)}")

    # Parse invoice date
    parsed_invoice_date = None
    if warranty_invoice_date:
        try:
            parsed_invoice_date = _date.fromisoformat(warranty_invoice_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="warranty_invoice_date must be YYYY-MM-DD")

    spare = ServiceTicketSpareRequest(
        ticket_id=ticket_id,
        spare_item_name=item_name,
        spare_description=description,
        quantity_required=max(1, quantity),
        spare_source='customer',
        procurement_status='acknowledged',  # customer already has it — skip pending
        requested_by_id=staff.id,
        acknowledged_by_id=staff.id,
        requested_at=datetime.now(),
        acknowledged_at=datetime.now(),
        request_notes=notes,
        stock_available=True,
        # Warranty fields
        is_warranty=is_under_warranty,
        warranty_invoice_number=warranty_invoice_number.strip() if warranty_invoice_number else None,
        warranty_sale_date=parsed_invoice_date,
        warranty_notes=f"Sold by: {sold_by.strip()}" if sold_by else None,
    )
    db.add(spare)
    db.flush()

    warranty_note = f" | Warranty: Invoice {warranty_invoice_number}, sold by {sold_by}" if is_under_warranty else ""
    db.add(TicketLog(
        ticket_id=ticket_id,
        action_type='customer_spare_accepted',
        action_description=f"Customer-supplied part accepted: {item_name} (qty {quantity}){' | ' + notes if notes else ''}{warranty_note}",
        staff_performer_id=staff.id
    ))
    db.commit()
    db.refresh(spare)
    return {"success": True, "spare_request": spare.to_dict()}


@router.patch("/service/spares/{spare_id}/repair-route")
async def set_spare_repair_route(
    spare_id: int,
    repair_route: str = Body(..., embed=True),
    notes: Optional[str] = Body(default=None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC-CUSTOMER-SPARE-001: Set repair routing for a spare (customer-supplied or company).
    repair_route: 'vendor_external' | 'internal' | 'done'
    vendor_external auto-generates sub_ticket_number (TKT{id}-R{n}).
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, TicketLog
    from datetime import datetime

    if repair_route not in ('vendor_external', 'internal', 'done'):
        raise HTTPException(status_code=400, detail="repair_route must be vendor_external, internal, or done")

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_id).first()
    if not spare:
        raise HTTPException(status_code=404, detail="Spare request not found")

    spare.repair_route = repair_route
    spare.last_action_date = datetime.now()

    # DC-CUSTOMER-SPARE-001: customer spare sent to vendor → seed tracker record as 'pending'
    # so it appears in Vendor Returns page awaiting vendor selection & dispatch
    if repair_route == 'vendor_external':
        is_cust = getattr(spare, 'spare_source', 'company') == 'customer'
        if is_cust and not getattr(spare, 'vendor_repair_status', None):
            spare.vendor_repair_status = 'pending'
            spare.sent_to_vendor_date = datetime.now()

    if repair_route == 'vendor_external' and not spare.sub_ticket_number:
        existing_count = db.query(ServiceTicketSpareRequest).filter(
            ServiceTicketSpareRequest.ticket_id == spare.ticket_id,
            ServiceTicketSpareRequest.sub_ticket_number.isnot(None)
        ).count()
        spare.sub_ticket_number = f"TKT{spare.ticket_id}-R{existing_count + 1}"

    route_labels = {
        'vendor_external': 'Sent to Vendor for Repair',
        'internal': 'Routed for Internal Repair',
        'done': 'Repair Completed'
    }
    db.add(TicketLog(
        ticket_id=spare.ticket_id,
        action_type='spare_repair_route_set',
        action_description=f"[Repair Route] {spare.spare_item_name}: {route_labels.get(repair_route, repair_route)}"
                           + (f" | {notes}" if notes else ""),
        staff_performer_id=staff.id
    ))
    db.commit()
    db.refresh(spare)
    return {"success": True, "spare_request": spare.to_dict()}


@router.get("/service/repair-queue")
async def get_repair_queue(
    route: str = Query(default='vendor_external'),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_hybrid)
):
    """
    DC-CUSTOMER-SPARE-001: All spare parts routed for repair (vendor or internal).
    Used by the two new Service Queue tabs — Sent for Repair / Internal Repair.
    """
    from app.core.security import get_current_staff_user_from_hybrid
    from app.models.ticket import ServiceTicketSpareRequest, ServiceTicket

    if route not in ('vendor_external', 'internal'):
        raise HTTPException(status_code=400, detail="route must be vendor_external or internal")

    staff = get_current_staff_user_from_hybrid(current_user, db)
    if not staff:
        raise HTTPException(status_code=403, detail="Staff authentication required")

    spares = (
        db.query(ServiceTicketSpareRequest)
        .filter(
            ServiceTicketSpareRequest.repair_route == route,
            ServiceTicketSpareRequest.procurement_status != 'cancelled'
        )
        .order_by(ServiceTicketSpareRequest.last_action_date.desc().nullslast())
        .limit(200)
        .all()
    )

    result = []
    for s in spares:
        sd = s.to_dict()
        ticket = db.query(ServiceTicket).filter(ServiceTicket.id == s.ticket_id).first()
        if ticket:
            sd['ticket_number'] = ticket.ticket_number
            sd['customer_name'] = ticket.customer_name
            sd['vehicle_number'] = ticket.vehicle_number
            sd['ticket_sub_status'] = ticket.sub_status
        result.append(sd)

    return {"spare_repairs": result, "route": route, "count": len(result)}
