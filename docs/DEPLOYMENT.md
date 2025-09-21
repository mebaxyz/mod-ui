# MOD UI Deployment Guide

## Overview

This guide covers deployment options for MOD UI, from local development to production environments. MOD UI can be deployed as a standalone application, in Docker containers, or as a system service.

## Deployment Options

### 1. Local Development Deployment

**Requirements:**
- Python 3.8+
- JACK Audio Connection Kit
- LV2 plugins
- MOD hardware (optional)

**Installation:**
```bash
# Clone repository
git clone https://github.com/mebaxyz/mod-ui.git
cd mod-ui

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Build C++ utilities
make -C utils

# Install MOD UI
pip install -e .

# Run
mod-ui
```

**Access:**
- Web interface: `http://localhost:8888`
- API: `http://localhost:8888/api/v1/`

### 2. Docker Container Deployment

**Requirements:**
- Docker
- Docker Compose
- Linux host with audio hardware access

**Quick Start:**
```bash
# Clone repository
git clone https://github.com/mebaxyz/mod-ui.git
cd mod-ui

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

**Docker Compose Configuration:**
```yaml
version: '3.8'
services:
  mod-ui:
    build: .
    ports:
      - "8888:8888"
    devices:
      - /dev/snd:/dev/snd
    privileged: true
    environment:
      - JACK_NO_START_SERVER=1
    volumes:
      - ./data:/data
      - /tmp/.X11-unix:/tmp/.X11-unix
    network_mode: host
```

### 3. System Service Deployment

**Requirements:**
- Ubuntu/Debian system
- Root access
- Audio hardware configured

**Installation Script:**
```bash
#!/bin/bash
# install-mod-ui.sh

# Install system dependencies
apt-get update
apt-get install -y python3 python3-pip python3-venv jackd2 lv2-dev

# Create mod user
useradd -r -s /bin/false mod

# Install MOD UI
cd /opt
git clone https://github.com/mebaxyz/mod-ui.git
cd mod-ui
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
make -C utils
pip install -e .

# Create systemd service
cat > /etc/systemd/system/mod-ui.service << EOF
[Unit]
Description=MOD UI
After=jackd.service
Requires=jackd.service

[Service]
Type=simple
User=mod
ExecStart=/opt/mod-ui/venv/bin/mod-ui --port 8888
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable mod-ui
systemctl start mod-ui
```

## Production Configuration

### Environment Variables

```bash
# Basic configuration
MOD_PORT=8888
MOD_HOST=0.0.0.0
MOD_DEBUG=0

# Audio configuration
JACK_NO_START_SERVER=1
JACK_DEFAULT_SERVER=default

# Hardware configuration
MOD_SERIAL_DEVICE=/dev/ttyACM0
MOD_HARDWARE_TIMEOUT=5000

# Web configuration
MOD_WEB_ROOT=/opt/mod-ui/html
MOD_STATIC_CACHE=3600
```

### Configuration Files

**mod-ui.conf:**
```ini
[server]
port = 8888
host = 0.0.0.0
debug = false

[audio]
jack_server = default
buffer_size = 128
sample_rate = 48000

[hardware]
serial_device = /dev/ttyACM0
timeout = 5000
retry_count = 3

[web]
static_cache = 3600
template_cache = 3600
websocket_timeout = 30000
```

### Security Configuration

**Firewall Rules:**
```bash
# Allow web interface access
ufw allow 8888/tcp

# Restrict to local network only
ufw allow from 192.168.1.0/24 to any port 8888
```

**User Permissions:**
```bash
# Add user to audio groups
usermod -a -G audio mod
usermod -a -G dialout mod

# Set proper permissions for serial device
chmod 666 /dev/ttyACM0
```

## Hardware-Specific Deployments

### MOD Duo

**Requirements:**
- MOD Duo hardware
- USB connection
- Audio interface

**Configuration:**
```bash
# Serial device
MOD_SERIAL_DEVICE=/dev/ttyACM0

# Audio setup
JACK_DEFAULT_SERVER=mod
```

### Generic Hardware

**Requirements:**
- Serial-connected hardware
- JACK-compatible audio interface
- LV2 plugin host

**Configuration:**
```bash
# Custom serial device
MOD_SERIAL_DEVICE=/dev/ttyUSB0

# Audio device
JACK_DEFAULT_SERVER=default
ALSA_DEVICE=hw:0,0
```

## Monitoring and Maintenance

### System Monitoring

**Basic Monitoring:**
```bash
# Check service status
systemctl status mod-ui

# View logs
journalctl -u mod-ui -f

# Check resource usage
top -p $(pgrep mod-ui)
```

**Performance Monitoring:**
```bash
# CPU usage
ps aux | grep mod-ui

# Memory usage
pmap $(pgrep mod-ui)

# Network connections
netstat -tlnp | grep :8888
```

### Log Management

**Log Rotation:**
```bash
# Configure logrotate
cat > /etc/logrotate.d/mod-ui << EOF
/var/log/mod-ui/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 mod mod
}
EOF
```

**Centralized Logging:**
```bash
# Install rsyslog configuration
cat > /etc/rsyslog.d/mod-ui.conf << EOF
:programname, startswith, "mod-ui" /var/log/mod-ui/app.log
& stop
EOF

systemctl restart rsyslog
```

### Backup and Recovery

**Data Backup:**
```bash
#!/bin/bash
# backup-mod-ui.sh

BACKUP_DIR="/var/backups/mod-ui"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup pedalboards
tar -czf $BACKUP_DIR/pedalboards_$DATE.tar.gz /opt/mod-ui/pedalboards/

# Backup configuration
cp /etc/mod-ui.conf $BACKUP_DIR/config_$DATE.conf

# Backup user data
tar -czf $BACKUP_DIR/userdata_$DATE.tar.gz /opt/mod-ui/userdata/
```

**Recovery:**
```bash
#!/bin/bash
# restore-mod-ui.sh

BACKUP_DATE="20231201_120000"

# Stop service
systemctl stop mod-ui

# Restore data
tar -xzf /var/backups/mod-ui/pedalboards_$BACKUP_DATE.tar.gz -C /
cp /var/backups/mod-ui/config_$BACKUP_DATE.conf /etc/mod-ui.conf

# Start service
systemctl start mod-ui
```

## Troubleshooting Deployment Issues

### Service Won't Start

**Check Dependencies:**
```bash
# Verify Python installation
python3 --version

# Check JACK installation
jackd --version

# Verify LV2 plugins
lv2ls | head -5
```

**Check Logs:**
```bash
# System logs
journalctl -u mod-ui -n 50

# Application logs
tail -f /var/log/mod-ui/app.log
```

**Common Issues:**
- Missing dependencies
- Permission issues with audio devices
- Serial device not accessible
- Port already in use

### Audio Issues

**JACK Problems:**
```bash
# Check JACK status
jackd -S

# List JACK clients
jack_lsp

# Check sample rate
jack_samplerate
```

**ALSA Issues:**
```bash
# List audio devices
aplay -l

# Test audio output
speaker-test -c 2 -t sine
```

### Web Interface Issues

**Port Conflicts:**
```bash
# Check port usage
netstat -tlnp | grep :8888

# Change port
MOD_PORT=8889 mod-ui
```

**Firewall Issues:**
```bash
# Check firewall status
ufw status

# Allow port
ufw allow 8888/tcp
```

### Hardware Communication Issues

**Serial Device Problems:**
```bash
# Check device existence
ls -la /dev/ttyACM*

# Test serial communication
stty -F /dev/ttyACM0
```

**Permission Issues:**
```bash
# Add user to dialout group
usermod -a -G dialout mod

# Set device permissions
chmod 666 /dev/ttyACM0
```

## Scaling and High Availability

### Load Balancing

**Nginx Configuration:**
```nginx
upstream mod_ui_backend {
    server 127.0.0.1:8888;
    server 127.0.0.1:8889 backup;
}

server {
    listen 80;
    server_name mod-ui.example.com;

    location / {
        proxy_pass http://mod_ui_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Multiple Instances

**Docker Compose for Scaling:**
```yaml
version: '3.8'
services:
  mod-ui-1:
    image: mod-ui:latest
    environment:
      - MOD_INSTANCE_ID=1
    ports:
      - "8888:8888"

  mod-ui-2:
    image: mod-ui:latest
    environment:
      - MOD_INSTANCE_ID=2
    ports:
      - "8889:8888"
```

### Database Considerations

**For Multi-Instance Deployments:**
- Shared storage for pedalboards
- Centralized configuration management
- Session state synchronization

## Update Procedures

### Rolling Updates

**Zero-Downtime Updates:**
```bash
# Update code
cd /opt/mod-ui
git pull origin main

# Install new dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Build utilities
make -C utils clean
make -C utils

# Restart service
systemctl restart mod-ui
```

### Rollback Procedure

**Quick Rollback:**
```bash
# Revert to previous version
cd /opt/mod-ui
git checkout HEAD~1

# Reinstall
source venv/bin/activate
pip install -e .

# Restart
systemctl restart mod-ui
```

## Performance Tuning

### System Optimization

**Kernel Parameters:**
```bash
# Real-time kernel settings
echo 80 > /proc/sys/kernel/sched_rt_runtime_us
echo 950000 > /proc/sys/kernel/sched_rt_period_us

# Network optimization
echo 1 > /proc/sys/net/ipv4/tcp_low_latency
```

**JACK Optimization:**
```bash
# Low latency settings
jackd -d alsa -r 48000 -p 128 -n 2
```

### Application Tuning

**Memory Optimization:**
```python
# In mod/__init__.py
import gc
gc.set_threshold(1000, 10, 10)
```

**Threading Optimization:**
```python
# Use thread pool for I/O operations
import concurrent.futures
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
```

## Compliance and Security

### Security Hardening

**Service Hardening:**
```bash
# Run as non-root user
useradd -r -s /bin/false mod

# Limit capabilities
capsh --print | grep cap_net_bind_service
```

**Network Security:**
```bash
# Use HTTPS
certbot --nginx -d mod-ui.example.com

# Configure SSL
ssl_certificate /etc/letsencrypt/live/mod-ui.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/mod-ui.example.com/privkey.pem;
```

### Data Protection

**Backup Encryption:**
```bash
# Encrypt backups
tar -czf - /opt/mod-ui/data | gpg -c > backup.tar.gz.gpg
```

**Access Control:**
```bash
# File permissions
chown -R mod:mod /opt/mod-ui
chmod -R 755 /opt/mod-ui
chmod 600 /etc/mod-ui.conf
```

## Support and Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Check system logs
- Monitor resource usage
- Verify backup integrity

**Monthly:**
- Update system packages
- Review security patches
- Clean up old logs

**Quarterly:**
- Full system backup
- Performance benchmarking
- Hardware health checks

### Getting Help

**Community Support:**
- [MOD Forum](https://forum.moddevices.com)
- [GitHub Issues](https://github.com/mebaxyz/mod-ui/issues)
- [Documentation](https://moddevices.com/docs)

**Commercial Support:**
- MOD Devices enterprise support
- Professional services partners

This deployment guide covers the most common deployment scenarios for MOD UI. For specific requirements or custom deployments, consult the MOD Devices support team.</content>
<parameter name="filePath">/home/nicolas/project/madeline/mod-ui/docs/DEPLOYMENT.md