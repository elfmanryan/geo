
#!/bin/bash

####INSTALL UBUNTU ENVIRONMENT LIBRARIES######

add-apt-repository ppa:deadsnakes/ppa
add-apt-repository ppa:ubuntugis/ppa

PYTHON_VERSION=3.7

apt update && apt upgrade

apt install -y \
	gdal-bin \
	python3 \
	python${PYTHON_VERSION} \
	python${PYTHON_VERSION}-dev \
	python3-dev \
	python3-pip \
	python3-gdal \
	python3-setuptools \
	libgdal-dev \
	libgsl-dev \
	libssl-dev \
	virtualenv \
	libsm6 \
	libgl1-mesa-glx \
	libxext6 \
	libsm6 \
	libxrender1 \
	libfontconfig1 \
	tree 
	

####CREATE PROJECT STRCTURE#####	
#when adding vagrant to .bashrc, ~ changed from /home/vagrant to /root

HOME=/home/vagrant
PROJECTS=$HOME/projects
ENVS="/envs"
NAME="venv"
#DATA=$HOME/projects
		
mkdir -p $ENVS
mkdir -p $PROJECTS
mkdir -p $DATA

echo "New project folder created at:"
echo $PROJECTS

####CREATE PYTHON ENVIRONMENT########
echo "making virtual environment"
virtualenv -p python${PYTHON_VERSION} $ENVS/$NAME


###ACTIVATE ENVIRONMENT AND INSTALL PYTHON LIBRARIES########
source $ENVS/$NAME/bin/activate
	
pip${PYTHON_VERSION} install \
GDAL==2.1.3 --global-option="build_ext" \
			--global-option="--gdal-config=/usr/bin/gdal-config" \
			--global-option="--include-dirs=/usr/include/gdal/"
 

# for pyproj on 3.7 (issue 136)
#https://github.com/jswhit/pyproj/zipball/master#egg=pyproj \ 

#do seperate pip installs so that if one fails the the rest are still installed
pip${PYTHON_VERSION} install cython==0.28.5
pip${PYTHON_VERSION} install cythongsl 
pip${PYTHON_VERSION} install numpy
pip${PYTHON_VERSION} install pandas==0.23.4
pip${PYTHON_VERSION} install https://github.com/jswhit/pyproj/zipball/master#egg=pyproj 
pip${PYTHON_VERSION} install geopandas==0.4.0
pip${PYTHON_VERSION} install rasterio==1.0.9
pip${PYTHON_VERSION} install rasterstats==0.13.0
pip${PYTHON_VERSION} install opencv-python-headless==3.4.3.18
pip${PYTHON_VERSION} install scikit-image==0.14.1
pip${PYTHON_VERSION} install scikit-learn==0.20.0
pip${PYTHON_VERSION} install scipy==1.1.0
pip${PYTHON_VERSION} install xarray	
pip${PYTHON_VERSION} install sentinelsat==0.12.2
pip${PYTHON_VERSION} install opencv-contrib-python
pip${PYTHON_VERSION} install python-dateutil	
pip${PYTHON_VERSION} install lxml
pip${PYTHON_VERSION} install geojson
pip${PYTHON_VERSION} install progressbar2
##pip${PYTHON_VERSION} install



###############################
#### PROJECT SPECIFIC CODE ####
###############################

cd $PROJECTS	
rm -rf nd || true #remove project if true
#git clone https://github.com/jnhansen/nd
git clone -b dev --single-branch https://github.com/jnhansen/nd #dev branch
cd nd 
$ENVS/$NAME/bin/pip${PYTHON_VERSION} install .


###FIX PERMISSIONS FOR VAGRANT########
#Give vagrant user access to home for deployment permission from pycharm
echo "Giving vagrant sudo root access to /home/vagrant"
#echo "sudo su -" >> .bashrc
chown vagrant:vagrant $HOME -R
	
	
	