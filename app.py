from fastapi import FastAPI, UploadFile, File, HTTPException,Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Query

from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from database import SessionLocal, Document, User, AuditLog

import shutil
import uuid
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

import qrcode
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter

app = FastAPI()
app.mount("/static", StaticFiles(directory="frontend"), name="static")
app.mount("/docs", StaticFiles(directory="documents"), name="documents")
app.mount("/output", StaticFiles(directory="output"), name="output")
# --------------------------------------------------
# CREATE FASTAPI INSTANCE (IMPORTANT NAME: app)
# --------------------------------------------------

# --------------------------------------------------
# FOLDERS
# --------------------------------------------------
UPLOAD_FOLDER = "documents"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --------------------------------------------------
# HELPER FUNCTION: HASH FILE
# --------------------------------------------------
def hash_file(filepath):
    digest = hashes.Hash(hashes.SHA256())
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            digest.update(chunk)
    return digest.finalize()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials"
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()

    if user is None:
        raise credentials_exception

    return user

def log_action(document_id, action, user):

    db = SessionLocal()

    log = AuditLog(
        id=str(uuid.uuid4()),
        document_id=document_id,
        action=action,
        performed_by=user
    )

    db.add(log)
    db.commit()
    db.close()
# --------------------------------------------------
# Register
# --------------------------------------------------

@app.post("/register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):

    db = SessionLocal()

    existing_user = db.query(User).filter(User.username == username).first()

    if existing_user:
        db.close()
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        hashed_password=hash_password(password),
        role=role
    )

    db.add(user)
    db.commit()
    db.close()

    return {"message": "User registered successfully"}


# --------------------------------------------------
# login
# --------------------------------------------------
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):

    db = SessionLocal()

    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        db.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )

    db.close()

    return {"access_token": token, "token_type": "bearer","username": user.username,
    "role": user.role}
# --------------------------------------------------
# HOME ROUTE
# --------------------------------------------------
from fastapi.responses import FileResponse

@app.get("/")
def serve_login():
    return FileResponse("/Users/apple/Desktop/Project/frontend/index.html")

@app.get("/dashboard")
def serve_dashboard():
    return FileResponse("/Users/apple/Desktop/Project/frontend/dashboard.html")

# --------------------------------------------------
# UPLOAD + HASH + SIGN
# --------------------------------------------------
@app.post("/upload")
async def upload_document(file: UploadFile = File(...),signer_id: str = Form(...),current_user: User = Depends(get_current_user)):

    doc_id = str(uuid.uuid4())
    file_location = f"{UPLOAD_FOLDER}/{doc_id}.pdf"

    # Save uploaded file
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Insert into DB
    db = SessionLocal()

    new_doc = Document(
    id=doc_id,
    file_path=file_location,
    uploaded_by=current_user.id,
    signer_id=signer_id,
    status="PENDING"
)

    db.add(new_doc)
    db.commit()
    db.close()
    log_action(doc_id, "UPLOAD", current_user.username)
    return {
        "message": "Document uploaded successfully",
        "document_id": doc_id,
        "status": "PENDING"
    }


# --------------------------------------------------
# Sign Documents
# --------------------------------------------------
@app.post("/sign/{doc_id}")
def sign_document(doc_id: str,current_user: User = Depends(get_current_user)):
        if current_user.role != "SIGNER":
            raise HTTPException(status_code=403, detail="Only signer can sign documents")

        db = SessionLocal()
        doc = db.query(Document).filter(Document.id == doc_id).first()

        if not doc:
            db.close()
            raise HTTPException(status_code=404, detail="Document not found")

        if doc.status == "SIGNED":
            db.close()
            return {"message": "Already signed"}

        # Hash file
        file_hash = hash_file(doc.file_path)

        # Load private key (Signer B)
        with open("/Users/apple/Desktop/Project/crypto/private_key.pem", "rb") as f:
            private_key = serialization.load_pem_private_key(
            f.read(),
            password=None
        )

        signature = private_key.sign(
        file_hash,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
        )

        signature_path = f"{OUTPUT_FOLDER}/{doc_id}_signature.bin"
        with open(signature_path, "wb") as f:
            f.write(signature)

        doc.signature_path = signature_path
        doc.status = "SIGNED"
        log_action(doc_id, "SIGN", current_user.username)
        # ---------------------------------
        # Generate QR
        # ---------------------------------
        verification_link = f"http://172.20.10.3:8000/verify/{doc_id}"

        qr = qrcode.make(verification_link)
        qr_path = f"{OUTPUT_FOLDER}/{doc_id}_qr.png"
        qr.save(qr_path)

        # ---------------------------------
        # Embed QR into PDF
        # ---------------------------------
        overlay_pdf = f"{OUTPUT_FOLDER}/{doc_id}_overlay.pdf"

        c = canvas.Canvas(overlay_pdf)
        c.drawImage(qr_path, 450, 700, width=100, height=100)
        c.save()

        reader = PdfReader(doc.file_path)
        overlay = PdfReader(overlay_pdf)
        writer = PdfWriter()

        page = reader.pages[0]
        page.merge_page(overlay.pages[0])
        writer.add_page(page)

        final_pdf_path = f"{OUTPUT_FOLDER}/{doc_id}_signed.pdf"

        with open(final_pdf_path, "wb") as f:
            writer.write(f)

        doc.signed_pdf_path = final_pdf_path

        # ---------------------------------
        # Commit DB AFTER everything
        # ---------------------------------
        db.commit()
        db.close()

        return {
            "message": "Document signed & QR embedded successfully ✅",
            "document_id": doc_id,
            "signed_pdf": final_pdf_path,
            "verification_link": verification_link
        }
# --------------------------------------------------
# audit logs
# --------------------------------------------------
@app.get("/audit/{doc_id}")
def get_audit_logs(doc_id: str):

    db = SessionLocal()

    logs = db.query(AuditLog).filter(AuditLog.document_id == doc_id).all()

    db.close()

    return logs
# --------------------------------------------------
# VERIFY DOCUMENT
# --------------------------------------------------
@app.get("/verify/{doc_id}")
def verify_document(doc_id: str):
    db = SessionLocal()

    doc = db.query(Document).filter(Document.id == doc_id).first()

    if not doc:
        db.close()
        return {"status": "Document not found"}

    if doc.status != "SIGNED":
        db.close()
        return {"status": "Document not signed"}

    # 🔥 GET SIGNER NAME
    signer = db.query(User).filter(User.id == doc.signer_id).first()

    signer_name = signer.username if signer else "Unknown"

    db.close()

    return {
        "status": f"Valid Document, Signed by {signer_name}"
    }
@app.get("/signers")
def get_signers(current_user: User = Depends(get_current_user)):

    db = SessionLocal()

    signers = db.query(User).filter(User.role == "SIGNER").all()

    result = []
    for s in signers:
        result.append({
            "id": s.id,
            "username": s.username
})

    db.close()

    return result
@app.get("/signer/pending")
def signer_pending_docs(current_user: User = Depends(get_current_user)):

    # ✅ Role check
    if current_user.role != "SIGNER":
        raise HTTPException(status_code=403, detail="Only signer can view this")

    db = SessionLocal()

    # ✅ Fetch documents assigned to this signer
    docs = db.query(Document).filter(
        Document.signer_id == current_user.id,
        Document.status == "PENDING"
    ).all()

    result = []   # ✅ Initialize first

    # ✅ Build response
    for d in docs:
        user = db.query(User).filter(User.id == d.uploaded_by).first()

        result.append({
            "id": d.id,
            "uploaded_by": user.username if user else "Unknown"
        })

    db.close()

    return result
    
@app.get("/user/documents")
def user_documents(current_user: User = Depends(get_current_user)):

    db = SessionLocal()

    docs = db.query(Document).filter(
        Document.uploaded_by == current_user.id
    ).all()

    result = []   # ✅ DEFINE FIRST

    for d in docs:
        signer = db.query(User).filter(User.id == d.signer_id).first()

        result.append({
            "id": d.id,
            "signer": signer.username if signer else "Unknown",  # ✅ SAFE
            "status": d.status,
            "signed_pdf": d.signed_pdf_path
        })

    db.close()
    return result




@app.get("/document/{doc_id}")
def view_document(doc_id: str, token: str = Query(...)):

    # decode token manually
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")

    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()

    doc = db.query(Document).filter(Document.id == doc_id).first()

    if not doc:
        raise HTTPException(status_code=404)

    if doc.uploaded_by != user.id and doc.signer_id != user.id:
        raise HTTPException(status_code=403)

    return FileResponse(doc.file_path, media_type="application/pdf")

@app.get("/signer/signed")
def signer_signed_docs(current_user: User = Depends(get_current_user)):

    if current_user.role != "SIGNER":
        raise HTTPException(status_code=403, detail="Only signer can view")

    db = SessionLocal()

    docs = db.query(Document).filter(
        Document.signer_id == current_user.id,
        Document.status == "SIGNED"
    ).all()

    result = []

    for d in docs:
        result.append({
            "id": d.id,
            "signed_pdf": d.signed_pdf_path
        })

    db.close()

    return result