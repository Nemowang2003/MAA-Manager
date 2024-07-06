# MAA-Manager

An HTTPS Server to manage MAA through its remote control protocol managed by poetry.  
At this stage, maybe just call it MAA-Tracker :(

## Feature

- Report MAA action (login/logoout) by username.

- Query MAA last action (login/logout) time by username.

## API

- `/report/<user>/<action>` (`action` is 'online' or 'offline')

    - response: No content.

- `/query/<user>`

    - response: Plain text of decription for time since last action.

## Dependency

This project is managed by `poetry`.  
So just have `poetry` and `python3.12` (will soon change to a more reasonable one) installed, it would deal with the rest.

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
    User=YOUR-USERNAME
    ExecStart=/path/to/poetry run flask run
    WorkingDirectory=/path/to/project
    RestartSec=10 # Maybe shorter? I'm not sure.
    
    [Install]
    WantedBy=multi-user.target

**Note**: `User` should be specified because we usually don't have `poetry` installed for root.

## TODO

Looking forward to deploy on something like waitress.
