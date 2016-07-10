export TERM=xterm

apt-get update
apt-get upgrade -y

apt-get install -y unzip python3-pip git
pip3 install ujson python-dateutil

wget https://accascina.me/zatt.zip
unzip zatt.zip
cd zatt

python3 setup.py develop
