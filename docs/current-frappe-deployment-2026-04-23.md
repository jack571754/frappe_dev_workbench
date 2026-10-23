# Current Frappe Deployment Document

Generated on: 2026-04-23

## 1. Deployment Overview

- Deployment type: single-host Docker Compose deployment
- Compose project name: `erpnext`
- Actual deployment directory: `/root/gitops`
- Active Compose file: `/root/gitops/erpnext-ip.yaml`
- Host startup: `docker.service` is enabled
- Actual application type: this is a `Frappe 16 + custom app` deployment, not a standard ERPNext installation

## 2. Application Stack

- Framework: `frappe 16.16.0`
- Custom app: `product_sales_planning 0.0.1`
- Not found in installed apps: `erpnext`
- Business image: `crpi-er7i3tcavt4npqiz.cn-chengdu.personal.cr.aliyuncs.com/571754723/frappev16:v1.0.1`
- Database image: `mariadb:11.8`
- Redis image: `redis:8.6-alpine`

## 3. Service Topology

The deployment contains these services:

- `backend`: Frappe Python backend
- `frontend`: Nginx entry service
- `scheduler`: scheduled job service
- `queue-short`: short/default queue worker
- `queue-long`: long/default/short queue worker
- `websocket`: Socket.IO / realtime service
- `configurator`: one-shot initialization container
- `db`: MariaDB database
- `redis-cache`: cache Redis
- `redis-queue`: queue / socket Redis

Startup order:

1. `db`, `redis-cache`, `redis-queue`
2. `configurator`
3. `backend`, `scheduler`, `queue-short`, `queue-long`, `websocket`
4. `frontend`

## 4. Access and Networking

- Docker network: `erpnext_default`
- Frontend published port: host `8085` -> container `8080`
- Direct confirmed access entry: `http://<server-ip>:8085`
- Site business URL configured in site config: `https://psp.xajuzi.com`
- Frontend site header setting: `FRAPPE_SITE_NAME_HEADER=172.16.200.44`

Current observation:

- The deployed site directory name is IP-based: `172.16.200.44`
- The configured `host_name` uses a domain: `https://psp.xajuzi.com`
- No dedicated `nginx` / `traefik` / `caddy` reverse proxy for this stack was confirmed on ports `80/443`
- Therefore, if the domain is in active use, the reverse-proxy or gateway layer is likely outside this Compose stack

## 5. Site Information

- Site directory: `/home/frappe/frappe-bench/sites/172.16.200.44`
- Installed apps on the site:
  - `frappe 16.16.0`
  - `product_sales_planning 0.0.1`
- Database type: `mariadb`
- Site uses a dedicated database and database user

## 6. Core Configuration

Global config file:

- `/home/frappe/frappe-bench/sites/common_site_config.json`

Confirmed settings:

- `db_host = db`
- `db_port = 3306`
- `redis_cache = redis://redis-cache:6379`
- `redis_queue = redis://redis-queue:6379`
- `redis_socketio = redis://redis-queue:6379`
- `socketio_port = 9000`
- `chromium_path = /usr/bin/chromium-headless-shell`

Site config file:

- `/home/frappe/frappe-bench/sites/172.16.200.44/site_config.json`

Sensitive values were intentionally omitted from this document. If the previously exposed values were real production secrets, they should be rotated immediately.

## 7. Data Persistence

### Named volumes

- Site data volume: `erpnext_sites`
  - Host path: `/var/lib/docker/volumes/erpnext_sites/_data`
  - Container path: `/home/frappe/frappe-bench/sites`

- Database volume: `erpnext_db-data`
  - Host path: `/var/lib/docker/volumes/erpnext_db-data/_data`
  - Container path: `/var/lib/mysql`

- Queue Redis volume: `erpnext_redis-queue-data`

### Logs

- Backend logs path in container: `/home/frappe/frappe-bench/logs`
- Current host storage uses a Docker anonymous volume
- This is functional, but less maintainable than a named volume or explicit bind mount

## 8. Restart Policy and Availability

- Core services use `unless-stopped`
- `configurator` uses `on-failure`
- `docker.service` is enabled on boot

Operational implication:

- After a host reboot, Docker should start automatically
- The main Frappe services should auto-recover unless they were manually stopped

## 9. Backup Status

Observed backup-related information:

- Directory `/root/gitops/backups` currently exists but is empty
- Root crontab includes:

```cron
0 2 * * * /home/mysql_backup/backup_frappe_mariadb.sh
```

Current conclusion:

- A MariaDB backup task exists
- It is not yet confirmed whether `erpnext_sites` is also backed up
- Until both database and site files are backed up together, restore completeness is not guaranteed

## 10. Routine Operations

### Check container status

```bash
docker ps --filter name=erpnext-
docker ps -a --filter name=erpnext-
```

### Start services

```bash
docker compose -f /root/gitops/erpnext-ip.yaml up -d
```

### Stop services

```bash
docker compose -f /root/gitops/erpnext-ip.yaml down
```

### Restart key services

```bash
docker restart erpnext-backend-1
docker restart erpnext-frontend-1
docker restart erpnext-db-1
```

### View logs

```bash
docker logs -f erpnext-backend-1
docker logs -f erpnext-frontend-1
docker logs -f erpnext-db-1
docker logs -f erpnext-scheduler-1
```

### Enter backend container

```bash
docker exec -it erpnext-backend-1 bash
```

### Check framework and app versions

```bash
docker exec erpnext-backend-1 bench version
docker exec erpnext-backend-1 bash -lc 'bench --site 172.16.200.44 list-apps'
```

### Check config and volumes

```bash
docker exec erpnext-backend-1 bash -lc 'cat /home/frappe/frappe-bench/sites/common_site_config.json'
docker exec erpnext-backend-1 bash -lc 'cat /home/frappe/frappe-bench/sites/172.16.200.44/site_config.json'
docker inspect erpnext-backend-1 --format '{{range .Mounts}}{{println .Destination " <- " .Source}}{{end}}'
docker inspect erpnext-db-1 --format '{{range .Mounts}}{{println .Destination " <- " .Source}}{{end}}'
docker volume ls
```

### Pull updated images and redeploy

```bash
docker compose -f /root/gitops/erpnext-ip.yaml pull
docker compose -f /root/gitops/erpnext-ip.yaml up -d
```

## 11. Known Risks

### High risk

- Sensitive values were exposed during information collection, including database credentials, encryption material, and third-party integration secrets
- If those were production secrets, they should be treated as leaked and rotated immediately
- The Compose file contained a weak MariaDB root password in plain text; this should be replaced with a strong secret and removed from inline YAML

### Medium to high risk

- The Compose project is named `erpnext`, but the deployed app set does not include `erpnext`
- This can cause confusion during operations, upgrades, monitoring, and handover

### Medium risk

- Site directory naming is IP-based while `host_name` is domain-based
- This mixed model can lead to confusion in reverse-proxy, HTTPS, callback, and future multi-site scenarios

- Current evidence confirms database backup scheduling, but not full site-file backup
- Without `sites` backup, restore may miss attachments, private files, and site-specific configuration

- The backend logs volume is anonymous, which makes long-term operations and migration less convenient

- `pull_policy: always` increases deployment variability if the same tag is overwritten upstream

## 12. Recommended Remediation

1. Rotate all exposed secrets immediately
2. Replace the weak MariaDB root password with a strong secret
3. Move secrets out of inline Compose YAML into env files or a proper secret management solution
4. Confirm and implement backup for both database and `erpnext_sites`
5. Document the full domain access path for `psp.xajuzi.com`
6. Decide whether the site should be identified by IP or domain, then standardize it
7. Replace anonymous log storage with a named volume or explicit bind mount
8. Use immutable image tags or digests for production deployment

## 13. Pending Information

To complete the backup and restore section, the following should still be reviewed:

```bash
sed -n '1,260p' /home/mysql_backup/backup_frappe_mariadb.sh
```

That script is needed to document:

- backup target path
- retention strategy
- compression behavior
- cleanup policy
- restore prerequisites
- whether the backup covers only MariaDB or the full application state
