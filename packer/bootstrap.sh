#!/bin/bash

set -e

export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical

echo "deb http://ftp.debian.org/debian stretch-backports main" >> /etc/apt/sources.list

apt-get update
apt-get install -y python3 python3-pip nginx postgresql postgresql-client python3-dev build-essential golang-1.10 libssl-dev zlib1g-dev libpcap-dev git tmux vim

git clone https://github.com/avishai-ish-shalom/resilient-design-workshop.git /workshop

pip3 install -r /workshop/requirements.txt

mkdir -p /usr/local/go/src
export GOPATH=/usr/local/go
export GOROOT=/usr/lib/go-1.10
export PATH=$PATH:$GOROOT/bin:$GOPATH/bin
go get -u github.com/golang/dep/cmd/dep
go install -v github.com/golang/dep/cmd/dep
go get -v github.com/circonus-labs/circonus-agent
cd $GOPATH/src/github.com/circonus-labs/circonus-agent
dep ensure
go build -o circonus-agentd github.com/circonus-labs/circonus-agent
cp circonus-agentd /usr/local/bin

go get -v github.com/circonus-labs/wirelatency
go install github.com/circonus-labs/wirelatency/protocol_observer

cd ~
git clone https://github.com/giltene/wrk2.git
cd wrk2
make
cp wrk /usr/local/bin

# setup db
sudo -u postgres psql -v ON_ERROR_STOP=1 <<-"EOSQL"
    CREATE USER app WITH PASSWORD 'password';
    CREATE DATABASE "resilient-design";
    GRANT ALL PRIVILEGES ON DATABASE "resilient-design" TO app;
EOSQL
cd /workshop
PYTHONPATH=src FLASK_APP=server:app flask initdb
bash load_images.sh

cp /workshop/packer/nginx.conf /etc/nginx/sites-available/app
ln -s ../sites-available/app /etc/nginx/sites-enabled/app

pip3 install statsd
mkdir -p /varl/ib/circonus/{state,plugins}

cat - >/etc/systemd/system/log2statsd.service <<-"EOF"
[Unit]
Description=Log2Statsd
After=syslog.target network.target

[Service]
ExecStart=/bin/bash -c 'tail -F /var/log/nginx/extended.log | python3 /workshop/packer/nginx-statsd.py'
Type=simple

[Install]
WantedBy=multi-user.target
EOF

cat - >/etc/systemd/system/app.service <<-"EOF"
[Unit]
Description=app
After=syslog.target network.target

[Service]
ExecStart=/usr/local/bin/gunicorn -b :8881 --pythonpath /workshop/src --config /workshop/gunicorn.config server:app
Type=simple
WorkingDirectory=/workshop
User=admin

[Install]
WantedBy=multi-user.target
EOF

cat - >/etc/systemd/system/circonus-agent.service <<-"EOF"
[Unit]
Description=circonus-agent
After=syslog.target network.target

[Service]
ExecStart=/usr/local/bin/circonus-agentd --api-key e79ccd26-8955-4275-9172-34c477e8b310 -p /var/lib/circonus/plugins -C -E --check-metric-state-dir /varl/ib/circonus/state
Type=simple

[Install]
WantedBy=multi-user.target
EOF

systemctl enable app.service
systemctl enable log2statsd.service
systemctl enable circonus-agent.service

chown admin -R /workshop

cat > /etc/rc.local <<'EOF'
cd /workshop
sudo -u admin git pull
EOF

cat > /etc/profile.d/workshop.sh <<'EOF'
alias restart_app='sudo systemctl restart app.service'
alias error_log='journalctl _SYSTEMD_UNIT=app.service'
EOF
