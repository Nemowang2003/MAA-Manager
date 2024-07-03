# MAA-Manager

An HTTPS Server to manage MAA through its remote control protocol.  
At this stage, maybe just call it MAA-Tracker :(

## Feature

- Report MAA login action by username.

- Query MAA last login action time by username.

## API

- `/report` accepts `POST`

    - content: Plain text for username.

    - response: No content.

- `/query` accepts `GET`

    - parmas:

        - user: The username to query.

    - response: Plain text of decription for time since last login action.

## Deployment

- Self-Signed Certificate

This project is using a self-signed certificate.  
The certificate and the key should be palced at `example.crt` and `example.key` respectively.

To get a self-signed (ECDSA-SHA256) certificate, run the command below.

    openssl req -x509 \
      -newkey EC -pkeyopt ec_paramgen_curve:P-256 \
      -sha256 -days ${DAYS} \
      -nodes -keyout ${KEY} -out ${CERT} -subj "/CN=${NAME}" \
      -addext "subjectAltName=DNS:${HOST1},DNS:${HOST2},IP:${IP1},IP:${IP2}"

- Systemd Service

This project is designed to be deployed as systemd service.  
Here is an example:

    # /etc/systemd/system/maa-manager.service
    [Unit]
    Description=MAA Manager HTTPS Server
    After=multi-user.target
    
    [Service]
    ExecStart=python3 -u /path/to/project/server.py
    WorkingDirectory=/path/to/project
    RestartSec=10 # Maybe shorter? I'm not sure.
    
    [Install]
    WantedBy=multi-user.target
