# DevSecOps Todo Application

An end-to-end DevSecOps portfolio project that builds, tests, scans, containerizes, deploys, and monitors a Python Flask Todo application using **GitHub, Jenkins, pytest, SonarQube, Docker, Docker Hub, Kubernetes, Prometheus, and Grafana**. Grafana is exposed through Nginx over HTTPS with a Let's Encrypt IP-address certificate.

> **Status:** Working portfolio MVP. CI/CD, Kubernetes deployment, monitoring dashboards, HTTPS access, and a Certbot renewal dry run were verified. Known security and reliability gaps remain; see [Limitations](#security-and-known-limitations).

## Highlights
- GitHub webhook triggers Jenkins on repository updates.
- pytest tests and SonarQube static analysis run in the pipeline.
- Jenkins builds and pushes a Docker image to Docker Hub.
- Kubernetes runs two Todo replicas with health probes and resource limits.
- Prometheus and Grafana provide Kubernetes metrics and dashboards.
- Nginx provides HTTPS for Grafana; Certbot schedules certificate renewal.

## Architecture

### CI/CD and deployment
![CI/CD architecture](docs/assets/cicd.png)

1. Push code to GitHub (`main`); a webhook triggers Jenkins job `todo-devsecops-pipeline`.
2. Jenkins checks out code, prepares Python, tests with pytest, and runs SonarQube analysis.
3. Jenkins builds and pushes the image, then deploys the workload to Kubernetes.
4. Kubernetes runs two Todo pods behind `todo-app-service`.

### Monitoring and HTTPS
![Monitoring and HTTPS architecture](docs/assets/observability.png)

Prometheus collects Kubernetes metrics and Grafana displays dashboards. A host-managed `kubectl port-forward` binds Grafana to `127.0.0.1:3000`; Nginx terminates TLS on port `443` and proxies requests to Grafana. HTTP redirects to HTTPS except for the ACME HTTP-01 challenge path.

> The public Nginx endpoint in this implementation serves **Grafana**. The Todo Service has NodePort `30080`, but public exposure of that NodePort through the Kind node was not verified.

## Technology Stack
- **Application/testing:** Python, Flask, pytest
- **Source/CI:** GitHub, GitHub webhook, Jenkins
- **Code analysis:** SonarQube Community Build
- **Containers/registry:** Docker, Docker Compose, Docker Hub
- **Orchestration:** Kubernetes, Kind
- **Monitoring:** Helm, kube-prometheus-stack, Prometheus, Grafana
- **HTTPS:** Nginx, Let's Encrypt, Certbot

## CI/CD Pipeline
- **Repository:** [siddhesh0710/todo-devsecops-pipeline](https://github.com/siddhesh0710/todo-devsecops-pipeline)
- **Branch:** `main` | **Jenkins job:** `todo-devsecops-pipeline`
- **Image:** [`sidd7/todo-devsecops`](https://hub.docker.com/r/sidd7/todo-devsecops)

Stages: **Checkout → Setup Python → Tests → SonarQube Analysis → Docker Build → Push to Docker Hub → Deploy to Kubernetes → Post Actions**.

Recorded Jenkins Build **#6** passed all displayed stages, and four pytest tests passed in that run. Pipeline success does not mean all SonarQube findings are fixed or that a quality gate blocks deployment. Keep credentials in Jenkins Credentials; never commit tokens, passwords, kubeconfig files, or private keys.

## Repository Structure
```text
.
├── app.py                     # Flask application
├── templates/index.html       # Todo UI
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # Test/development dependencies
├── test_app.py                # pytest tests
├── Dockerfile
├── compose.yaml
├── Jenkinsfile
├── sonar-project.properties
├── k8s-deployment.yaml        # Kubernetes Deployment and Service
├── monitoring-values.yaml     # Helm values
└── docs/assets/
    ├── cicd.png
    └── observability.png
```

## Run with Docker
Prerequisite: Docker installed and running.
```bash
docker pull sidd7/todo-devsecops:latest
docker volume create todo-data
docker run -d --name todo-app --restart unless-stopped \
  -p 5000:5000 -v todo-data:/app/data sidd7/todo-devsecops:latest
```
Open [http://localhost:5000](http://localhost:5000). Logs: `docker logs --tail=100 todo-app`. Stop: `docker rm -f todo-app`. The volume persists until removed but is not a backup strategy.

## Kubernetes
Recorded configuration: Kind cluster/context `dev-cluster` / `kind-dev-cluster`; namespace `default`; Deployment `todo-app` with **2 replicas**; container port `5000`; Service `todo-app-service` (`NodePort`, `30080`); CPU request/limit `100m`/`500m`; memory request/limit `128Mi`/`512Mi`. Readiness and liveness probes use HTTP `GET /` on port `5000`.

```bash
kubectl --context kind-dev-cluster get nodes
kubectl --context kind-dev-cluster get deploy,pods,svc -n default
kubectl --context kind-dev-cluster rollout status deployment/todo-app -n default
kubectl --context kind-dev-cluster logs deployment/todo-app -n default --tail=100
```
Use an appropriately authorized context in other environments. Keep Jenkins Kubernetes permissions least-privileged.

## Monitoring
The `kube-prometheus-stack` Helm release `monitoring` runs in namespace `monitoring`. Prometheus retention is `7d` with a `5GB` retention-size limit; Prometheus PVC is `10Gi` and Grafana PVC is `2Gi` (both reported `Bound` during validation). The **Kubernetes / Compute Resources / Cluster** dashboard displayed live metrics.

```bash
kubectl --context kind-dev-cluster get pods,pvc,svc -n monitoring
```
`kubectl top nodes` previously returned `Metrics API not available`; this does not by itself indicate Prometheus is unavailable. Kind node-exporter metrics are not a full host-OS monitoring solution.

## HTTPS and Certificate Renewal
- Nginx listens on ports `80` and `443`; HTTP redirects to HTTPS except the ACME challenge path `/.well-known/acme-challenge/`.
- Certbot was installed using Snap and its renewal timer is enabled.
- Deploy hook `/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh` runs `nginx -t` and reloads Nginx.
- The hook ran successfully and `certbot renew --dry-run` reported all simulated renewals succeeded.

Certificate files are under `/etc/letsencrypt/live/<PUBLIC_IP>/` on the host. IP certificates are short-lived: monitor expiry, keep port 80 reachable for ACME validation, and periodically verify the timer and hook. A dry run does not guarantee future renewal or uptime.
```bash
sudo /snap/bin/certbot certificates
systemctl list-timers --all | grep -i certbot
sudo /snap/bin/certbot renew --dry-run
sudo nginx -t
```

## Validation Results
- Jenkins Build #6: all displayed stages passed; pytest: four tests passed in the recorded run.
- Two Todo pods were `Running`, `1/1 Ready`, with zero restarts at the time checked.
- Monitoring pods were healthy and Prometheus/Grafana PVCs were `Bound` during validation.
- Grafana displayed live Kubernetes CPU, memory, and namespace metrics.
- Nginx validation passed; HTTPS returned Grafana's `302` login redirect, and `curl` validated the production IP certificate without `-k`.
- Certbot renewal dry run succeeded.

These are point-in-time results, not a guarantee of future availability.

## Security and Known Limitations
- **Trivy:** A scan reported **44 HIGH and 0 CRITICAL** OS-package vulnerabilities in the Debian 13.7 base layer at that time. Rebuild, test, and rescan before production use; findings may change.
- **SonarQube:** The project showed **2 security issues**, **1 reliability issue**, and **0% coverage** reported by SonarQube. Review findings and configure quality-gate enforcement if it should block releases.
- **SQLite persistence:** Kubernetes does not mount persistent storage at `/app/data/todos.db`; data may be lost when pods are replaced, and separate replicas do not share a single SQLite database.
- **Jenkins Kubernetes credentials:** The configured kubeconfig used a short-lived token and a host-local Kind API endpoint. Establish a sustainable least-privilege credential lifecycle and rotate any exposed credentials.
- **Access and images:** Restrict administrative dashboards to trusted users/networks. Do not commit secrets. Prefer immutable image tags (Git SHA/build ID) over `latest` and document rollback steps.

## Troubleshooting
```bash
# Todo workload
kubectl --context kind-dev-cluster get pods -n default -o wide
kubectl --context kind-dev-cluster describe deployment todo-app -n default
kubectl --context kind-dev-cluster logs deployment/todo-app -n default --tail=100

# Grafana upstream / port-forward
sudo systemctl status grafana-port-forward --no-pager
curl -I --max-time 5 http://127.0.0.1:3000/
sudo journalctl -u grafana-port-forward -n 100 --no-pager

# Nginx / certificate
sudo nginx -t
curl -Iv https://<PUBLIC_IP>/
sudo /snap/bin/certbot certificates
```

## Roadmap
- Resolve or formally accept Trivy and SonarQube findings; add quality-gate enforcement.
- Design durable database storage for replicated Todo pods.
- Improve Jenkins credential lifecycle and use immutable image tags.
- Add host metrics, actionable alerts, and notification routing.
- Test backup/recovery, reboots, cluster restarts, certificate renewal, and rollback.

## Links
- **GitHub:** [todo-devsecops-pipeline](https://github.com/siddhesh0710/todo-devsecops-pipeline)
- **Docker Hub:** [sidd7/todo-devsecops](https://hub.docker.com/r/sidd7/todo-devsecops)

---
Built as a hands-on DevSecOps portfolio project to practice CI/CD automation, containers, Kubernetes deployment, static analysis, observability, and TLS operations.
