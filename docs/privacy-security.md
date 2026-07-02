# Privacy and Security

This project handles data that can be sensitive, especially student information, face images, trained models, QR codes, and camera recordings.

## MVP Privacy Position

- This is a local MVP/final demo version.
- Face data is stored locally.
- The SQLite database is stored locally.
- Generated QR/media files may contain sensitive student information.
- LAN demo is recommended for presentation.
- Public deployment needs extra security work before real use.

## Do Not Commit

Do not commit:

- `.env`
- `smart_classroom.db`
- dataset images
- trained models
- recordings
- private face data
- generated QR/media if sensitive

Examples of sensitive or local-only paths:

```text
backend/ai_module/face_recognition/datasets/
backend/ai_module/face_recognition/models/
backend/ai_module/object_detection/models/
backend/app/static/recordings/
backend/app/static/generated_qr/
*.db
*.sqlite
*.sqlite3
```

## Demo Safety Notes

- Use demo students or consented test data.
- Avoid showing private student information on screen unless it is demo data.
- Stop monitoring when the demo ends.
- Do not upload face datasets or recordings to GitHub.
- Do not share the LAN URL outside the local presentation network.

## Production Security Needs

Before public deployment, the project needs:

- HTTPS
- Strong password policy and secure session handling
- Proper secret management
- Role and permission review
- Database backup and recovery plan
- Consent workflow for face data
- Data retention and deletion policy
- Encrypted storage for sensitive files where required
- Logging and monitoring
- Security testing before real classroom use
