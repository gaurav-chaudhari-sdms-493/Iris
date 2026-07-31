# Internal Security Policy - Project Iris 👁️⚡

---

## 📌 Document Metadata
- **Project Version**: `v1.0.0`
- **Document Version**: `1.0.0`
- **Last Updated**: `2026-07-31`
- **Status**: `Approved / Operational`
- **Classification**: `STARK AI Internal & Confidential`

---

Project Iris controls physical electrical loads, lighting rows, and HVAC units within STARK AI office facilities. Maintaining rigorous security across hardware relays, computer vision video streams, and network sockets is critical.

---

## 1. Internal Security Incident Reporting

If you discover a security vulnerability, exposed local key, or unauthenticated endpoint:

- **Primary Contact**: STARK AI Cyber Security Team (`security@stark.ai`)
- **Internal Slack Channel**: `#sec-ops-internal`
- **Severity SLA**: Immediate response within 4 hours for physical hazard vulnerabilities (e.g. relay lockout or unauthorized AC control).

Do NOT discuss security vulnerabilities in public channels or external forums.

---

## 2. Secrets Management & Credential Protection

### 2.1 Confidentiality of Local Keys & API Tokens
- **Prohibited File Commits**: Never commit `.env` or `hardware_config.json` files to git repositories.
- **Gitignore Enforcement**:
  ```gitignore
  .env
  *.key
  backend/data/hardware_config.json
  ```
- **Local Key Protection**: Tuya `RELAY_A_KEY` and `RELAY_B_KEY` grant direct TCP control over office lighting relays. Protect these credentials as high-value internal secrets.

### 2.2 CCTV RTSP Stream Credentials
- RTSP video feeds are strictly internal camera streams. Always configure strong RTSP passwords (`rtsp://admin:StrongPassword@...`).
- Video stream frames processed in `backend/vision/` must remain in RAM and must not be saved to disk or broadcast externally.

---

## 3. Physical Office IoT Network Isolation

Commercial office IoT hardware (AZIOT 4 Node Smart Switches, Broadlink RM4 Mini, CCTV cameras) must be isolated from guest and general staff Wi-Fi networks:

```
[ STARK AI Internal Workstation Network ] ---- Restricted Firewall ----> [ Isolated IoT / Vision VLAN 30 ]
(React Dashboard / Server)                                                (AZIOT Relays / RTSP Cameras)
```

### Mandated Network Policies:
1. **Dedicated VLAN**: Deploy all AZIOT relays, Broadlink IR blasters, and RTSP cameras on an isolated corporate VLAN (e.g. VLAN 30).
2. **Internet Outbound Block**: Configure router firewall rules to block outbound public internet access for CCTV cameras and smart switch modules.
3. **Internal Subnet Binding**: Bind FastAPI server endpoints to internal interface IPs (`192.168.30.126:8008`) or `localhost`.

---

## 4. API & WebSocket Security

- **Intranet Binding**: REST API endpoints are designed for STARK AI internal network access.
- **CORS Policies**: In production deployment, restrict `CORSMiddleware` origins to authorized dashboard internal domains.
- **Pydantic Validation**: All REST payloads and WebSocket messages are validated via Pydantic schemas to prevent injection or invalid state mutations.
