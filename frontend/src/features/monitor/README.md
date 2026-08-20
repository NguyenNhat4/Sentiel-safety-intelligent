# Live Monitor

Owns the Live Monitor surface, the four-camera 2×2 MJPEG viewer, the explicit
**Tạo vùng** workflow, revisioned multi-zone draft/applied state and normalized
four-point editing. Each display camera reads the persisted mapping selected by
`system_admin`; an unmapped camera remains empty. Local video upload is not part
of the app flow. MJPEG-to-inference integration remains a separate runtime gate
until the backend stream adapter is approved.
