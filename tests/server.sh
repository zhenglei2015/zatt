export TERM=xterm

apt-get update
apt-get upgrade -y

apt-get install -y unzip python3-pip git iftop iotop
pip3 install python-dateutil

git clone git@github.com:simonacca/zatt.git
cd zatt
git checkout load

python3 setup.py develop
